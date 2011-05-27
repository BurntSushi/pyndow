import signal
import threading
import time
from functools import partial

import xcb.xproto

import xpybutil.keysym as keysym
import xpybutil.icccm as icccm

import state
import config
import events
import focus
import misc
import workspace

save = None

def init():
    kbs = config.get_keybindings()
    for k in kbs:
        key_string = k
        cmds = kbs[k]
        callback = None
        
        for cmd in cmds:
            if cmd not in ('init', 'spawn') and cmd in globals():
                callback = globals()[cmd]

            if cmd.startswith('`') and cmd.endswith('`'):
                callback = partial(spawn, cmd[1:-1])

            if not callback or not events.register_keypress(callback,
                                                            state.root,
                                                            key_string):
                print 'Could not bind %s to %s' % (key_string, cmd)

def spawn(exc, e):
    misc.spawn(exc)

def tile(e):
    workspace.tile()

def untile(e):
    workspace.untile()

def workspace_left(e):
    workspace.left()

def workspace_right(e):
    workspace.right()

def workspace_with_left(e):
    client = focus.focused()
    if client:
        workspace.with_left(client)

def workspace_with_right(e):
    client = focus.focused()
    if client:
        workspace.with_right(client)

def focus_up(e):
    client = focus.focused()
    if client:
        client.layout().focus_up()

def focus_down(e):
    client = focus.focused()
    if client:
        client.layout().focus_down()

def focus_left(e):
    client = focus.focused()
    if client:
        client.layout().focus_left()

def focus_right(e):
    client = focus.focused()
    if client:
        client.layout().focus_right()

def master_increment(e):
    client = focus.focused()
    if client:
        client.layout().master_increment()

def master_decrement(e):
    client = focus.focused()
    if client:
        client.layout().master_decrement()

def master_size_decrease(e):
    client = focus.focused()
    if client:
        client.layout().master_size_decrease()

def master_size_increase(e):
    client = focus.focused()
    if client:
        client.layout().master_size_increase()

def previous(e):
    client = focus.focused()
    if client:
        client.layout().previous()

def next(e):
    client = focus.focused()
    if client:
        client.layout().next()

def move_previous(e):
    client = focus.focused()
    if client:
        client.layout().move_previous()

def move_next(e):
    client = focus.focused()
    if client:
        client.layout().move_next()

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
