from functools import partial

import xcb.xproto

import util
import keysym
import event

import state
import events

aname = partial(util.get_atom_name, state.conn)

def cb_ClientMessage(e):
    if e.window in state.wins:
        print state.wins[e.window].win.wmname

    if aname(e.type) == '_PYNDOW_CMD':
        state.debug_obj(e)

# This only updates key codes at the moment
def cb_MappingNotifyEvent(e):
    newmap = keysym.get_keyboard_mapping(state.conn).reply()

    # Update the key codes that may have changed
    if e.request == xcb.xproto.Mapping.Keyboard:
        changes = {}

        for kc in xrange(*keysym.get_min_max_keycode(state.conn)):
            knew = keysym.get_keysym(state.conn, newmap, kc)
            oldkc = keysym.get_keycode(state.conn, state.get_kbmap(), knew)

            if oldkc != kc:
                changes[oldkc] = kc

        state.set_kbmap(newmap)
        events.regrab(changes)