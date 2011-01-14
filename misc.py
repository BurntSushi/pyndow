import subprocess
from threading import Event, Thread
from time import sleep

def spawn(exc):
    if isinstance(exc, basestring):
        exc = exc.split()
    return subprocess.Popen(exc).pid

def command(cmd, window, timeout=None, count=None):
    s = './pyndow-cmd %s %d' % (cmd, window)
    if timeout:
        timeout /= 1000.0
        s += ' %0.3f' % timeout
    if count:
        s += ' %d' % count
    spawn(s)

# Not sure if I can use this... it yields strange results.
# X doesn't seem to cooperate...
class TimerRepeat(Thread):
    def __init__(self, interval, cb, *args, **kwargs):
        Thread.__init__(self)

        self.interval = interval
        self.cb = cb
        self.args = args
        self.kwargs = kwargs
        self.finished = Event()

    def run(self):
        while not self.finished.is_set():
            self.finished.wait(self.interval)
            if not self.finished.is_set():
                self.cb(*self.args, **self.kwargs)

    def cancel(self):
        self.finished.set()

