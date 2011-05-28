import signal
import threading
import time
from functools import partial

import xcb.xproto

import xpybutil.keysym as keysym
import xpybutil.icccm as icccm

import state
import events
import focus
import misc
import workspace

from config.keybind import keybinds

def init():
    for k in keybinds:
        key_string = k
        cmds = keybinds[k]

        if not isinstance(cmds, list):
            cmds = [cmds]
        
        for cmd in cmds:
            # I want to close over 'cmd', but it's mutable. I've used
            # a nastry trick that's explained here:
            # http://stackoverflow.com/questions/233673/lexical-closures-in-python/235764#235764
            if (isinstance(cmd, basestring) 
                and cmd.startswith('`') and cmd.endswith('`')):
                def callback(e, cmd=cmd):
                    misc.spawn(cmd[1:-1])
            else:
                def callback(e, cmd=cmd):
                    cmd()

            if not events.register_keypress(callback, state.root, key_string):
                print 'Could not bind %s to %s' % (key_string, cmd)

def spawn(exc, e):
    misc.spawn(exc)

def test1(e):
    focus.focused().decorate()

def test2(e):
    focus.focused().decorate(border=True)

def test3(e):
    focus.focused().decorate(slim=True)

def test4(e):
    focus.focused().undecorate()

def test5(e):
    client = focus.focused()

    if client:
        client.attention_start()

def test6(e):
    client = focus.focused()

    if client:
        client.attention_stop()

def test7(e):
    pass

def test8(e):
    pass

def test9(e):
    pass

def test0(e):
    pass

