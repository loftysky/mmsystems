import argparse
import json
import time as _time
from urlparse import urljoin

import requests

from ..core import Metrics


def main_query():

    parser = argparse.ArgumentParser()
    parser.add_argument('-U', '--url', default='http://influxdb.mm')
    parser.add_argument('query')
    args = parser.parse_args()

    url = urljoin(args.url, '/query')
    res = requests.post(url, data=dict(q=args.query))
    print json.dumps(res.json(), sort_keys=True, indent=4)


def main_write():

    parser = argparse.ArgumentParser()
    parser.add_argument('-U', '--url', default='http://influxdb.mm')
    parser.add_argument('-D', '--database', default='metrics')
    parser.add_argument('name')
    parser.add_argument('fields', nargs='+')
    args = parser.parse_args()

    fields = dict(x.split('=', 1) for f in args.fields)

    send_many(args.url, args.database, Metrics(args.name, fields=fields))



def send_many(base_url, database, metrics_iter, time=None):

    lines = []
    for metrics in metrics_iter:
        lines.append(metrics.format_influx(time=time))

    payload = ''.join(line + '\n' for line in lines)
    
    url = urljoin(base_url, '/write')
    res = requests.post(url, params=dict(db=database), data=payload, headers={
        'Content-Type': 'text/plain',
    })

    res.raise_for_status()

