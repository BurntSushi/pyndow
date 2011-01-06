import signal
import subprocess
import time
from functools import partial

import xcb.xproto

import keysym

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

        if cmd in globals():
            callback = globals()[cmd]

        if cmd.startswith('`') and cmd.endswith('`'):
            callback = partial(spawn, cmd[1:-1])

        if not callback or not events.register_keypress(callback,
                                                        state.root,
                                                        key_string):
            print 'Could not bind %s' % key_string

def spawn(exc, e):
    subprocess.Popen([exc]).pid

def toggle_catchall(e):
    focus.focused().toggle_catchall()

def test1(e):
    focus.focused().decorate()

def test2(e):
    focus.focused().decorate(border=True)

def test3(e):
    focus.focused().decorate(slim=True)

def test4(e):
    focus.focused().undecorate()

def test5(e):
    pass

def test6(e):
    pass

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

def down(e):
    state.debug('BUTTON DOWN')
    #events.unregister_keypress(down, state.root, 'f')
    events.unregister_buttonpress(down, state.root, '1')

def down2(e):
    state.debug('DOWN2')
    #events.unregister_keypress(down2, state.root, 'f')
    events.unregister_buttonpress(down2, state.root, '1')

def up(e):
    state.debug('BUTTON UP')
    #events.unregister_keyrelease(up, state.root, 'f')
    events.unregister_buttonrelease(up, state.root, '1')