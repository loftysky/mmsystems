import os
import sys


def reexec_sudo():
    if os.getuid():
        os.execvp('sudo', ['sudo',
            'bash', '-c', 'source /usr/local/vee/environments/markmedia/master/etc/bashrc; exec "$0" "$@"',
            sys.executable,
        ] + sys.argv)
