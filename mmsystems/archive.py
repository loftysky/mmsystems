from __future__ import print_function

import argparse
import errno
import os
import re
import subprocess
import sys

import psutil
import yaml

from .smart import parse_info as parse_smart
from uindex.create import main as index_create_main


def makedirs(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

def ingest_main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--name')
    parser.add_argument('-d', '--description')
    parser.add_argument('-m', '--mountpoint', default='/Volumes/archive')
    parser.add_argument('-c', '--checksum', action='store_true')
    parser.add_argument('-y', '--yes', action='store_true',
        help="Assume 'yes' answers all questions.")
    parser.add_argument('-f', '--force', action='store_true',
        help="Proceed without caution.")
    parser.add_argument('root')
    args = parser.parse_args()

    mounts = psutil.disk_partitions(True)
    
    # Lets be super safe about what we are going.
    dst_mount = next((m for m in mounts if m.mountpoint == args.mountpoint), None)
    if not dst_mount:
        print("Archive is not mounted.", file=sys.stderr)
        exit(1)
    dst_root = os.path.join(args.mountpoint, 'ingest')
    if not os.path.exists(dst_root):
        print("Archive ingest is missing.", file=sys.stderr)
        exit(1)

    args.root = os.path.abspath(args.root)
    src_mount = next((m for m in mounts if m.mountpoint == args.root), None)
    if not src_mount:
        print("Source is not a mount.", file=sys.stderr)
        exit(1)

    print("Fetching SMART data...", file=sys.stderr)
    device = src_mount.device
    device = re.sub(r'(/dev/sd[a-z]+)\d*$', r'\1', device) # Linux
    device = re.sub(r'(/dev/disk\d+)(?:s\d+)?$', r'\1', device) # macOS
    
    try:
        smart_a = subprocess.check_output(['smartctl', '-a', device])
    except subprocess.CalledProcessError:
        print("WARNING: Cannot fetch SMART data!", file=sys.stderr)
        print("Enter the serial number (or enter to continue without): ", end='', file=sys.stderr)
        serial_number = raw_input().strip()
        has_smart = False
    else:
        # The next one is allowed to fail.
        smart_x = subprocess.Popen(['smartctl', '-x', device], stdout=subprocess.PIPE).communicate()[0]
        smart = parse_smart(smart_a)
        serial_number = smart['serial number']
        has_smart = True

    # Restore the name from serial number.
    if serial_number:
        by_serial_link = os.path.join(dst_root, '__by_serial__', serial_number)
        if not args.name and os.path.exists(by_serial_link):
            args.name = os.path.basename(os.readlink(by_serial_link))

    if not args.name and not args.yes:
        default = os.path.basename(args.root)
        default = re.sub(r'[^\w-]+', '-', default).strip('-')
        args.name = raw_input('Backup name [{}]: '.format(default)).strip() or default
    if re.search(r'[^\w-]+', args.name):
        print("Invalid name.", file=sys.stderr)
        exit(1)

    dst_dir = os.path.join(dst_root, args.name)
    meta_dir = os.path.join(dst_dir, '__mmbackup__')
    meta_path = os.path.join(meta_dir, 'metadata.yml')
    smart_pattern = os.path.join(meta_dir, 'smartctl,{}.txt')

    if args.checksum:
        checksum_path = os.path.join(meta_dir, 'index.txt')
        print("Writing checksums into {}".format(checksum_path))
        makedirs(meta_dir)
        index_create_main([
            '--verbose',
            '--auto-start',
            '--out', checksum_path,
            args.root
        ])
        return

    if os.path.exists(meta_path):

        print("Archive already exists.", file=sys.stderr)

        existing_metadata = list(yaml.load_all(open(meta_path).read()))[0]
        version = existing_metadata['version']
        if version != 1:
            raise ValueError("Unknown metadata version.", version)

        # Get the existing serial number.
        try:
            existing_smart = parse_smart(open(smart_pattern.format('a')).read())
        except IOError as e:
            existing_serial = existing_metadata.get('serial_number')
        else:
            existing_serial = existing_smart['serial number']

        if serial_number and existing_serial and existing_serial != serial_number:
            print("Existing archive is for another drive: {}".format(existing_serial), file=sys.stderr)
            if not args.force:
                print("Cannot continue without --force.", file=sys.stderr)
                exit(1)

        args.description = args.description or existing_metadata.get('description')

    if args.description is None and not args.yes:
        description = [raw_input("Description (enter blank line to finish): ").strip()]
        while description[-1]:
            description.append(raw_input().rstrip())
        args.description = '\n'.join(description)

    makedirs(os.path.dirname(meta_path))

    with open(meta_path, 'wb') as fh:
        fh.write(yaml.dump({
            'version': 1,
            'name': args.name,
            'description': args.description.strip(),
            'serial_number': serial_number,
        },
            explicit_start=False,
            indent=4,
            default_flow_style=False
        ))

    if has_smart:
        with open(smart_pattern.format('a'), 'wb') as fh:
            fh.write(smart_a)
        with open(smart_pattern.format('x'), 'wb') as fh:
            fh.write(smart_x)

    # Create the serial link.
    if serial_number and not os.path.exists(by_serial_link):
        makedirs(os.path.dirname(by_serial_link))
        os.symlink(dst_dir, by_serial_link)

    subprocess.call(['sudo', 'rsync',
        '-rlt',
        '--partial',
        '--progress',
        # '--exclude', '.DocumentRevisions-V100',
        # '--exclude', '.fseventsd',
        # '--exclude', '.Spotlight-V100',
        # '--exclude', '.TemporaryItems',
        # '--exclude', '.Trashes',
        '--exclude', '/.*',
        '--exclude', '.DS_Store',
        # '--delete-excluded',
        args.root + '/',
        dst_dir + '/',
    ])



