from Queue import Queue
import os
import threading
import time
import traceback

from ..core import Metrics


def start(name, root, next_time, interval):

    if not os.path.exists(root):
        if not os.path.exists(os.path.dirname(root)):
            raise ValueError("Parent of iolag directory must exist.", root)
        os.makedirs(root)
    
    queue = Queue()
    thread = threading.Thread(target=_target, args=(queue, name, root, next_time, interval))
    thread.daemon = True
    thread.start()
    return queue

def _target(queue, name, root, next_time, interval):

    while True:

        now = time.time()
        while now > next_time:
            next_time += interval
        time.sleep(next_time - now)

        try:
            t1, t2, t3 = go(root)
        except Exception:
            traceback.print_exc()

        queue.put(Metrics('iolag', 'iolag.{name}.{host}', time=(t1 + t3) / 2, fields=dict(
            wtime=t2 - t1,
            rtime=t3 - t2,
        ), tags=dict(
            name=name,
        )))


def go(root):

    path = os.path.join(root, os.urandom(4).encode('hex'))
    content = os.urandom(16).encode('hex')

    try:

        t1 = time.time()
        with open(path, 'w') as fh:
            fh.write(content)

        t2 = time.time()

        with open(path, 'r') as fh:
            content2 = fh.read()

        t3 = time.time()

        return t1, t2, t3

    finally:
        os.unlink(path)

