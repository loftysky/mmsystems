from Queue import Queue
import threading

import paramiko


class SSHPool(object):

    def __init__(self, host, username='root', poolsize=8):
        self.client = paramiko.SSHClient()
        self.client.load_system_host_keys()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(host, username=username)
        self.sema = threading.Semaphore(poolsize)

    def exec_command(self, command):
        self.sema.acquire()
        in_, out, err = self.client.exec_command(command)
        in_.close()
        queue = Queue()
        thread = threading.Thread(target=self._watch_io, args=[out, err, queue])
        thread.daemon = True
        thread.start()
        return queue

    def _watch_io(self, out, err, queue):
        queue.put((out.read(), err.read()))
        self.sema.release()
