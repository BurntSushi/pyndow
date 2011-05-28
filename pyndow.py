from functools import partial
import sys
import time
import traceback

import xcb
import xcb.xproto as xproto

import xpybutil.util as util
import xpybutil.icccm as icccm
import xpybutil.ewmh as ewmh
import xpybutil.event as event

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

masks = [ xproto.EventMask.SubstructureNotify 
        | xproto.EventMask.SubstructureRedirect
        | xproto.EventMask.PropertyChange
        # | xproto.EventMask.FocusChange 
        ]
state.core.ChangeWindowAttributesChecked(state.root, xproto.CW.EventMask, 
                                         masks).check()

events.register_callback(xproto.ClientMessageEvent,
                         root.cb_ClientMessage, state.root)
events.register_callback(xproto.MappingNotifyEvent,
                         root.cb_MappingNotifyEvent, state.root)
events.register_callback(xproto.MapRequestEvent,
                         client.cb_MapRequestEvent, state.root)
events.register_callback(xproto.FocusInEvent,
                         client.cb_FocusInEvent, state.root)
events.register_callback(xproto.FocusOutEvent,
                         client.cb_FocusOutEvent, state.root)
events.register_callback(xproto.ConfigureRequestEvent,
                         window.cb_ConfigureRequestEvent, state.root)
events.register_callback(xproto.MotionNotifyEvent, grab.drag_do,
                         state.pyndow, None, None, None)
events.register_callback(xproto.ButtonReleaseEvent, grab.drag_end,
                         state.pyndow, None, None, None)

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
