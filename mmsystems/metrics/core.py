from time import time as _time
import socket


HOSTNAME = socket.gethostname().rsplit('.', 1)[0].replace('.', '_')

def gethostname():
    return HOSTNAME


class Metrics(object):

    def __init__(self, influx_name, graphite_pattern=None, tags=None, fields=None, time=None):
        self.influx_name = influx_name
        self.graphite_pattern = graphite_pattern
        self.tags = dict(tags or {})
        self.tags.setdefault('host', gethostname())
        self.fields = dict(fields or {})
        self.time = None

    def pprint_influx(self):
        print '{},{}'.format(self.influx_name, ','.join('{}={}'.format(k, v) for k, v in sorted(self.tags.iteritems())))
        for k, v in sorted(self.fields.iteritems()):
            print '    {}={}'.format(k, v)

    def pprint_graphite(self, **kwargs):
        for name, (_, value) in sorted(self.iter_graphite(**kwargs)):
            print '{} {}'.format(name, value)

    def iter_graphite(self, time=None, prefix='', **extra):
        if time is None:
            time = _time()
        for key, value in self.fields.iteritems():
            data = extra.copy()
            data.update(self.tags)
            basename = self.graphite_pattern.format(**data)
            name = '{}{}.{}'.format(prefix or '', basename, key)
            yield (name, (self.time or time, value))

    def format_influx(self, time=None):

        timestamp = int(1e9 * (time or _time()))

        name = self.influx_name
        if self.tags:
            name = '{},{}'.format(name, ','.join('{}={}'.format(k, v) for k, v in sorted(self.tags.iteritems()) if v is not None))

        return '{} {} {}'.format(
            name,
            ','.join('{}={}'.format(k, v) for k, v in sorted(self.fields.iteritems()) if v is not None),
            timestamp,
        )

