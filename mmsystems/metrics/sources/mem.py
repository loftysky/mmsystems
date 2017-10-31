import psutil

from ..core import Metrics


def get_metrics():

    raw_mem = psutil.virtual_memory()
    raw_swap = psutil.swap_memory()

    fields = {'mem_' + k: v for k, v in raw_mem._asdict().iteritems()}
    fields.update(('swap_' + k, v) for k, v in raw_swap._asdict().iteritems())

    return Metrics('mem', 'mem.{host}', fields=fields)
    
