# coding: utf-8

import re
import subprocess

from . import utils
from ..core import Metrics



def iter_metrics():
    for m in iter_ipmitool():
        yield m
    for m in iter_lm_sensors():
        yield m

def iter_ipmitool():
    fans = []
    temps = {}

    currents = []
    powers = []

    proc = subprocess.Popen(['ipmitool', 'sensor'], stdout=subprocess.PIPE)
    for line in proc.stdout:

        if not line.strip():
            continue

        parts = line.lower().split('|')
        parts = [x.strip() for x in parts]
        parts = [None if x == 'na' else x for x in parts]

        name, value, unit, id_, low_non_recoverable, low_critital, low_warning, high_warning, high_critical, hi_warning = parts

        if value is None:
            continue
        if unit in ('degrees c', 'rpm', 'amps', 'volts', 'watts'):
            value = float(value)

        if name == 'ambient temp':
            temps.setdefault('ambient', []).append(value)

        elif name.startswith('fan') and unit == 'rpm':
            fans.append(value)

        elif name == 'current':
            currents.append(value)

        elif name == 'system level':
            powers.append(value)

    for type_, values in temps.items():
        yield Metrics('sensors.temp', 'sensors.temp.{host}.{type}', fields=dict(
            average=sum(values) / len(values),
            max=max(fans),
        ), tags=dict(
            type=type_,
        ))

    if fans:
        yield Metrics('sensors.fanspeed', 'sensors.fanspeed.{host}', fields=dict(
            max=max(fans),
            average=sum(fans) / len(fans),
        ))

    if currents:
        yield Metrics('sensors.current', graphite_name='sensors.current.{host}', fields=dict(
            total=sum(currents),
        ))

    if powers:
        yield Metrics('sensors.power', graphite_name='sensors.power.{host}', fields=dict(
            total=sum(powers),
        ))


def iter_lm_sensors():

    powers = []
    temps = {}

    proc = subprocess.Popen(['sensors'], stdout=subprocess.PIPE)
    for line in proc.stdout:

        if ':' not in line:
            continue

        name, rest = line.lower().split(':', 1)
        rest = rest.strip()

        m = re.match(r'\+?(\d[\d\.]*)\s*(°c|w)', rest)
        if m:
            value, unit = m.groups()
            value = float(value)
            unit = unit[-1]
        else:
            continue

        if name.startswith('power'):
            powers.append(value)

        elif name.startswith('physical') and unit == 'c':
            temps.setdefault('cpu', []).append(value)

        elif name.startswith('core') and unit == 'c':
            temps.setdefault('core', []).append(value)


    for type_, values in temps.items():
        yield Metrics('sensors.temp', 'sensors.temp.{host}.{type}', fields=dict(
            max=max(values),
            average=sum(values) / len(values),
        ), tags=dict(
            type=type_,
        ))

    if powers:
        yield Metrics('sensors.power', graphite_name='sensors.power.{host}', fields=dict(
            total=sum(powers),
        ))


