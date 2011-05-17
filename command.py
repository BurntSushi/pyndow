import signal
import threading
import time
from functools import partial

import xcb.xproto

import keysym
import icccm

import state
import config
import events
import focus
import misc

save = None

def init():
    kbs = config.get_keybindings()
    for k in kbs:
        key_string = k
        cmd = kbs[k]
        callback = None

        if cmd not in ('init', 'spawn') and cmd in globals():
            callback = globals()[cmd]

        if cmd.startswith('`') and cmd.endswith('`'):
            callback = partial(spawn, cmd[1:-1])

        if not callback or not events.register_keypress(callback,
                                                        state.root,
                                                        key_string):
            print 'Could not bind %s' % key_string

def spawn(exc, e):
    misc.spawn(exc)

def focus_switcher(e):
    print 'Focus switcher!'

def toggle_catchall(e):
    focus.focused().toggle_catchall()

def toggle_decorations(e):
    client = focus.focused()

    if client:
        client.toggle_decorations()

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

#def test1(e):
    #client = focus.focused()
    #client.frame.title.set_text('hey-oh!')
    #client.frame.title.render()

#def test2(e):
    #client = focus.focused()
    #client.frame.title.set_text(client.win.wmname)
    #client.frame.title.render()

#def test3(e):
    #state.debug('Pyndow focus: %s, %d' % (str(focus.focused()), focus.focused().win.id))
    #state.debug('Real focus: %s' % state.conn.core.GetInputFocus().reply().focus)

def quit(e):
    state.die = True
    misc.spawn('killall Xephyr')

def close(e):
    client = focus.focused()
    if client:
        client.close()
