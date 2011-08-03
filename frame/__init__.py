import xcb.xproto

import xpybutil.ewmh as ewmh

import state
import events
import window
import focus
import config.mousebind as mousebind

def switch(old_frame, new_frame_cb):
    if isinstance(old_frame, new_frame_cb):
        return

    client = old_frame.client
    parent = old_frame.parent

    if not client.is_alive():
        return

    old_frame.switch_off()
    client.frame = new_frame_cb(client, parent)
    client.frame.switch_on()

class State:
    Active = 1
    Inactive = 2
    CatchAll = 3

class _FrameWindow(window.GeometryWindow):
    def __new__(cls, frame):
        self = window.GeometryWindow.__new__(cls)
        self.frame = frame

        return self

    def __init__(self):
        window.GeometryWindow.__init__(self, self.id)

    def destroy(self):
        events.unregister_window(self.id)
        state.conn.core.DestroyWindow(self.id)

    def clear(self):
        state.conn.core.ClearArea(0, self.id, 0, 0, 0, 0)

    def map(self):
        window.GeometryWindow.map(self)
        self.render()

    def render(self):
        pass

class Parent(_FrameWindow):
    def __new__(cls, frame):
        self = _FrameWindow.__new__(cls, frame)

        self.nada = False

        mask = xcb.xproto.CW.EventMask
        bg = self.frame.colors[self.frame.state]['bg']
        if bg == -1:
            self.nada = True
            mask |= xcb.xproto.CW.BackPixmap
            values = [xcb.xproto.BackPixmap.ParentRelative]
        else:
            mask |= xcb.xproto.CW.BackPixel
            values = [0]
        values.append(xcb.xproto.EventMask.SubstructureRedirect |
                      xcb.xproto.EventMask.ButtonPress |
                      xcb.xproto.EventMask.ButtonRelease)

        self.id = window.create(state.root, mask, values)

        return self

    def __init__(self, _):
        _FrameWindow.__init__(self)

        mousebind.register('frame', self, self.id)

    def render(self):
        if not self.nada:
            state.conn.core.ChangeWindowAttributes(
                self.id,
                xcb.xproto.CW.BackPixel,
                [self.frame.colors[State.Active]['thinborder']]
            )
        self.clear()

class _Frame(object):
    def __init__(self, client, parent):
        # Start activated?
        if focus.focused() == client:
            self.state = State.Active
        else:
            self.state = State.Inactive

        self.allowed_states = [State.Active, State.Inactive]

        self.client = client
        self.parent = parent or Parent(self)

        # State variables
        self.moving = None
        self.resizing = None

        if parent is None:
            state.conn.core.ReparentWindow(self.client.win.id, self.parent.id,
                                           self.pos['client']['x'],
                                           self.pos['client']['y'])
        else:
            parent.frame = self
            self.client.win.configure(x=self.pos['client']['x'],
                                      y=self.pos['client']['y'])

    def gravitize(self, x, y):
        retx = rety = None
        if x is None:
            retx = True
            x = 0
        if y is None:
            rety = True
            y =0

        nm = self.client.win.normal_hints

        g = nm['win_gravity']
        gr = xcb.xproto.Gravity

        if nm['flags']['PWinGravity'] and g != gr.NorthWest:
            if g in (gr.Static, gr.BitForget):
                x -= self.left
                y -= self.top
            elif g == gr.North:
                x -= abs(self.left - self.right) / 2
            elif g == gr.NorthEast:
                x -= self.left + self.right
            elif g == gr.East:
                x -= self.left + self.right
                y -= abs(self.top - self.bottom) / 2
            elif g == gr.SouthEast:
                x -= self.left + self.right
                y -= self.top + self.bottom
            elif g == gr.South:
                x -= abs(self.left - self.right) / 2
                y -= self.top + self.bottom
            elif g == gr.SouthWest:
                y -= self.top + self.bottom
            elif g == gr.West:
                y -= abs(self.top - self.bottom) / 2
            elif g == gr.Center:
                x -= abs(self.left - self.right) / 2
                y -= abs(self.top - self.bottom) / 2
            # else:
            #   NorthWest is already assumed

        return x if retx is None else None, y if rety is None else None

    # Ensures that the client gets its proper width/height
    # And gravitizes the x,y coordinates
    def configure_client(self, x=None, y=None, width=None, height=None,
                         border_width=None, sibling=None, stack_mode=None):
        x, y = self.gravitize(x, y)

        if width:
            width -= self.pos['client']['width']
        if height:
            height -= self.pos['client']['height']

        self.configure(x, y, width, height, border_width, sibling, stack_mode)

    def configure(self, x=None, y=None, width=None, height=None,
                  border_width=None, sibling=None, stack_mode=None,
                  ignore_hints=False):
        cw = ch = w = h = None

        # If resizing, update the client's size too. Make sure to use the
        # proper sizes based on the current frame, and validate!
        # Validation is used here so we know when to stop resizing the frame.
        # XXX: Does not handle x/y correctly when minimum size is reached.
        #      I don't think it's possible when the client is sending simple
        #      configure requests. Perhaps when I support _NET_WM_MOVERESIZE
        #      things will be better.
        if width or height:
            if width: 
                cw = width + self.pos['client']['width']
            if height: 
                ch = height + self.pos['client']['height']

            if not ignore_hints:
                w, h = self.client.win.validate_size(cw, ch)

                if w != cw:
                    width = (w - self.pos['client']['width'])

                if h != ch:
                    height = (h - self.pos['client']['height'])
            else:
                w, h = cw, ch

        # The order that the following two configures doesn't seem to matter.
        # Logically, it makes sense that when decreasing the size of a window,
        # we should resize the frame first and then the client. Vice versa
        # for when we increase the size of a window. But I can't really see
        # any visible difference... Hmmm...

        self.client.win.configure(x=self.pos['client']['x'],
                                  y=self.pos['client']['y'], width=w, height=h,
                                  ignore_hints=True)

        self.parent.configure(x, y, width, height, border_width, sibling,
                              stack_mode)

        # pass on the modified values...
        return x, y, width, height, border_width, sibling, stack_mode

    def validate_size(self, width, height):
        if width is not None:
            width += self.pos['client']['width']
        if height is not None:
            height += self.pos['client']['height']

        width, height = self.client.win.validate_size(width, height)

        if width is not None:
            width -= self.pos['client']['width']
        if height is not None:
            height -= self.pos['client']['height']

        return width, height

    def render(self):
        return self.client.is_alive()

    def set_state(self, st):
        assert st in self.allowed_states

        if self.state == st:
            return False
        self.state = st

        return True

    def switch_off(self):
        pass

    def switch_on(self):
        self.render()

    def map(self):
        self.parent.map()

    def unmap(self):
        state.conn.core.UnmapWindowChecked(self.parent.id).check()

    def unparent(self):
        state.conn.core.ReparentWindow(self.client.win.id, state.root,
                                       self.parent.geom['x'],
                                       self.parent.geom['y'])

    def destroy(self):
        self.unparent()
        #state.conn.core.DestroySubwindows(self.parent.id)
        state.conn.core.DestroyWindow(self.parent.id)


# Setup the available frames

import frames

Full = frames.Full
Border = frames.Border
SlimBorder = frames.SlimBorder
Nada = frames.Nada
