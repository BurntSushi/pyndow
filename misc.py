import os
import os.path
import subprocess

def spawn(exc):
    if isinstance(exc, basestring):
        exc = exc.split()
    devnull = open('/dev/null')
    return subprocess.Popen(exc, stdout=devnull, stderr=devnull).pid

def command(cmd, window, timeout=None, count=None):
    s = 'pyndow-cmd %s %d' % (cmd, window)
    if timeout:
        timeout /= 1000.0
        s += ' %0.3f' % timeout
    if count:
        s += ' %d' % count

    spawn(os.path.join(os.getenv('PWD'), s))
