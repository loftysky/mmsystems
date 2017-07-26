import re
import os
import errno

import psutil

from . import utils
from .core import Metrics
from ..zfs import zpool_list


KEYS = ('read_count', 'write_count', 'read_bytes', 'write_bytes', 'read_time', 'write_time')


def iter_metrics(include_devices=None, exclude_devices=None, tags_by_name=None, aggregators=None):

    all_data = psutil.disk_io_counters(True)

    # Collapse partitions into devices.
    # psutil gives us sda1 without sda, but does give us sda if there is no sda1.
    all_data = utils.aggregate_namedtuples(all_data, [(
        lambda name, data: re.sub(r'^(sd[a-z]+)\d+$', r'\1', name),
        sum,
    )], return_tags=False)

    # Filter out partitions.
    all_data = {k: v for k, v in all_data.iteritems() if not k[-1].isdigit()}

    # User filtering.
    if include_devices:
        all_data = {k: v for k, v in all_data.iteritems() if k in include_devices}
    if exclude_devices:
        all_data = {k: v for k, v in all_data.iteritems() if k not in exclude_devices}

    aggregators = list(aggregators or [])
    aggregators.append((
        ('__sum__', dict(agg_key='__all__')),
        sum,
    ))

    # Sum it all.
    all_data = utils.aggregate_namedtuples(all_data, aggregators)

    for name, (data, agg_tags) in sorted(all_data.iteritems()):
        tags = dict(tags_by_name.get(name) or {}) if tags_by_name else {}
        tags.update(agg_tags)
        tags.setdefault('name', name)
        yield Metrics('disk.io', 'disk.io.{name}', tags, data._asdict())


_zfs_kwargs = {}

def iter_zfs_metrics(force_zpool_list=False):

    if force_zpool_list or not _zfs_kwargs:

        _zfs_kwargs['include_devices'] = include = set()
        _zfs_kwargs['tags_by_name'] = tags_by_name = {}
        _zfs_kwargs['aggregators'] = aggregators = []

        pool_by_name = {}

        for pool in zpool_list():
            # print 'pool', pool

            for vdev in pool.vdevs:
                # print 'vdev', vdev
                for disk in vdev.disks:
                    # print 'disk', disk

                    name = disk.name
                    try:
                        path = os.readlink(os.path.join('/dev/disk/by-id', name))
                    except OSError as e:
                        if e.errno != errno.ENOENT:
                            raise
                    else:
                        name = os.path.basename(path)

                    pool_by_name[name] = pool

                    include.add(name)
                    tags_by_name[name] = dict(
                        pool=pool.name,
                        vdev_type=vdev.name,
                        vdev_index=vdev.index,
                        disk_index=disk.index,
                    )

        def pool_key(name, _):
            pool = pool_by_name[name]
            return '__sum_{}__'.format(pool.name), dict(agg_key='pool', pool=pool.name)
        aggregators.append((pool_key, sum))

    return iter_metrics(**_zfs_kwargs)



if __name__ == '__main__':

    for m in iter_zfs_metrics():
        m.pprint_influx()
