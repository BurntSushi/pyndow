import sys
import time

import xcb, xcb.xproto

import util
import icccm
import ewmh

import state
import config
import window
import events
import drag
import command
import client

icccm.build_atom_cache(state.conn)
ewmh.build_atom_cache(state.conn)

command.init()

state.conn.core.ChangeWindowAttributesChecked(
    state.root,
    xcb.xproto.CW.EventMask | xcb.xproto.CW.Cursor,
    [xcb.xproto.EventMask.SubstructureNotify |
     xcb.xproto.EventMask.SubstructureRedirect |
     xcb.xproto.EventMask.PropertyChange, state.cursors['LeftPtr']]
).check()

events.register_callback(xcb.xproto.MapRequestEvent,
                         client.cb_MapRequestEvent, state.root)
events.register_callback(xcb.xproto.ConfigureRequestEvent,
                         window.cb_ConfigureRequestEvent, state.root)
events.register_callback(xcb.xproto.MotionNotifyEvent, drag.drag, state.pyndow,
                         None, None, None)
events.register_callback(xcb.xproto.ButtonReleaseEvent, drag.end, state.pyndow,
                         None, None, None)

state.root_focus()

while True:
    event = state.conn.wait_for_event()
    events.dispatch(event)
    while events.dispatch(state.conn.poll_for_event()):
        pass

    events.run_latent()

    state.conn.flush()

    if state.die:
        break
