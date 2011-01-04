import keysym

import state

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

def start(begin, during, end, e):
    global __ondrag, __done

    __ondrag, __done = during, end
    __grab(begin(e) or 0)

def drag(e):
    global __ondrag, __done

    # If there are no callbacks registered, then ungrab!
    if not __ondrag or not __done:
        __ungrab()
        __ondrag = __done = None

    __ondrag(e)

def end(e):
    global __ondrag, __done

    __done(e)
    __ungrab()
    __ondrag = __done = None
