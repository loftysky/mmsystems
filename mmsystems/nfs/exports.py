#!usr/bin/env python

from __future__ import print_function

import argparse
import os
import re
import shutil
import socket
import subprocess
import sys

from mmcore.configfile import ConfigFile

import netaddr


named_networks = {

    'all': '10.0.0.0/8',

    'wired': '10.10.0.0/16',
    'untrusted': '10.20.0.0/16',

    'vpn': '10.90.0.0/16',
    'ipsec': '10.90.0.0/24',
    'openvpn': '10.90.1.0/24',

    'network': '10.10.0.0/24',
    'original': '10.10.1.0/24',
    'fileservers': '10.10.2.0/24',
    'workstations': '10.10.3.0/24',
    'farm': '10.10.4.0/24',
    'supes': '10.10.5.0/24',

    'dhcp': '10.10.100.0/20', # This is a bit wide.

    'core': ['network', 'original', 'fileservers', 'farm', 'supes', 'net_admins'],

    'net_admins': ['mikeb.mm'],
    'admins': ['mikeb.mm', 'yvanp.mm'],

    'strong_authed': ['wired', 'ipsec'],
    'weak_authed': ['wired', 'vpn'],

}

def resolve_networks(x):
    return list(sorted(set(_resolve_networks(x))))

def _resolve_networks(x):

    while isinstance(x, basestring):
        try:
            x = named_networks[x.lower()]
        except KeyError:
            break

    if isinstance(x, basestring):
        yield x

    else:
        for y in x:
            for z in _resolve_networks(y):
                yield z




def main():

    parser = argparse.ArgumentParser()

    parser.add_argument('-n', '--dry-run', action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')

    parser.add_argument('-c', '--config', default='/etc/mmconfig/exports.py')

    parser.add_argument('-a', '--all', action='store_true',
        help="Same as -emfME.")

    parser.add_argument('-e', '--exports', action='store_true',
        help="Modify /etc/exports.")
    parser.add_argument('-m', '--mkdir', action='store_true',
        help="Make /export/VOLUME mount points.")
    parser.add_argument('-f', '--fstab', action='store_true',
        help="Modify /etc/fstab.")
    parser.add_argument('-M', '--mount', action='store_true',
        help="Auto-mount via `mount -a`.")
    parser.add_argument('-E', '--exportfs', action='store_true',
        help="Reload exports via `exportfs -ra`.")

    args = parser.parse_args()

    if args.all:
        args.exports = args.mkdir = args.fstab = args.mount = args.exportfs = True

    if not (args.dry_run or args.exports or args.mkdir or args.fstab or args.mount or args.exportfs):
        print("Nothing to do. Please use -a, -n, or one of -emfME.", file=sys.stderr)
        exit(1)

    if not os.path.exists(args.config):
        print("Could not find {}.".format(args.config), file=sys.stderr)
        exit(2)

    exports = {}
    def export(name, src_path, networks):
        
        if src_path != os.path.abspath(src_path):
            raise ValueError("Source paths must be absolute.", src_path)
        if not os.path.exists(src_path):
            raise ValueError("Source paths must exist.", src_path)

        if args.verbose:
            print('export({!r}, {!r}, {!r})'.format(name, src_path, networks))

        networks = resolve_networks(networks)

        if args.verbose:
            print('    resolved: ', ', '.join(sorted(networks)))

        ip_set = netaddr.IPSet()
        new_networks = []
        for x in networks:
            if re.match(r'\d+\.', x):
                ip_set.add(x)
            else:
                new_networks.append(x)
        ip_set.compact()
        for x in ip_set.iter_cidrs():
            new_networks.append(str(x))
        new_networks.sort()

        if args.verbose:
            print('    compacted:', ', '.join(sorted(new_networks)))

        exports[name] = dict(src_path=src_path, networks=new_networks)

    namespace = dict(
        export=export,
    )
    namespace.update({k.upper(): v for k, v in named_networks.items()})
    execfile(args.config, namespace)


    if args.exports:
        update_etc_exports(exports, verbose=args.verbose, dry_run=args.dry_run)

    if args.mkdir:
        for name in exports:
            path = os.path.join('/export', name)
            if not os.path.lexists(path):
                if args.verbose:
                    print("mkdir {}".format(path))
                if not args.dry_run:
                    os.makedirs(path)

    if args.fstab:
        update_etc_fstab(exports, verbose=args.verbose, dry_run=args.dry_run)

    if args.mount:
        if not args.dry_run:
            subprocess.check_call(['mount', '-a'])

    if args.exportfs:
        if not args.dry_run:
            subprocess.check_call(['exportfs', '-ra'])


def update_etc_exports(exports, verbose=False, dry_run=False):

    chunks = []

    for name, spec in sorted(exports.items()):
        chunks.append('/export/{}'.format(name))
        for network in spec['networks']:
            chunks.append(' \\\n\t{}(rw,nohide,insecure,no_subtree_check,async,no_root_squash)'.format(network))    
        chunks.append('\n')

    config_str = ''.join(chunks)
    if verbose:
        print(config_str)

    if not dry_run:
        config = ConfigFile('/etc/exports')
        config.set_content('mmnfs-exports', config_str)
        config.dump()


def update_etc_fstab(exports, verbose=False, dry_run=False):

    chunks = []

    for name, spec in sorted(exports.items()):
        chunks.append('{} /export/{} none bind\n'.format(spec['src_path'], name))


    config_str = ''.join(chunks)
    if verbose:
        print(config_str)

    if not dry_run:
        config = ConfigFile('/etc/fstab')
        config.set_content('mmnfs-exports', config_str)
        config.dump()


'''



elif hostname == 'nx02.mm':

    volumes = [
        
        dict(name='TerraBlock.bak', networks=['main']),
        dict(name='BBQ-backup', networks=['main']),

        #dict(name='archive', networks=['main']),
        
        dict(name='securitycams', networks=['supes', 'admin_workstations']),

        dict(name='home', networks=authned_networks),
        dict(name='masters', networks=authned_networks),
        
        dict(name='MM02b', networks=authned_networks),
        dict(name='EditOnline', networks=authned_networks),
    ]

else:
    print 'Unknown host:', hostname
    exit(1)

for volume in volumes:
    write('/export/{name}'.format(**volume))
    for network in volume['networks']:
        network = networks.get(network, network)
        write(' \\\n\t{}(rw,nohide,insecure,no_subtree_check,async,no_root_squash)'.format(network))    
    write('\n')


if out is not None:
    out.close()
    shutil.move(args.output + '.in-progress', args.output)


'''

if __name__ == '__main__':
    main()
