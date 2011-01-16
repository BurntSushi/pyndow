import keysym

import state

dragging = False
keying = False

__onkey = None
__ondrag = None
__done = None

def __grab(cursor):
    keysym.grab_pointer(state.conn, state.pyndow, state.root, cursor)
    keysym.grab_keyboard(state.conn, state.pyndow)
    state.grab_pointer = state.grab_keyboard = True

def __ungrab(force=False):
    keysym.ungrab_keyboard(state.conn)
    keysym.ungrab_pointer(state.conn)
    state.grab_pointer = state.grab_keyboard = False

def drag_start(begin, during, end, e):
    global __ondrag, __done, dragging

    dragging = True
    __ondrag, __done = during, end
    __grab(begin(e) or 0)

def drag_do(e):
    global __ondrag, __done, dragging

    # If there are no callbacks registered, then ungrab!
    if not __ondrag or not __done:
        __ungrab()
        __ondrag = __done = None
        dragging = False

    __ondrag(e)

def drag_end(e):
    global __ondrag, __done, dragging

    __done(e)
    __ungrab()
    __ondrag = __done = None
    dragging = False

def key_start(begin, during, end, e):
    global __onkey, __done, keying

    __onkey, __done = during, end
    __grab(begin(e) or 0)
    keying = True

def key_do(e):
    global __onkey, __done, keying

    # If there are no callbacks registered, then ungrab!
    if not __onkey or not __done:
        __ungrab()
        __onkey = __done = None
        keying = False

    __onkey(e)

def key_end(e):
    global __onkey, __done, keying

    __done(e)
    __ungrab()
    __onkey = __done = None
    keying = False
