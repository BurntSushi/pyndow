from functools import partial
import sys
import time
import traceback

import xcb, xcb.xproto

import util
import icccm
import ewmh
import event

import state
import root
import config
import window
import events
import grab
import command
import client
import misc

aid = partial(util.get_atom, state.conn)

util.build_atom_cache(state.conn, icccm)
util.build_atom_cache(state.conn, ewmh)

command.init()

state.conn.core.ChangeWindowAttributesChecked(
    state.root,
    xcb.xproto.CW.EventMask | xcb.xproto.CW.Cursor,
    [xcb.xproto.EventMask.SubstructureNotify |
     xcb.xproto.EventMask.SubstructureRedirect |
     xcb.xproto.EventMask.PropertyChange |
     xcb.xproto.EventMask.FocusChange, state.cursors['LeftPtr']]
).check()

events.register_callback(xcb.xproto.ClientMessageEvent,
                         root.cb_ClientMessage, state.root)
events.register_callback(xcb.xproto.MappingNotifyEvent,
                         root.cb_MappingNotifyEvent, state.root)
events.register_callback(xcb.xproto.MapRequestEvent,
                         client.cb_MapRequestEvent, state.root)
events.register_callback(xcb.xproto.FocusInEvent,
                         client.cb_FocusInEvent, state.root)
events.register_callback(xcb.xproto.FocusOutEvent,
                         client.cb_FocusOutEvent, state.root)
events.register_callback(xcb.xproto.ConfigureRequestEvent,
                         window.cb_ConfigureRequestEvent, state.root)
events.register_callback(xcb.xproto.MotionNotifyEvent, grab.drag_do,
                         state.pyndow, None, None, None)
events.register_callback(xcb.xproto.ButtonReleaseEvent, grab.drag_end,
                         state.pyndow, None, None, None)

def test_start(e):
    print '-' * 50, '\n', 'START\n', '-' * 50
def test_do(e):
    print '-' * 50, '\n', 'DO\n', '-' * 50
def test_done(e):
    print '-' * 50, '\n', 'DONE\n', '-' * 50

events.register_keygrab(test_start, test_do, test_done, state.root,
                        config.get_option('cycle'), 'Mod1-Alt_L')

state.root_focus()

while True:
    event.read(state.conn, block=True)
    for e in event.queue():
        events.dispatch(e)

    events.run_latent()

    state.conn.flush()

    if state.die:
        break

misc.spawn('killall Xephyr')