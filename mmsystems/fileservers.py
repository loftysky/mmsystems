#import argparse

import collections
import subprocess
import os
import re
import sys

from . import zfs
from . import smart
from .ssh import SSHPool


Disk = collections.namedtuple('Disk', 'id zfs devs info')
ZFSInfo = collections.namedtuple('ZFSInfo', 'pool vdev disk')
Device = collections.namedtuple('Device', 'host path')


def iter_disks():
    
    nx01 = SSHPool('nx01.mm')
    nx02 = SSHPool('nx02.mm')

    zpool_queue_1 = nx01.exec_command(zfs.zpool_list_command)
    zpool_queue_2 = nx02.exec_command(zfs.zpool_list_command)
    by_id_queue_1 = nx01.exec_command('''bash -c 'for x in $(ls -1 /dev/disk/by-id); do echo $(hostname) $x $(readlink /dev/disk/by-id/$x); done' ''')
    by_id_queue_2 = nx02.exec_command('''bash -c 'for x in $(ls -1 /dev/disk/by-id); do echo $(hostname) $x $(readlink /dev/disk/by-id/$x); done' ''')

    pools = []
    for q in zpool_queue_1, zpool_queue_2:
        new_pools = zfs.zpool_list(q.get()[0])
        pools.extend(new_pools)

    by_id_dir = '/dev/disk/by-id'
    devs_by_id = {}
    info_q_by_id = {}
    for ssh, by_id_q in (nx01, by_id_queue_1), (nx02, by_id_queue_2):

        for line in by_id_q.get()[0].splitlines():

            line = line.strip()
            if not line:
                continue

            host, id_, link = line.split()

            # We only care about WWNs.
            if not id_.startswith('wwn-'):
                continue

            dev = os.path.normpath(os.path.join(by_id_dir, link))

            # We only care about full devices.
            dev_name = os.path.basename(dev)
            if not re.match(r'^sd[a-z]+$', dev_name):
                continue

            devs_by_id.setdefault(id_, []).append(Device(host, dev))

            # Only lookup smart on one machine.
            if id_ not in info_q_by_id:
                info_q = ssh.exec_command('''smartctl -i {}'''.format(dev))
                info_q_by_id[id_] = info_q

    info_by_id = {}
    for id_, q in info_q_by_id.iteritems():
        info = smart.parse_info(q.get()[0])
        info_by_id[id_] = info

    seen = set()

    for pool in pools:
        for vdev in pool.vdevs:
            for zdisk in vdev.disks:
                id_ = zdisk.name
                yield Disk(id_, ZFSInfo(pool, vdev, zdisk), tuple(devs_by_id.get(id_) or ()), info_by_id.get(id_) or smart.SmartInfo())
                seen.add(zdisk.name)

    for id_ in sorted(devs_by_id):
        if id_ in seen:
            continue
        yield Disk(id_, None, tuple(devs_by_id.get(id_) or ()), info_by_id.get(id_) or smart.SmartInfo())



def main():

    pattern = '{pool:10}  {vdev:10}  {devs:35}  {make:7}  {model:20}  {capacity:>7}  {disk:38}  {sn}'
    print pattern.format(
        pool='ZFS_POOL',
        vdev='ZFS_VDEV',
        devs='DEVICES',
        make='MAKE',
        model='MODEL',
        capacity='SIZE',
        disk='WWN',
        sn='SERIAL',
    )

    for disk in iter_disks():

        devs_str = ','.join('{}:{}'.format(*x) for x in sorted(disk.devs))
        make, model = disk.info.make_and_model

        zpool = disk.zfs.pool if disk.zfs else None
        zvdev = disk.zfs.vdev if disk.zfs else None
        zdisk = disk.zfs.disk if disk.zfs else None

        sn = disk.info.get('serial number')
        capacity = disk.info.capacity_str

        print pattern.format(
            pool=zpool.name if zpool else '-',
            vdev='{}:{}:{}'.format(zvdev.name, zvdev.index, zdisk.index) if zvdev else '-',
            devs=devs_str,
            make=make or '-',
            model=model or '-',
            capacity=capacity,
            disk=disk.id,
            sn=sn,
        )







if __name__ == '__main__':
    main()
