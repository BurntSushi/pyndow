import xpybutil.keysym as keysym

import state

dragging = False
keying = False
grabbed_mods = 0
grabbed_keyc = 0

__ondrag = None
__done = None

def grab_exists():
    return state.grab_pointer or state.grab_keyboard

def grab(cursor=0):
    assert not grab_exists(), \
           'cannot grab when there is already a grab in place'
    keysym.grab_pointer(state.conn, state.pyndow, state.root, cursor)
    keysym.grab_keyboard(state.conn, state.pyndow)
    state.grab_pointer = state.grab_keyboard = True

def ungrab():
    keysym.ungrab_keyboard(state.conn)
    keysym.ungrab_pointer(state.conn)
    state.grab_pointer = state.grab_keyboard = False

def drag_start(begin, during, end, e):
    global __ondrag, __done, dragging

    if grab_exists():
        return

    status = begin(e)
    if status['grab']:
        __ondrag, __done = during, end
        grab(status.setdefault('cursor', 0))
        dragging = True

def drag_do(e):
    global __ondrag, __done, dragging

    # If there are no callbacks registered, then ungrab!
    if not __ondrag or not __done:
        ungrab()
        __ondrag = __done = None
        dragging = False
        return

    __ondrag(e)

def drag_end(e):
    global __ondrag, __done, dragging

    __done and __done(e)
    ungrab()
    __ondrag = __done = None
    dragging = False

def key_start(begin, end, (mods, keycode), e):
    global __done, keying, grabbed_mods, grabbed_keyc

    if grab_exists():
        return

    # It is actually very important to initiate the grab first, in an "act
    # first, ask questions later" type manner. This is due to a key release
    # event that should *end* the grab being generated before the grab can
    # take effect. This way, the grab is made as soon as possible, which
    # prevents ungrab events from sneaking by. Hopefully.
    grab(0)
    status = begin(e)
    if status['grab']:
        grabbed_mods, grabbed_keyc = mods, keycode
        __done = end
        ungrab() # Must grab again with proper settings
        grab(status.setdefault('cursor', 0))
        keying = True
    else:
        ungrab()

def key_do(dof, e):
    global __done, keying, grabbed_mods, grabbed_keyc

    # If there are no callbacks registered, then ungrab!
    if not __done:
        ungrab()
        __done = None
        grabbed_mods = grabbed_keyc = 0
        keying = False
        return

    dof(e)

def key_end(e):
    global __done, keying, grabbed_mods, grabbed_keyc

    __done and __done(e)
    ungrab()
    __done = None
    grabbed_mods = grabbed_keyc = 0
    keying = False

    state.conn.flush()
