import xcb.xproto

import state

__stack = []

def get_stack():
    return __stack

def add(win):
    global __stack

    assert win not in __stack

    __stack.append(win)

def remove(win):
    global __stack

    assert win in __stack

    __stack.remove(win)

def above(win):
    global __stack

    assert win in __stack

    __stack.remove(win)
    __stack.append(win)

def fallback():
    # This is *really* important. On occasion, it seems that focus can stay
    # with a destroyed window. If this happens to be the last window, and
    # there is nothing left in the focus stack, we *must* fall back to the
    # root!
    if not __stack:
        state.root_focus()
    else:
        win = __stack[-1]
        win.stack_raise()
        win.focus()

def focused():
    if not __stack:
        return None

    return __stack[-1]