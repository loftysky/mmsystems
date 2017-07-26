from __future__ import print_function

import sys
import socket
import cPickle as pickle
import struct


_socks = {}

def _get_sock(con, reopen=False):
    sock = _socks.get(con)
    if reopen or not sock:
        _socks[con] = sock = socket.create_connection(con)
    return sock


def send_many(con, metrics_iter, time=None, prefix=''):

    raw_payload = []
    for metric in metrics_iter:
        for row in metric.iter_graphite(time=time, prefix=prefix):
            raw_payload.append(row)
        
    encoded_payload = pickle.dumps(raw_payload, protocol=2)
    header = struct.pack('!L', len(encoded_payload))
    message = header + encoded_payload

    sock = _get_sock(con)
    try:
        sock.sendall(message)
    except Exception as e:
        print(e, file=sys.stderr)
        sock = _get_sock(con, reopen=True)
        sock.sendall(message)
