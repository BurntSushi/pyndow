from functools import partial

import xcb.xproto

import xpybutil.util as util
import xpybutil.keysym as keysym
import xpybutil.event as event

import state
import events

width = state.rsetup.width_in_pixels
height = state.rsetup.height_in_pixels

aname = partial(util.get_atom_name, state.conn)

def cb_ClientMessage(e):
    if e.window in state.windows:
        print state.windows[e.window].win.wmname
        print aname(e.type)
        print '-' * 45

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
    # Update the modifier mappings that may have changed
    elif e.request == xcb.xproto.Mapping.Modifier:
        state.set_keys_to_mods(keysym.get_keys_to_mods(state.conn))

