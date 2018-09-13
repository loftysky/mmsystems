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
    parser.add_argument('-v', '--verbose', action='count')

    parser.add_argument('-c', '--config', default='/etc/mmconfig/exports.py')

    parser.add_argument('-a', '--all', action='store_true',
        help="Same as `--nfs --smb`.")

    parser.add_argument('--common', action='store_true',
        help="Same as `-mfM`.")
    parser.add_argument('--nfs', action='store_true',
        help="Same as `-mfM -eE`.")
    parser.add_argument('--smb', '--samba', action='store_true',
        help="Same as `-mfM -sS`.")

    parser.add_argument('-m', '--mkdir', action='store_true',
        help="Make /export/VOLUME mount points.")
    parser.add_argument('-f', '--fstab', action='store_true',
        help="Modify /etc/fstab.")
    parser.add_argument('-M', '--mount', action='store_true',
        help="Auto-mount via `mount -a`.")

    parser.add_argument('-e', '--exports', action='store_true',
        help="Modify /etc/exports.")
    parser.add_argument('-E', '--exportfs', action='store_true',
        help="Reload exports via `exportfs -ra`.")

    parser.add_argument('-s', '--smb-conf', action='store_true',
        help="Modify /etc/samba/smb.conf.")
    parser.add_argument('-S', '--restart-smbd', action='store_true',
        help="Restart smbd.")


    args = parser.parse_args()

    if args.all:
        args.nfs = args.smb = True
    if args.nfs:
        args.common = True
        args.exports = args.exportfs = True
    if args.smb:
        args.common = True
        args.smb_conf = args.restart_smbd = True
    if args.common:
        args.mkdir = args.fstab = args.mount = True

    if not (
           args.dry_run
        or args.exportfs
        or args.exports
        or args.fstab
        or args.mkdir
        or args.mount
        or args.restart_smbd
        or args.smb_conf
    ):
        print("Nothing to do. Please use -a, -n, or one of -mfMeEsS.", file=sys.stderr)
        exit(1)

    if not os.path.exists(args.config):
        print("Could not find {}.".format(args.config), file=sys.stderr)
        exit(2)

    exports = {}
    def export(name, src_path, networks, **kwargs):
        
        if src_path != os.path.abspath(src_path):
            raise ValueError("Source paths must be absolute.", src_path)
        if not os.path.exists(src_path):
            raise ValueError("Source paths must exist.", src_path)

        if args.verbose:
            print('export({!r:20s}, {!r:40s}, networks={!r}{})'.format(name, src_path, networks,
                ''.join(',\n\t{}={!r}'.format(k, v) for k, v in sorted(kwargs.iteritems()))
            ))

        networks = resolve_networks(networks)

        if args.verbose > 1:
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
            new_networks.append(x)
        new_networks.sort()

        if args.verbose > 1:
            print('    compacted:', ', '.join(sorted(new_networks)))

        kwargs['src_path'] = src_path
        kwargs['networks'] = new_networks
        exports[name] = kwargs

    namespace = dict(
        export=export,
    )
    namespace.update({k.upper(): v for k, v in named_networks.items()})
    execfile(args.config, namespace)


    if args.mkdir:
        for name in exports:
            path = os.path.join('/export', name)
            if not os.path.lexists(path):
                if args.verbose:
                    print("mkdir {}".format(path))
                if not args.dry_run:
                    os.makedirs(path)

    if args.fstab:
        update_fstab(exports, verbose=args.verbose, dry_run=args.dry_run)

    if args.mount:
        if not args.dry_run:
            subprocess.check_call(['mount', '-a'])

    if args.exports:
        update_exports(exports, verbose=args.verbose, dry_run=args.dry_run)

    if args.exportfs:
        if not args.dry_run:
            subprocess.check_call(['exportfs', '-ra'])

    if args.smb_conf:
        update_smb_conf(exports, verbose=args.verbose, dry_run=args.dry_run)

    if args.restart_smbd:
        if not args.dry_run:
            subprocess.check_call(['systemctl', 'restart', 'smbd'])





def update_fstab(exports, verbose=False, dry_run=False):

    chunks = []

    for name, spec in sorted(exports.items()):
        chunks.append('{} /export/{} none bind\n'.format(spec['src_path'], name))


    config_str = ''.join(chunks)
    if verbose:
        print(config_str)

    if not dry_run:
        config = ConfigFile('/etc/fstab')
        config.set_content('mmnfs-exports', None) # Delete the old section.
        config.set_content('mmexports', config_str)
        config.dump()


def update_exports(exports, verbose=False, dry_run=False):

    chunks = []

    for name, spec in sorted(exports.items()):

        if not spec.get('nfs', True):
            continue

        chunks.append('/export/{}'.format(name))
        for network in spec['networks']:
            chunks.append(' \\\n\t{}(rw,nohide,insecure,no_subtree_check,async,no_root_squash)'.format(network))    
        chunks.append('\n')

    config_str = ''.join(chunks)
    if verbose:
        print(config_str)

    if not dry_run:
        config = ConfigFile('/etc/exports')
        config.set_content('mmnfs-exports', None) # Delete the old section.
        config.set_content('mmexports', config_str)
        config.dump()


def update_smb_conf(exports, verbose=False, dry_run=False):

    chunks = []

    for name, spec in sorted(exports.items(), key=lambda x: x[0].lower()):

        if not spec.get('smb', True):
            continue

        users = spec.get('users', [])
        groups = spec.get('groups', [])
        if not (users or groups):
            continue

        if isinstance(users, basestring):
            users = [x.strip() for x in users.split(',')]
        if isinstance(groups, basestring):
            groups = [x.strip() for x in groups.split(',')]
        users.extend('@' + x for x in groups)

        yes_no = lambda x: 'yes' if x else 'no'

        chunks.append('[{}]'.format(name))
        chunks.append('path = {}'.format(spec['src_path']))
        chunks.append('guest ok = {}'.format(yes_no(spec.get('guest_ok', False))))
        chunks.append('read only = {}'.format(yes_no(spec.get('read_only', False))))
        chunks.append('browseable = {}'.format(yes_no(spec.get('browseable', False))))
        chunks.append('valid users = {}'.format(' '.join(sorted(users))))

        # hosts_allow = []
        # for network in spec['networks']:

        #     if network.prefixlen == 32:
        #         hosts_allow.append(network.ip)
        #         continue

        #     ip_chunks = {8: 1, 16: 2, 24: 3}.get(network.prefixlen)
        #     if not ip_chunks:
        #         print("We can't represent {} in smb.conf.".format(network))
        #         continue

        #     hosts_allow.append('.'.join(str(network.ip).split('.')[:ip_chunks]) + '.')

        # chunks.append('hosts allow = {}'.format(' '.join(sorted(hosts_allow))))

        chunks.append('hosts allow = {}'.format(' '.join(map(str, sorted(spec['networks'])))))

        umask = spec.get('umask', 0o007)
        if isinstance(umask, basestring):
            umask = int(umask, 8)
        umask = umask & 0o777

        file_perms = 0o666 & ~umask
        chunks.append('create mask = 0{:03o}'.format(file_perms))
        chunks.append('force create mode = 0{:03o}'.format(file_perms))

        dir_perms = 0o777 & ~umask
        chunks.append('directory mask = 2{:03o}'.format(dir_perms))
        chunks.append('force directory mode = 2{:03o}'.format(dir_perms))

        # This is required for Excel on Windows for whatever reason.
        # In the same sentence on many sites, they also include:
        #     acl check permissions = no
        # but that doesn't seem required for us. I'm testing simply by saving
        # an empty Excel file to the volume.
        # This also doesn't seem to affect permissions in general, as I can
        # stil deny read/write via permission bits.
        chunks.append('nt acl support = {}'.format(yes_no(spec.get('nt_acl_support', False))))

        chunks.append('')

    config_str = '\n'.join(chunks)
    if verbose:
        print(config_str)

    if not dry_run:
        config = ConfigFile('/etc/samba/smb.conf')
        config.set_content('mmnfs-exports', None) # Delete the old section.
        config.set_content('mmexports', config_str)
        config.dump()




if __name__ == '__main__':
    main()
