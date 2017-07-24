import argparse
import json
import time

import requests



def main_query():

    parser = argparse.ArgumentParser()
    parser.add_argument('-H', '--host', default='influxdb.mm')
    parser.add_argument('query')
    args = parser.parse_args()

    res = requests.post('http://{}/query'.format(args.host), data=dict(q=args.query))
    print json.dumps(res.json(), sort_keys=True, indent=4)


def main_write():

    parser = argparse.ArgumentParser()
    parser.add_argument('-H', '--host', default='influxdb.mm')
    parser.add_argument('db')
    parser.add_argument('name')
    parser.add_argument('fields')
    args = parser.parse_args()

    res = requests.post('http://{}/write'.format(args.host), params=dict(db=args.db), data='{} {} {:d}'.format(
        args.name, args.fields, int(1e9 * time.time()),
    ))

    # TODO: Assert it was successful.
    # json.dumps(res.json(), sort_keys=True, indent=4)
