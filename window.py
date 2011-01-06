import struct

import xcb.xproto

import util
import icccm
import ewmh
import motif
import event

import state
import events
import layers
import focus

def create(parent, mask, values):
    wid = state.conn.generate_id()
    state.conn.core.CreateWindow(state.rsetup.root_depth, wid, parent, 0, 0, 1,
                                 1, 0, xcb.xproto.WindowClass.InputOutput,
                                 state.rsetup.root_visual,
                                 mask, values)

    return wid

class SimpleWindow(object):
    def __init__(self, wid):
        self.id = wid

    def map(self):
        state.conn.core.MapWindow(self.id)

    def unmap(self):
        state.conn.core.UnmapWindow(self.id)

    def configure(self, x=None, y=None, width=None, height=None,
                  border_width=None, sibling=None, stack_mode=None):
        mask = 0
        values = []
        conf = xcb.xproto.ConfigWindow

        if x is not None:
            self.geom['x'] = x

            mask |= conf.X

            if x < 0:
                x = 2 ** 32 - 1 + x
            values.append(x)
        if y is not None:
            self.geom['y'] = y

            mask |= conf.Y

            if y < 0:
                y = 2 ** 32 - 1 + y
            values.append(y)
        if width is not None:
            self.geom['width'] = width

            mask |= conf.Width

            if width <= 0:
                width = 1
            values.append(width)
        if height is not None:
            self.geom['height'] = height

            mask |= conf.Height

            if height <= 0:
                height = 1
            values.append(height)
        if border_width is not None:
            self.geom['border_width'] = border_width

            mask |= conf.BorderWidth
            values.append(border_width)
        if sibling is not None:
            mask |= conf.Sibling
            values.append(sibling)
        if stack_mode is not None:
            mask |= conf.StackMode
            values.append(stack_mode)

        state.conn.core.ConfigureWindow(self.id, mask, values)

class GeometryWindow(SimpleWindow):
    def __init__(self, wid):
        SimpleWindow.__init__(self, wid)

        self._geom = state.conn.core.GetGeometry(self.id)

    @property
    def geom(self):
        if isinstance(self._geom, xcb.xproto.GetGeometryCookie):
            self._geom = self._geom.reply()

            self._geom = {
                'x': self._geom.x, 'y': self._geom.y,
                'width': self._geom.width, 'height': self._geom.height,
                'border_width': self._geom.border_width,
                'depth': self._geom.depth
            }

        return self._geom

class Window(GeometryWindow):
    def __init__(self, wid):
        GeometryWindow.__init__(self, wid)

        self._protocols = icccm.get_wm_protocols(state.conn, self.id)
        self._hints = icccm.get_wm_hints(state.conn, self.id)
        self._normal_hints = icccm.get_wm_normal_hints(state.conn, self.id)
        self._class = icccm.get_wm_class(state.conn, self.id)
        self._motif = motif.get_hints(state.conn, self.id)
        self._wmname = ewmh.get_wm_name(state.conn, self.id)

    def desires_decor(self):
        if (self.motif and
            self.motif['flags']['Decorations']):
            if self.motif['decoration'] == motif.Decoration._None:
                return None
            elif (not self.motif['decoration'] & motif.Decoration.All and
                  not self.motif['decoration'] & motif.Decoration.Title and
                  not self.motif['decoration'] & motif.Decoration.ResizeH):
                return False

        return True

    @property
    def protocols(self):
        if isinstance(self._protocols, util.PropertyCookie):
            self._protocols = self._protocols.reply()

        return self._protocols

    @property
    def hints(self):
        if isinstance(self._hints, icccm.HintsCookie):
            self._hints = self._hints.reply()

        return self._hints

    @property
    def normal_hints(self):
        if isinstance(self._normal_hints, icccm.NormalHintsCookie):
            self._normal_hints = self._normal_hints.reply()

        return self._normal_hints

    @property
    def cls(self):
        if isinstance(self._class, util.PropertyCookie):
            self._class = self._class.reply()

        return self._class

    @property
    def motif(self):
        if isinstance(self._motif, motif.MotifHintsCookie):
            self._motif = self._motif.reply()

        return self._motif

    @property
    def wmname(self):
        if isinstance(self._wmname, util.PropertyCookie):
            self._wmname = self._wmname.reply()

        return self._wmname

def cb_ConfigureRequestEvent(e):
    values = []
    conf = xcb.xproto.ConfigWindow
    mask = e.value_mask

    if conf.X & mask:
        values.append(e.x)
    if conf.Y & mask:
        values.append(e.y)
    if conf.Width & mask:
        values.append(e.width)
    if conf.Height & mask:
        values.append(e.height)
    if conf.BorderWidth & mask:
        values.append(e.border_width)
    if conf.Sibling & mask:
        values.append(e.sibling)
    if conf.StackMode & mask:
        values.append(e.stack_mode)

    state.conn.core.ConfigureWindow(e.window, mask, values)