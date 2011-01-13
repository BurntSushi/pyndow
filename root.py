import util

import state

def cb_ClientMessage(e):
    if e.window in state.wins:
        state.debug(state.wins[e.window].win.wmname)

    state.debug(util.get_atom_name(state.conn, e.type))

    state.debug_obj(e, True)