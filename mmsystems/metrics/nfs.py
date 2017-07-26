import argparse
import json
import os
import re
import socket
import sys
import time
from subprocess import check_output

import psutil

from .core import Metrics

IS_MACOS = sys.platform == 'darwin'
IS_LINUX = not IS_MACOS


# NOTE: This is largely lifted from the statuspage package.

def get_metrics(server=False):

    data = {}
    lines = check_output(['nfsstat', '-s3' if server else '-c3']).splitlines()
    keys = None
    for line in lines:

        line = line.strip()
        if not line:
            continue

        # Skip headers.
        if line[-1] == ':':
            continue

        parts = line.strip().split()

        if not parts[0].isdigit(): # Keys!
            keys = parts
            continue

        # Sometimes there are percentages (that we ignore):
        #null         getattr       setattr       lookup        access       readlink     
        #822       0% 443225955 28% 683627589 43% 107789126  6% 19023042  1% 24851     0% 
        if parts[-1][-1] == '%':
            # Linux has percentages.
            parts = parts[0::2]

        values = map(int, parts)

        for k, v in zip(keys, values):
            data[k] = data.get(k, 0) + int(v)
            keys = None
    
    return Metrics('nfs', 'nfs.{type}.{host}', dict(
        type='server' if server else 'client',
    ), data)


if __name__ == '__main__':
    get_metrics(True).pprint_influx()
