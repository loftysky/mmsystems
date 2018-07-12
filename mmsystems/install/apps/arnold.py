import argparse
import os
import subprocess
import sys

from mmsystems.sudo import reexec_sudo


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-V', '--maya-version', default='2018')
    parser.add_argument('-F', '--farmsoup', action='store_true')
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

    if args.farmsoup:
        for resource in (
            'arnold',
            'mtoa{}'.format(args.maya_version),
        ):
            farmsoup_line = '''WORKER_RESOURCES['{}'] = 'Inf' # mminstall-arnold'''.format(resource)
            farmsoup_path = '/etc/farmsoup.py'
            farmsoup_done = os.path.exists(farmsoup_path) and farmsoup_line in open(farmsoup_path).read()
            if not farmsoup_done:
                subprocess.check_call(['bash', '-c', 'echo "{}" >> {}'.format(farmsoup_line, farmsoup_path)])


if __name__ == '__main__':
    main()
