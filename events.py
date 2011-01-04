from collections import defaultdict
from functools import partial

import xcb.xproto

import ewmh
import keysym

import state
import drag

# The __events dictionary is keyed by the X event and then by window.
# Additional criteria (like key binding, mouse binding) can
# then be specified in a sub-dictionary
__events = defaultdict(defaultdict)

# This is what needs to be executed sparingly. For example, there may
# be several Expose events, but only one redraw event would be necessary.
# In this instance, normal callbacks will be executed for each Expose
# event, but each callback can register a latent callback (which will only
# be added once). Once the callbacks in this set are executed, the set
# is emptied.
__latent = set()

# A dictionary of grabbed keys/buttons, deyed by
# (modifiers, keycode, button) and assigned to a count that reflect the
# number of times that (m, k, b) has been grabbed. That way, keys should
# only be grabbed from the X server if the count is zero, and keys should
# only be ungrabbed from the X server if the count is zero.
__grabbed = defaultdict(int)

# Keeps track of the most recent time...
time = xcb.xproto.Time.CurrentTime

def __parse_keystring(key_string):
    modifiers = 0
    keycode = None

    for part in key_string.split('-'):
        if hasattr(xcb.xproto.KeyButMask, part):
            modifiers |= getattr(xcb.xproto.KeyButMask, part)
        else:
            keycode = keysym.lookup_string(state.conn, state.get_kbmap(),
                                           part.lower())

    return modifiers, keycode

def __parse_buttonstring(button_string):
    modifiers = 0
    button = None

    for part in button_string.split('-'):
        if hasattr(xcb.xproto.KeyButMask, part):
            modifiers |= getattr(xcb.xproto.KeyButMask, part)
        else:
            button = int(part)

    return modifiers, button

def register_callback(xevent, callback, wid, modifiers=None,
                      keycode=None, button=None):
    global __events

    try:
        for cb in callback:
            register_callback(xevent, cb, wid, modifiers, keycode, button)
    except TypeError:
        modkey = (modifiers, keycode, button)
        if wid not in __events[xevent]:
            __events[xevent][wid] = defaultdict(list)

        if callback not in __events[xevent][wid][modkey]:
            __events[xevent][wid][modkey].append(callback)

            return True

        return False

    return True

def unregister_callback(xevent, callback, wid, modifiers=None, keycode=None,
                        button=None):
    global __events

    modkey = (modifiers, keycode, button)

    try:
        callbacks = __events[xevent][wid][modkey]
    except KeyError:
        return False

    if callback not in callbacks:
        return False

    __events[xevent][wid][modkey].remove(callback)

    return True

def unregister_window(wid):
    global __events, __grabbed

    for xevent in __events:
        if wid in __events[xevent]:
            del __events[xevent][wid]

    # Events are removed from __events, now release all grabs...
    for wid2, modifiers, keycode, button in __grabbed:
        if wid2 != wid or __grabbed[(wid2, modifiers, keycode, button)] == 0:
            continue

        #if button is not None:
            #keysym.ungrab_button(state.conn, wid, modifiers, button)
        #elif keycode is not None:
            #keysym.ungrab_key(state.conn, wid, modifiers, keycode)

        __grabbed[(wid2, modifiers, keycode, button)] = 0

def __register_button(xevent, callback, wid, button_string, propagate=False,
                      grab=True):
    global __grabbed

    modifiers, button = __parse_buttonstring(button_string)
    modkey = (wid, modifiers, None, button)

    if not button:
        return False

    if grab:
        if (not __grabbed[modkey] and
            not keysym.grab_button(state.conn, wid, modifiers, button, propagate)):
            return False

        # Only increment this when we WANT a grab...
        __grabbed[modkey] += 1

    return register_callback(xevent, callback, wid, modifiers, None, button)

def register_drag(start, during, end, wid, button_string,
                  propagate=False, grab=True):
    register_buttonpress(partial(drag.start, start, during, end), wid,
                         button_string, propagate, grab)

def register_buttonpress(callback, wid, button_string, propagate=False,
                         grab=True):
    return __register_button(xcb.xproto.ButtonPressEvent, callback, wid,
                             button_string, propagate, grab)

def register_buttonmotion(callback, wid, button_string, propagate=False,
                          grab=True):
    return __register_button(xcb.xproto.MotionNotifyEvent, callback, wid,
                             button_string, propagate, grab)

def register_buttonrelease(callback, wid, button_string, propagate=False,
                           grab=True):
    return __register_button(xcb.xproto.ButtonReleaseEvent, callback, wid,
                             button_string, propagate, grab)

def __unregister_button(xevent, callback, wid, button_string):
    global __grabbed

    modifiers, button = __parse_buttonstring(button_string)
    modkey = (wid, modifiers, None, button)

    if not button:
        return False

    if not unregister_callback(xevent, callback, wid, modifiers, None,
                               button):
        return False

    if __grabbed[modkey] > 1:
        __grabbed[modkey] -= 1
    elif __grabbed[modkey] == 1:
        __grabbed[modkey] = 0

        if not keysym.ungrab_button(state.conn, wid, modifiers, button):
            return False
    else:
        return False

    return True

def unregister_buttonpress(callback, wid, button_string):
    return __unregister_button(xcb.xproto.ButtonPressEvent, callback, wid,
                               button_string)

def unregister_buttonmotion(callback, wid, button_string):
    return __unregister_button(xcb.xproto.MotionNotifyEvent, callback, wid,
                               button_string)

def unregister_buttonrelease(callback, wid, button_string):
    return __unregister_button(xcb.xproto.ButtonReleaseEvent, callback, wid,
                               button_string)

def __register_key(xevent, callback, wid, key_string):
    global __grabbed

    modifiers, keycode = __parse_keystring(key_string)
    modkey = (wid, modifiers, keycode, None)

    # If there's no valid key code, then there's no reason to register
    # an event callback...
    if not keycode:
        return False

    if (not __grabbed[modkey] and
        not keysym.grab_key(state.conn, wid, modifiers, keycode)):
        return False

    __grabbed[modkey] += 1

    return register_callback(xevent, callback, wid, modifiers, keycode, None)

def register_keypress(callback, wid, key_string):
    return __register_key(xcb.xproto.KeyPressEvent, callback, wid, key_string)

def register_keyrelease(callback, wid, key_string):
    return __register_key(xcb.xproto.KeyReleaseEvent, callback, wid,
                          key_string)

def __unregister_key(xevent, callback, wid, key_string):
    global __grabbed

    modifiers, keycode = __parse_keystring(key_string)
    modkey = (wid, modifiers, keycode, None)

    if not keycode:
        return False

    if not unregister_callback(xevent, callback, wid, modifiers, keycode,
                               None):
        return False

    if __grabbed[modkey] > 1:
        __grabbed[modkey] -= 1
    elif __grabbed[modkey] == 1:
        __grabbed[modkey] = 0

        if not keysym.ungrab_key(state.conn, wid, modifiers, keycode):
            return False
    else:
        return False

    return True

def unregister_keypress(callback, wid, key_string):
    return __unregister_key(xcb.xproto.KeyPressEvent, callback, wid,
                            key_string)

def unregister_keyrelease(callback, wid, key_string):
    return __unregister_key(xcb.xproto.KeyReleaseEvent, callback, wid,
                            key_string)

def register_latent_callback(callback):
    global __latent

    __latent.add(callback)

def run_latent():
    for latent in __latent:
        latent()

def dispatch(xevent):
    global time

    if not xevent:
        return False

    # Try to update the time...
    if hasattr(xevent, 'time'):
        time = xevent.time

    #state.debug_obj(xevent, True)
    #if hasattr(xevent, 'window'):
        #try:
            #state.debug(ewmh.get_wm_name(state.conn, xevent.window).reply())
        #except:
            #pass

    dname = 'dispatch_%s' % xevent.__class__.__name__
    if dname in globals():
        globals()[dname](xevent)
    #else:
        #state.debug(xevent)

    return True

def __dispatch_fetch_callbacks(xevent, wid, modifiers, keycode, button):
    if xevent not in __events:
        return []

    if wid not in __events[xevent] or not __events[xevent][wid]:
        return []

    modkey = (modifiers, keycode, button)

    # Return a copy in case we unregister in a callback
    return __events[xevent][wid].setdefault(modkey, [])[:]

def dispatch_ButtonPressEvent(e):
    if state.grab_pointer:
        mods = None
        button = None
    else:
        button = e.detail
        button_mask = getattr(xcb.xproto.KeyButMask, 'Button%d' % button)
        mods = e.state

        for mod in keysym.TRIVIAL_MODS + [button_mask]:
            mods &= ~mod

    cbs = __dispatch_fetch_callbacks(xcb.xproto.ButtonPressEvent, e.event,
                                     mods, None, button)

    for cb in cbs:
        cb(e=e)

def dispatch_ButtonReleaseEvent(e):
    if state.grab_pointer:
        mods = None
        button = None
    else:
        button = e.detail
        button_mask = getattr(xcb.xproto.KeyButMask, 'Button%d' % button)
        mods = e.state

        for mod in keysym.TRIVIAL_MODS + [button_mask]:
            mods &= ~mod

    cbs = __dispatch_fetch_callbacks(xcb.xproto.ButtonReleaseEvent,
                                     e.event, mods, None, button)

    for cb in cbs:
        cb(e=e)

def dispatch_MotionNotifyEvent(e):
    if state.grab_pointer:
        mods = None
        button = None
    else:
        mods = e.state
        button = None

        for i in xrange(1, 6):
            if mods & getattr(xcb.xproto.KeyButMask, 'Button%d' % i):
                button = i
                break

        if button is not None:
            button_mask = getattr(xcb.xproto.KeyButMask, 'Button%d' % button)
            for mod in keysym.TRIVIAL_MODS + [button_mask]:
                mods &= ~mod

    cbs = __dispatch_fetch_callbacks(xcb.xproto.MotionNotifyEvent, e.event,
                                     mods, None, button)

    for cb in cbs:
        cb(e=e)

def __dispatch_KeyEvent(e, xevent):
    keycode = e.detail
    mods = e.state
    for mod in keysym.TRIVIAL_MODS:
        mods &= ~mod

    cbs = __dispatch_fetch_callbacks(xevent, e.event, mods, keycode, None)

    for cb in cbs:
        cb(e=e)

def dispatch_KeyPressEvent(e):
    __dispatch_KeyEvent(e, xcb.xproto.KeyPressEvent)

def dispatch_KeyReleaseEvent(e):
    __dispatch_KeyEvent(e, xcb.xproto.KeyReleaseEvent)

def dispatch_ConfigureRequestEvent(e):
    cbs = __dispatch_fetch_callbacks(xcb.xproto.ConfigureRequestEvent,
                                     e.window, None, None, None)

    if not cbs:
        cbs = __dispatch_fetch_callbacks(xcb.xproto.ConfigureRequestEvent,
                                         e.parent, None, None, None)

    for cb in cbs:
        cb(e=e)

def dispatch_MapRequestEvent(e):
    cbs = __dispatch_fetch_callbacks(xcb.xproto.MapRequestEvent, e.window,
                                     None, None, None)

    if not cbs:
        cbs = __dispatch_fetch_callbacks(xcb.xproto.MapRequestEvent, e.parent,
                                         None, None, None)

    for cb in cbs:
        cb(e=e)

def dispatch_DestroyNotifyEvent(e):
    cbs = __dispatch_fetch_callbacks(xcb.xproto.DestroyNotifyEvent, e.window,
                                     None, None, None)

    for cb in cbs:
        cb(e=e)

def dispatch_UnmapNotifyEvent(e):
    cbs = __dispatch_fetch_callbacks(xcb.xproto.UnmapNotifyEvent, e.window,
                                     None, None, None)

    for cb in cbs:
        cb(e=e)

def dispatch_FocusInEvent(e):
    cbs = __dispatch_fetch_callbacks(xcb.xproto.FocusInEvent, e.event,
                                     None, None, None)

    for cb in cbs:
        cb(e=e)

def dispatch_FocusOutEvent(e):
    cbs = __dispatch_fetch_callbacks(xcb.xproto.FocusOutEvent, e.event,
                                     None, None, None)

    for cb in cbs:
        cb(e=e)

def dispatch_ExposeEvent(e):
    cbs = __dispatch_fetch_callbacks(xcb.xproto.ExposeEvent, e.window,
                                     None, None, None)

    for cb in cbs:
        cb(e=e)