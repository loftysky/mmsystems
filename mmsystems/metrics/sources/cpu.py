import psutil

from ..core import Metrics


def get_metrics():
    raw = psutil.cpu_times()
    return Metrics('cpu', 'cpu.{host}', fields=raw._asdict())
    
