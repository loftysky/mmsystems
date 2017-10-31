import psutil

from ..core import Metrics


def get_metrics():
    raw = psutil.net_io_counters()
    return Metrics('net.io', 'net.io.{host}', fields=raw._asdict())
    
