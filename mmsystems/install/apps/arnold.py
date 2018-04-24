import argparse
import os
import subprocess
import sys

from mmsystems.sudo import reexec_sudo


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-V', '--maya-version', default='2018')
    parser.add_argument('--no-sudo', action='store_true')
    args = parser.parse_args()

    if not args.no_sudo:
        reexec_sudo()

    if sys.platform == 'darwin':
        subprocess.check_call(['installer',
            '-verbose',
            '-target', '/',
            '-pkg', '/Volumes/CGroot/systems/software/SolidAngle/MtoA-3.0.0.2-darwin-{}.pkg'.format(args.maya_version),
        ])
    else:
        subprocess.check_call([
            '/Volumes/CGroot/systems/software/SolidAngle/MtoA-3.0.0.2-linux-{}.run'.format(args.maya_version),
            'silent', # Accept the EULA, etc..
        ])


if __name__ == '__main__':
    main()
