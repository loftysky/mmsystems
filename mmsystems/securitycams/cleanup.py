from Queue import Queue
import argparse
import datetime
import errno
import math
import os
import sys
import threading
import time
import traceback

sys.path.append('/usr/local/vee/environments/markmedia/master/lib64/python2.7/site-packages')

import MySQLdb as mysql


BULK_SIZE = 900
BULK_PAD  = 6


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument('-a', '--de-alarm', action='store_true')
    parser.add_argument('-A', '--de-alert', action='store_true')

    parser.add_argument('-T', '--re-total-frames', action='store_true')
    parser.add_argument('-t', '--re-total-events', action='store_true')
    parser.add_argument('-b', '--re-bulk', action='store_true')


    # parser.add_argument('-m', '--migrate', action='store_true')

    parser.add_argument('-M', '--add-missing', action='store_true')

    parser.add_argument('-x', '--delete-boring', action='store_true')
    parser.add_argument('-X', '--delete-old', action='store_true')

    parser.add_argument('-f', '--delete-files', action='store_true')

    parser.add_argument('-n', '--dry-run', action='store_true')
    args = parser.parse_args()

    con = mysql.Connect(
        host='127.0.0.1',
        user='zmuser',
        passwd='GK9CLtdD4zcEQ8LMYV',
        db='zm',
    )

    for name in ('de_alarm', 'de_alert', 'add_missing',
        'delete_boring', 're_total_frames', 're_bulk', 're_total_events',
        'delete_old', 'delete_files'):
        if getattr(args, name):
            globals()[name](con, args)


def de_alarm(con, args):

    cur = con.cursor()
    start_id = 0

    while True:

        cur.execute('''SELECT Id, EventId, FrameId FROM Frames WHERE Id > %s AND Score > 0 AND Score < 5 LIMIT 1000''', [start_id])
        rows = cur.fetchall()
        if not rows:
            return

        start_id = rows[-1][0]

        by_event = {}
        for row in rows:
            Id, EventId, FrameId = row
            by_event.setdefault(EventId, []).append((Id, FrameId))

        for EventId, rows in sorted(by_event.iteritems()):
            print '    event {}: {} frames from {} to {}'.format(EventId, len(rows), rows[0][1], rows[-1][1])
            if not args.dry_run:
                cur.execute('''DELETE FROM Stats WHERE EventId = %s AND FrameId IN ({})'''.format(','.join(['%s'] * len(rows))), [EventId] + [row[1] for row in rows])
                cur.execute('''UPDATE Frames SET Score = 0, Type = "Normal" WHERE Id IN ({})'''.format(','.join(['%s'] * len(rows))), [row[0] for row in rows])





def de_alert(con, args):

    if args.dry_run:
        return

    # This one is kinda assumed. I'm not 100% what these are. They are frames with
    # score = 50, and no stats.

    print "Removing all alerts."

    cur = con.cursor()
    cur.execute('''SELECT Id FROM Events''')
    ids = [r[0] for r in cur]
    for EventId in ids:
        print '   ', EventId
        cur.execute('''
            UPDATE
                Frames
                LEFT OUTER JOIN Stats
                    ON Frames.FrameId = Stats.FrameId
                    AND Frames.EventId = Stats.EventId
            SET Frames.Score = 0,
                Frames.Type = "Normal"
            WHERE Frames.EventId = %s
              AND Frames.Score > 0
              AND Stats.Score IS NULL
        ''', [EventId])
        print cur.rowcount
        if cur.rowcount:
            con.commit()



def _calc_event_scores(cur, id_, num_frames=None):

    cur.execute('''SELECT Score From Stats WHERE EventId = %s and Score >= 5''', [id_])
    scores = [row[0] for row in cur]

    alarm_frames = len(filter(None, scores))
    tot_score = sum(scores) if scores else 0
    max_score = max(scores) if scores else 0

    if tot_score and num_frames is None:
        cur.execute('''SELECT Frames FROM Events WHERE Id = %s''', [id_])
        num_frames = cur.fetchone()[0]
    avg_score = int(tot_score / num_frames) if (tot_score and num_frames) else 0

    return alarm_frames, tot_score, max_score, avg_score



def re_total_frames(con, args):

    cur = con.cursor()
    cur.execute('''SELECT Id FROM Events WHERE NOT EndTime IS NULL ORDER BY Id DESC''')
    for eid, in cur.fetchall():

        print eid

        cur.execute('''SELECT FrameId, sum(Score) from Stats WHERE EventId = %s GROUP BY FrameId''', [eid])
        stat_scores = dict(cur)

        did_update = False
        cur.execute('''SELECT Id, FrameId, Score, Type from Frames WHERE EventId = %s''', [eid])
        for id_, fid, fscore, ftype in cur:
            sscore = stat_scores.get(fid, 0)
            if sscore != fscore or (not sscore and ftype == 'Alarm'):
                print '    frame {} ({}): {} != {}'.format(fid, id_, sscore, fscore or 0)
                if not args.dry_run:
                    cur.execute('''UPDATE Frames SET Score = %s, Type = %s WHERE Id = %s''', [
                        sscore, 'Alarm' if sscore else 'Normal', id_,
                    ])
                    did_update = True

        if did_update:
            con.commit()



def re_total_one(con, id_):
    cur = con.cursor()
    alarm_frames, tot_score, max_score, avg_score = _calc_event_scores(cur, id_)
    cur.execute('''UPDATE Events SET AlarmFrames = %s, TotScore = %s, MaxScore = %s, AvgScore = %s WHERE Id = %s''', [
        alarm_frames, tot_score, max_score, avg_score, id_,
    ])
    return tot_score


def re_total_events(con, args):

    print 'Re-totalling event scores.'

    cur = con.cursor()
    cur.execute('''SELECT Id, Frames, AlarmFrames, TotScore, MaxScore, AvgScore FROM Events''')
    events = list(cur)

    for EventId, Frames, AlarmFrames, TotScore, MaxScore, AvgScore in events:

        alarm_frames, tot_score, max_score, avg_score = _calc_event_scores(cur, EventId, Frames)
        if alarm_frames == AlarmFrames and tot_score == TotScore and max_score == MaxScore:
            continue

        print '    event {}: totaled {}/{}/{}/{} does not match recorded {}/{}/{}/{}'.format(EventId,
            alarm_frames, tot_score, max_score, avg_score,
            AlarmFrames, TotScore, MaxScore, AvgScore,
        )
        if not args.dry_run:
            cur.execute('''UPDATE Events SET AlarmFrames = %s, TotScore = %s, MaxScore = %s, AvgScore = %s WHERE Id = %s''', [
                alarm_frames, tot_score, max_score, avg_score, EventId,
            ])
            con.commit()


def re_bulk(con, args):


    print 'Re-Bulking frames.'

    cur = con.cursor()
    cur.execute('''SELECT Id FROM Events WHERE NOT EndTime IS NULL ORDER BY Id DESC''')
    event_ids = [r[0] for r in cur]

    to_bulk = []
    def do_bulk(EventId):

        ids_ = to_bulk[:]
        to_bulk[:] = []

        if len(ids_) < 3:
            return

        new_bulks = set()
        for id_ in ids_:
            new_id = int(math.ceil(id_ / float(BULK_SIZE))) * BULK_SIZE
            new_bulks.add(new_id)

        if len(new_bulks) == len(ids_):
            return

        print '    Making {} group(s) covering {} to {}'.format(len(new_bulks), ids_[0], ids_[-1])
        if not args.dry_run:
            cur.execute('''UPDATE Frames SET Type = "Bulk" WHERE EventId = %s AND FrameId IN ({})'''.format(','.join(['%s'] * len(new_bulks))), [EventId] + list(new_bulks))
            cur.execute('''DELETE FROM Frames              WHERE EventId = %s AND FrameId >= %s AND FrameId <= %s AND NOT FrameId IN ({})'''.format(','.join(['%s'] * len(new_bulks))), [
                    EventId, ids_[0], ids_[-1],
                ] + list(new_bulks))
            con.commit()


    for EventId in event_ids:

        print 'Event', EventId
        cur.execute('''SELECT FrameId, Type FROM Frames WHERE EventId = %s''', [EventId])
        frames = sorted(cur)

        # Figure out which frames are alarmy, with a half second of padding on
        # each side.
        alarmy = set()
        for FrameId, Type in frames:
            if Type == 'Alarm':
                for i in xrange(FrameId - BULK_PAD, FrameId + BULK_PAD + 1):
                    alarmy.add(i)

        for FrameId, Type in frames:

            if Type == 'Alarm':
                do_bulk(EventId)

            elif FrameId not in alarmy:
                to_bulk.append(FrameId)

        do_bulk(EventId)




def add_missing(con, args):

    if args.dry_run:
        return

    # My bad. I broke it all.
    print 'Replace missing frames.'

    cur = con.cursor()
    cur.execute('''SELECT Id, Frames, StartTime, EndTime FROM Events WHERE NOT EXISTS (SELECT 1 FROM Frames WHERE Frames.EventId = Events.Id)''')
    events = list(cur)

    for EventId, Frames, StartTime, EndTime in events:

        print '    Event {}'.format(EventId)

        per_frame = ((EndTime - StartTime).total_seconds() + 0.5) / float(Frames)

        cur.execute('''SELECT FrameId, sum(Score) FROM Stats WHERE EventId = %s AND Score >= 5 GROUP BY FrameId''', [EventId])
        frames = list(cur)

        last = 0
        FrameId = 0
        for FrameId, Score in frames:


            if last + 1 != FrameId:
                bDelta = (FrameId - 1) * per_frame
                bTimeStamp = StartTime + datetime.timedelta(seconds=bDelta)
                cur.execute('''INSERT INTO Frames (EventId, FrameId, Type, TimeStamp, Delta, Score) VALUES (%s, %s, %s, %s, %s, %s)''', [
                    EventId, FrameId - 1, "Bulk", bTimeStamp, bDelta, 0
                ])

            last = FrameId

            Delta = FrameId * per_frame
            TimeStamp = StartTime + datetime.timedelta(seconds=Delta)

            cur.execute('''INSERT INTO Frames (EventId, FrameId, Type, TimeStamp, Delta, Score) VALUES (%s, %s, %s, %s, %s, %s)''', [
                EventId, FrameId, "Alarm", TimeStamp, Delta, Score
            ])

        if FrameId != Frames:
            bDelta = Frames * per_frame
            bTimeStamp = StartTime + datetime.timedelta(seconds=bDelta)
            cur.execute('''INSERT INTO Frames (EventId, FrameId, Type, TimeStamp, Delta, Score) VALUES (%s, %s, %s, %s, %s, %s)''', [
                EventId, Frames, "Bulk", bTimeStamp, bDelta, 0
            ])

        con.commit()


def delete_event(cur, eid):
    cur.execute('''DELETE FROM Stats WHERE EventId = %s''', [eid])
    cur.execute('''DELETE FROM Frames WHERE EventId = %s''', [eid])
    cur.execute('''DELETE FROM Events WHERE Id = %s''', [eid])


def delete_old(con, args):

    cur = con.cursor()
    # cur.execute('''SELECT Id, StartTime, EndTime, TotScore FROM Events''')
    # events = list(cur)

    # for id_, start_time, end_time, tot_score in events:
    #     print start_time, end_time

    cur.execute('''SELECT Id FROM Events WHERE NOT EndTime is NULL AND (TotScore = 0 OR TIMESTAMPDIFF(DAY, EndTime, NOW()) >= 7)''')
    events = [row[0] for row in cur]

    for id_ in events:
        print 'Deleting event', id_
        if not args.dry_run:
            delete_event(cur, id_)
            con.commit()


def datetime_is_boring(v):

    if not v:
        return False

    if v.weekday() >= 5: # 0 is Monday, so 5 is Saturday
        return False

    if v.hour < 7: # Before 7am
        return False

    if v.hour >= 20: # After 8pm.
        return False

    return True


def delete_boring(con, args):

    cur = con.cursor()

    boring_zones = list()
    cur.execute('''SELECT Id, Name FROM Zones''')
    for zid, name in cur:
        boring = 'unit8' not in name and 'rear-door' not in name
        if boring:
            boring_zones.append(zid)
        print '{:16s} is {}'.format(name, 'boring' if boring else 'INTERESTING')
    boring_zones_sql = '({})'.format(', '.join(str(x) for x in boring_zones))

    cur.execute('''SELECT Id, StartTime, EndTime FROM Events WHERE TotScore > 0''')
    for eid, start_time, end_time in cur.fetchall():

        if not datetime_is_boring(start_time):
            continue
        if not datetime_is_boring(end_time):
            continue

        print 'Considering event {} from {} to {}'.format(eid, start_time, end_time)
        cur.execute('''DELETE FROM Stats WHERE EventId = %s AND ZoneId IN {}'''.format(boring_zones_sql), [eid])
        if cur.rowcount:
            print '    Removed {} boring stats.'.format(cur.rowcount)
            new_total = re_total_one(con, eid)
            if not new_total:
                print '    Event has no interesting stats; deleting.'
                delete_event(cur, eid)
            con.commit()



def delete_files(con, args):

    cur = con.cursor()
    cur.execute('''SELECT Id FROM Events''')
    ids = set(r[0] for r in cur)
    max_id = max(ids)

    def target():
        while True:
            path = queue.get()
            if not path:
                queue.put(None) # Cascade a shutdown.
            try:
                os.unlink(path)
            except:
                traceback.print_exc()

    n_threads = 32
    queue = Queue(n_threads)
    threads = []
    for _ in xrange(n_threads):
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        threads.append(thread)

    root = '/Volumes/securitycams/zoneminder/events'
    for monitor in '1', '2':
        mdir = os.path.join(root, monitor)
        for year in sorted(os.listdir(mdir)):
            Ydir = os.path.join(mdir, year)
            for month in sorted(os.listdir(Ydir)):
                Mdir = os.path.join(Ydir, month)
                for day in sorted(os.listdir(Mdir)):
                    Ddir = os.path.join(Mdir, day)
                    for event in sorted(os.listdir(Ddir)):
                        if event.startswith('.') and event[1:].isdigit():
                            id_ = int(event[1:])
                            if id_ >= max_id:
                                continue
                            if id_ not in ids:
                                print
                                print 'Deleting', id_,
                                if args.dry_run:
                                    continue
                                edir = os.path.join(Ddir, event)
                                try:
                                    names = os.listdir(edir)
                                except OSError as e:
                                    if e.errno == errno.ENOENT:
                                        continue
                                    raise
                                for i, name in enumerate(sorted(names)):
                                    if i % 100 == 0:
                                        sys.stdout.write('.')
                                        sys.stdout.flush()
                                    queue.put(os.path.join(edir, name))

                                # Need to wait for it to empty before cleaning up the symlink.
                                while not queue.empty():
                                    time.sleep(0.1)
                                os.unlink(edir)

    for thread in threads:
        queue.put(None)
        thread.join()



if __name__ == '__main__':
    main()
