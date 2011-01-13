import xcb.xproto

import state

__stack = []

def get_stack():
    return __stack

def add(client):
    assert client not in __stack

    __stack.append(client)

def remove(client):
    if client in __stack:
        __stack.remove(client)

def above(client):
    assert client in __stack

    __stack.remove(client)
    __stack.append(client)

def fallback():
    # This is *really* important. On occasion, it seems that focus can stay
    # with a destroyed window. If this happens to be the last window, and
    # there is nothing left in the focus stack, we *must* fall back to the
    # root!
    if not __stack:
        state.root_focus()
    else:
        client = __stack[-1]

        # If the window isn't alive, pop the stack until we get a good window
        if client.is_alive():
            client.stack_raise()
            client.focus()
        else:
            remove(client)
            fallback()

def focused():
    if not __stack:
        return None

    return __stack[-1]