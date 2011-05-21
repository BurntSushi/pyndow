import xcb.xproto

import state
import workspace

__stack = []

def get_stack():
    return __stack[:]

def add(client):
    if client not in __stack:
        __stack.append(client)
        return True
    return False

def remove(client):
    if client in __stack:
        __stack.remove(client)

def above(client):
    assert client in __stack

    __stack.remove(client)
    __stack.append(client)

def fallback():
    def fallbackable(c):
        return (c.mapped
                and (not c.workspaces or workspace.current() in c.workspaces))
    stck = [client for client in get_stack() if fallbackable(client)]

    # This is *really* important. On occasion, it seems that focus can stay
    # with a destroyed window. If this happens to be the last window, and
    # there is nothing left in the focus stack, we *must* fall back to the
    # root!
    if not stck:
        state.root_focus()
    else:
        client = stck[-1]

        # If the window isn't alive, pop the stack until we get a good window
        if client.is_alive():
            client.stack_raise()
            client.focus()
        else:
            remove(client)
            fallback()

def focused():
    stck = [client for client in get_stack() if client.mapped]

    if not stck:
        return None

    return stck[-1]

