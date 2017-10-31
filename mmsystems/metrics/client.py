from __future__ import print_function

import argparse
import cPickle as pickle
import socket
import sys
import time

import requests

from .sources import cpu
from .sources import disks
from .sources import mem
from .sources import net
from .sources import nfs
from .sources import zfs

from .servers import graphite
from .servers import influx


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument('-a', '--all', action='store_true')
    parser.add_argument('--nfs-client', action='store_true')
    parser.add_argument('-c', '--cpu', action='store_true')
    parser.add_argument('-d', '--disks', action='store_true')
    parser.add_argument('-m', '--mem', action='store_true')
    parser.add_argument('-n', '--network', action='store_true')
    parser.add_argument('-N', '--nfs-server', action='store_true')
    parser.add_argument('-z', '--zfs', action='store_true')

    parser.add_argument('--influx', default='http://influx.mm')
    parser.add_argument('-D', '--influx-database', default='metrics')
    parser.add_argument('--graphite', default='graphite.mm:2004')
    parser.add_argument('-P', '--graphite-prefix', default='')
    parser.add_argument('-I', '--no-influx', action='store_true')
    parser.add_argument('-G', '--no-graphite', action='store_true')
    parser.add_argument('-i', '--interval', type=int, default=10)

    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('--dev', action='store_true')

    parser.add_argument
    args = parser.parse_args()


    if args.graphite and ':' in args.graphite:
        host, port = args.graphite.split(':', 1)
        args.graphite = (host, int(port))

    if args.dev:
        args.influx_database = 'dev'
        args.graphite_prefix = 'dev.'


    def iter_many_metrics():

        if args.all or args.network:
            yield net.get_metrics()
        if args.all or args.mem:
            yield mem.get_metrics()
        if args.all or args.cpu:
            yield cpu.get_metrics()

        if args.all or args.zfs:
            for m in zfs.iter_all_metrics():
                yield m

        if args.all or args.nfs_server:
            yield nfs.get_metrics(server=True, )
        if args.nfs_client:
            yield nfs.get_metrics(server=False, )

        if args.all or args.disks:
            if args.all or args.zfs:
                for m in disks.iter_zfs_metrics():
                    yield m
            else:
                for m in disks.iter_metrics():
                    yield m




    now = time.time()
    next_time = 5 * (int(now) / 5)

    while True:

        all_metrics = list(iter_many_metrics())
        for m in all_metrics:
            m.time = m.time or now

        if args.verbose:
            print
            for m in all_metrics:
                m.pprint_graphite()

        if not args.no_influx:
            influx.send_many(args.influx, args.influx_database, all_metrics)
        if not args.no_graphite:
            graphite.send_many(args.graphite, all_metrics, prefix=args.graphite_prefix)

        next_time += args.interval
        to_sleep = next_time - time.time()
        if to_sleep > 0:
            time.sleep(to_sleep)

        now = next_time




