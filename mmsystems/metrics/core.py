from time import time as _time
import socket


HOSTNAME = socket.gethostname().rsplit('.', 1)[0].replace('.', '_')

def gethostname():
    return HOSTNAME


class Metrics(object):

    def __init__(self, influx_name, graphite_base=None, tags=None, fields=None, time=None, graphite_name=None):
        self.influx_name = influx_name
        self.graphite_base = graphite_base
        self.graphite_name = graphite_name
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
        for field, value in self.fields.iteritems():
            data = extra.copy()
            data.update(self.tags)
            data.setdefault('field', field)
            if self.graphite_name:
                name = (prefix or '') + self.graphite_name.format(**data)
            else:
                basename = self.graphite_base.format(**data)
                name = '{}{}.{}'.format(prefix or '', basename, field)
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

