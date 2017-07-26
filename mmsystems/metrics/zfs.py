import os

from .core import Metrics


import psutil


ROOT = '/proc/spl/kstat/zfs'
BOOT_TIME = psutil.boot_time()
BOOT_TIME_NS = int(BOOT_TIME * 1e9)

def iter_generic_values(name):
    with open(os.path.join(ROOT, name), 'rb') as fh:
        fh.next() # Skip pre-header.
        fh.next() # Skip header.
        for line in fh:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            name = parts[0]
            value = parts[-1]
            yield name, int(value)


def iter_pool_table(pool, name):
    with open(os.path.join(ROOT, pool, name), 'rb') as fh:
        fh.next() # Skip the header.
        names = fh.next().strip().split()
        for line in fh:
            line = line.strip()
            if line:
                values = [int(x) if x.isdigit() else x for x in line.split()]
                yield dict(zip(names, values))


_last_complete_txgs = {}

def iter_pool_txg_metrics(pool, skip_last=False, skip_rest=True):

    last_complete_txg = _last_complete_txgs.get(pool)
    max_time_ns = 0

    for row in reversed(list(iter_pool_table(pool, 'txgs'))):

        state = row.pop('state')
        if state != 'C':
            continue

        time_ns = BOOT_TIME_NS + row.pop('birth')
        max_time_ns = max(max_time_ns, time_ns)

        # Don't return anything we've already seen.
        if last_complete_txg and time_ns <= last_complete_txg:
            break

        # If this is the first run, then maybe we can return the most recent.
        if skip_last and not last_complete_txg:
            break

        yield Metrics('zfs.txgs', 'zfs.{pool}.txgs', dict(pool=pool), row, time=time_ns / 1.0e9)

        if skip_rest and not last_complete_txg:
            break

    if max_time_ns:
        _last_complete_txgs[pool] = max_time_ns

def iter_pools():
    for name in os.listdir(ROOT):
        path = os.path.join(ROOT, name, 'io')
        if os.path.exists(path):
            yield name



def iter_all_metrics():

    yield Metrics('zfs.arc', 'zfs.{host}.arc', dict(), iter_generic_values('/proc/spl/kstat/zfs/arcstats'))
    yield Metrics('zfs.zil', 'zfs.{host}.zil', dict(), iter_generic_values('/proc/spl/kstat/zfs/zil'))
    yield Metrics('zfs.dmu', 'zfs.{host}.dmu', dict(), iter_generic_values('/proc/spl/kstat/zfs/dmu_tx'))
    yield Metrics('zfs.zfetch', 'zfs.{host}.zfetch', dict(), iter_generic_values('/proc/spl/kstat/zfs/zfetchstats'))

    for pool in iter_pools():
        yield Metrics('zfs.io', 'zfs.{pool}.io', dict(pool=pool), next(iter_pool_table(pool, 'io')))
        for m in iter_pool_txg_metrics(pool):
            yield m


if __name__ == '__main__':

    for metric in iter_all_metrics():
        metric.pprint_influx()
