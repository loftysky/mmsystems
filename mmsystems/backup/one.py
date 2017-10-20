import argparse
import os
import re
import subprocess

from ..ssh import SSHPool


normalize_types = dict(
    hdd='hdds',
    server='servers',
    workstation='workstations',
)


def request_mountpoint(ssh, volume):
    return ssh.exec_command('sudo zfs get mountpoint {}'.format(volume))

def get_mountpoint(queue, strict=True):
    out, err = queue.get()
    if (out and err) or not (out or err):
        raise ValueError("Malformed output from zfs.", out, err)
    if out:
        lines = out.splitlines()
        return lines[1].split()[2]
    if strict:
        raise ValueError(err.strip())


def backup_one(type, name, source, subdir='', host='nx02.mm', user='mmbackup', pool='crazyhorse',
    parent='backup', verbose=False, dry_run=False, delete=False):
    
    type = type.lower()
    type = normalize_types.get(type, type)

    for id_name, value in (
        ('name', name),
        ('type', type),
        ('pool', pool),
    ):
        if re.search(r'\W', value):
            raise ValueError('Invalid characters in identifier.', id_name, value)

    parent_name = '{}/{}/{}'.format(   pool, parent, type)
    volume_name = '{}/{}/{}/{}'.format(pool, parent, type, name)

    source = os.path.abspath(source)
    if not os.path.exists(source):
        raise ValueError("Source does not exist.", source)

    ssh = SSHPool(host, user)
    
    parent_mount_q = request_mountpoint(ssh, parent_name)
    volume_mount_q = request_mountpoint(ssh, volume_name)

    if not get_mountpoint(parent_mount_q, strict=False):
        raise ValueError("Invalid type or parent.", type, parent)

    mountpoint = get_mountpoint(volume_mount_q, strict=False)
    if mountpoint and verbose:
        print "Volume {} already exists.".format(volume_name)
    if not mountpoint and not dry_run:
        if verbose:
            print "Creating volume {} ...".format(volume_name)
        out, err = ssh.exec_command('sudo zfs create {}'.format(volume_name)).get()
        if err:
            raise ValueError(err)
        mountpoint = get_mountpoint(request_mountpoint(ssh, volume_name))
    
    if verbose and mountpoint:
        print "Backup located at {}".format(mountpoint)

    rsync = ['rsync',
        '-e', 'ssh -i {}/.ssh/id_rsa'.format(os.path.expanduser('~')),
        '--rsync-path', 'sudo rsync',
        '-ax', # The -x is *critical* to leave.
    ]
    if verbose:
        rsync.append('-vP')
    if delete:
        rsync.extend(('--delete', '--delete-excluded'))
    rsync.append(source + '/')

    if subdir:
        dest = '{}/{}'.format(mountpoint, subdir)
    else:
        dest = mountpoint
    rsync.append('{}:{}/'.format(host, dest))

    dest = os.path.join(mountpoint)
    if verbose:
        print '$', ' '.join(("'%s'" % x if ' ' in x else x) for x in rsync)

    rsync = ['sudo', '-p', 'sudo password: '] + rsync

    if not dry_run:
        subprocess.check_call(rsync)

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-N', '--dry_run', action='store_true')
    parser.add_argument('-D', '--delete', action='store_true')
    parser.add_argument('--host', default='nx02.mm')
    parser.add_argument('--user', default='mmbackup')
    parser.add_argument('--pool', default='crazyhorse')
    parser.add_argument('--parent', default='backup')
    parser.add_argument('-t', '--type', required=True)
    parser.add_argument('-n', '--name', required=True)
    parser.add_argument('-C', '--subdir')
    parser.add_argument('source')
    args = parser.parse_args()

    backup_one(**args.__dict__)


if __name__ == '__main__':
    main()
