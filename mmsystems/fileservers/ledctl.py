import argparse
import subprocess
import os
import re
import sys

from .. import zfs




def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--all', action='store_true')
    parser.add_argument('-p', '--pattern', default='locate')
    parser.add_argument('pool', nargs='?')
    args = parser.parse_args()

    if not (args.all or args.pool):
        print 'Must supply pool or --all.'
        return

    pools = zfs.zpool_list()
    if args.pool:
        pools = [p for p in pools if p.name == args.pool]
    if not pools:
        print 'There is no pool:', args.pool
        return
    
    disks = []
    for pool in pools:
        for vdev in pool.vdevs:
            for zdisk in vdev.disks:
                disks.append('/dev/disk/by-id/' + zdisk.name)

    command = ['ledctl']
    command.append(args.pattern + '=' + ','.join(disks))

    subprocess.check_call(command)



if __name__ == '__main__':
    main()
