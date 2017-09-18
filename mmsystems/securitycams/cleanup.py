import argparse
import math
import datetime

import MySQLdb as mysql



parser = argparse.ArgumentParser()
parser.add_argument('-a', '--de-alarm', action='store_true')
parser.add_argument('-A', '--de-alert', action='store_true')
parser.add_argument('-t', '--re-total', action='store_true')
parser.add_argument('-b', '--re-bulk', action='store_true')
parser.add_argument('-m', '--add-missing', action='store_true')

parser.add_argument('-n', '--dry-run', action='store_true')
args = parser.parse_args()


con = mysql.Connect(
    host='127.0.0.1',
    user='zmuser',
    passwd='xxx',
    db='zm',
)


BULK_SIZE = 900
BULK_PAD  = 6


def de_alarm(start=0):

    cur = con.cursor()
    cur.execute('''SELECT Id, EventId, FrameId FROM Frames WHERE Id > %s AND Score > 0 AND Score < 5 LIMIT 1000''', [start])
    rows = cur.fetchall()
    if not rows:
        return

    max_id = rows[-1][0]

    by_event = {}
    for row in rows:
        Id, EventId, FrameId = row
        by_event.setdefault(EventId, []).append((Id, FrameId))

    for EventId, rows in sorted(by_event.iteritems()):
        print '    event {}: {} frames from {} to {}'.format(EventId, len(rows), rows[0][1], rows[-1][1])
        if not args.dry_run:
            cur.execute('''DELETE FROM Stats WHERE EventId = %s AND FrameId IN ({})'''.format(','.join(['%s'] * len(rows))), [EventId] + [row[1] for row in rows])
            cur.execute('''UPDATE Frames SET Score = 0, Type = "Normal" WHERE Id IN ({})'''.format(','.join(['%s'] * len(rows))), [row[0] for row in rows])

    return max_id

if args.de_alarm:

    print "Removing all stats with score < 5."
    i = 0
    state = 0
    while True:
        state = de_alarm(state)
        if not state:
            break
        i += 1
        if i % 10 == 0:
            con.commit()
    con.commit()


# This one is kinda assumed. I'm not 100% what these are. They are frames with
# score = 50, and no stats.
def de_alert(start=0):

    cur = con.cursor()
    cur.execute('''
        SELECT f.Id, f.EventId, f.Score
        FROM Frames as f LEFT OUTER JOIN Stats AS s
        ON f.EventId = s.EventId AND f.FrameId = s.FrameId
        WHERE f.Id > %s AND f.Score > 0 AND s.Score IS NULL
        LIMIT 1000
    ''', [start])

    rows = list(cur)
    if not rows:
        return

    ids = [r[0] for r in rows]
    event = rows[0][1]
    score = sum(r[2] for r in rows)

    print '    Normalizing {} frames from #{} with total score {}, from {} to {}'.format(len(ids), event, score, ids[0], ids[-1])
    if not args.dry_run:
        cur.execute('''UPDATE Frames SET Score = 0, Type = "Normal" WHERE Id IN ({})'''.format(','.join(['%s'] * len(ids))), ids)
    return ids[-1]

if args.de_alert:

    print "Removing all alerts."
    i = 0
    state = 0
    while True:
        state = de_alert(state)
        if not state:
            break
        i += 1
        if i % 10 == 0:
            con.commit()
    con.commit()


if args.re_total:

    print 'Re-totalling event scores.'

    cur = con.cursor()
    cur.execute('''SELECT Id, Frames, AlarmFrames, TotScore, MaxScore, AvgScore FROM Events WHERE TotScore > 0''')
    events = list(cur)

    for EventId, Frames, AlarmFrames, TotScore, MaxScore, AvgScore in events:
        cur.execute('''SELECT Score From Stats WHERE EventId = %s and Score > 0''', [EventId])
        scores = [r[0] for r in cur]
        alarm_frames = len(filter(None, scores))
        tot_score = sum(scores) if scores else 0
        max_score = max(scores) if scores else 0
        avg_score = int(tot_score / Frames) if scores else 0
        if alarm_frames != AlarmFrames or tot_score != TotScore or max_score != MaxScore:
            print '    event {}: totaled {}/{}/{}/{} does not match recorded {}/{}/{}/{}'.format(EventId,
                alarm_frames, tot_score, max_score, avg_score,
                AlarmFrames, TotScore, MaxScore, AvgScore,
            )
            if not args.dry_run:
                cur.execute('''UPDATE Events SET AlarmFrames = %s, TotScore = %s, MaxScore = %s, AvgScore = %s WHERE Id = %s''', [
                    alarm_frames, tot_score, max_score, avg_score, EventId,
                ])
                con.commit()


if args.re_bulk:

    print 'Re-Bulking frames.'

    cur = con.cursor()
    cur.execute('''SELECT Id FROM Events''')
    event_ids = list(cur)

    to_bulk = []
    def do_bulk(EventId):

        ids_ = to_bulk[:]
        to_bulk[:] = []

        if len(ids_) < 2:
            return

        new_bulks = set()
        for id_ in ids_:
            new_id = int(math.ceil(id_ / float(BULK_SIZE))) * BULK_SIZE
            new_bulks.add(new_id)

        if len(new_bulks) == len(ids_):
            return

        print '    Making {} groups covering {} to {}'.format(len(new_bulks), ids_[0], ids_[-1])
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




if args.add_missing:

    # My bad. I broke it all.
    print 'Replace missing frames.'

    cur = con.cursor()
    cur.execute('''SELECT Id, Frames, StartTime, EndTime FROM Events WHERE NOT EXISTS (SELECT 1 FROM Frames WHERE Frames.EventId = Events.Id)''')
    events = list(cur)

    for EventId, Frames, StartTime, EndTime in events:

        print '    Event {}'.format(EventId)

        per_frame = ((EndTime - StartTime).total_seconds() + 0.5) / float(Frames)

        cur.execute('''SELECT FrameId, sum(Score) FROM Stats WHERE EventId = %s GROUP BY FrameId''', [EventId])
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


