from functools import partial

import util

import state

aname = partial(util.get_atom_name, state.conn)

def cb_ClientMessage(e):
    if e.window in state.wins:
        print state.wins[e.window].win.wmname

    if aname(e.type) == '_PYNDOW_CMD':
        state.debug_obj(e)