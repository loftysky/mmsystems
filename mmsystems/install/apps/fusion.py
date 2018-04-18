from __future__ import print_function

from subprocess import check_call
import argparse
import os
import sys


def main_render():

    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--force', action='store_true',
        help="Install even if detected.")
    args = parser.parse_args()

    if not sys.platform.startswith('linux'):
        print("Can only be installed on Linux.")
        exit(1)

    if not args.force and os.path.exists('/opt/BlackmagicDesign/FusionRenderNode9/FusionRenderNode'):
        print("Already installed.")

    else:
        check_call(['sudo', 'yum', 'install', '-y',
            'fuse-libs', # For installer.
            'Xvfb', # For headless render.
        ])
        check_call(['sudo',
            '/Volumes/CGroot/systems/software/BlackMagic/Fusion-Studio/Blackmagic_Fusion_Render_Node_Linux_9.0.2_installer.run',
            '--install',
            '-y',
        ])

    farmsoup_line = '''WORKER_RESOURCES['fusion'] = 'Inf' # mminstall-fusion-render'''
    farmsoup_path = '/etc/farmsoup.py'
    farmsoup_done = os.path.exists(farmsoup_path) and farmsoup_line in open(farmsoup_path).read()
    if not farmsoup_done:
        check_call(['sudo', 'bash', '-c', 'echo "{}" >> {}'.format(farmsoup_line, farmsoup_path)])



if __name__ == '__main__':
    main_render()

