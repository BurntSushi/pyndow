import xcb.xproto

import state

stdgc = state.conn.generate_id()
state.conn.core.CreateGC(stdgc, state.root, 0, [])

def paint_pix(wid, data, w, h):
    pix = state.conn.generate_id()
    state.conn.core.CreatePixmap(state.rsetup.root_depth, pix,
                                 state.root, w, h)

    state.conn.core.PutImage(xcb.xproto.ImageFormat.ZPixmap, pix, stdgc, w, h,
                             0, 0, 0, 24, len(data), data)

    state.conn.core.ChangeWindowAttributes(wid, xcb.xproto.CW.BackPixmap,
                                           [pix])

    state.conn.core.ClearArea(0, wid, 0, 0, 0, 0)

    state.conn.core.FreePixmap(pix)