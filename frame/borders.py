from functools import partial

import xcb.xproto

import ewmh
import image

import state
import events
import rendering
import window

from frame import _FrameWindow

class _FrameBorder(_FrameWindow):
    def __new__(cls, frame, frm_ident, cursor, direction):
        self = _FrameWindow.__new__(cls, frame)

        mask = (xcb.xproto.CW.BackPixmap | xcb.xproto.CW.EventMask |
                xcb.xproto.CW.Cursor)
        values = [xcb.xproto.BackPixmap.ParentRelative,
                  xcb.xproto.EventMask.ButtonPress |
                    xcb.xproto.EventMask.ButtonRelease,
                  cursor]
        self.id = window.create(self.frame.parent.id, mask, values)

        self.frame = frame
        self.frm_ident = frm_ident
        self.cursor = cursor
        self.direction = direction

        return self

    def __init__(self, *_):
        _FrameWindow.__init__(self)

        self._imgs = dict([(st, None) for st in self.frame.allowed_states])

        self._img_w = self._img_h = None

        self.pos = {'x': self.frame.pos[self.frm_ident]['x'],
                    'y': self.frame.pos[self.frm_ident]['y'],
                    'width': self.frame.pos[self.frm_ident]['width'],
                    'height': self.frame.pos[self.frm_ident]['height']}

        events.register_drag(self.frame.client.cb_move_start,
                             self.frame.client.cb_move_drag,
                             self.frame.client.cb_move_end,
                             self.id, 'Mod4-1', grab=False)
        events.register_drag(partial(self.frame.client.cb_resize_start,
                                     direction=self.direction),
                             self.frame.client.cb_resize_drag,
                             self.frame.client.cb_resize_end,
                             self.id, '1', grab=False)

        # If this is a corner, then make sure normal resizing uses the
        # appropriate direction.
        if self.frm_ident.find('side') == -1:
            rs_start = partial(self.frame.client.cb_resize_start,
                               direction=self.direction)
        else:
            rs_start = self.frame.client.cb_resize_start

        events.register_drag(rs_start,
                             self.frame.client.cb_resize_drag,
                             self.frame.client.cb_resize_end,
                             self.id, 'Mod4-3', grab=False)

        self.setup()
        self.map()

    def setup(self):
        pass

    def render(self):
        assert self._img_w is not None and self._img_h is not None

        rendering.paint_pix(self.id, self._imgs[self.frame.state],
                            self._img_w, self._img_h)

class TopSide(_FrameBorder):
    def __new__(cls, frame):
        return _FrameBorder.__new__(cls, frame, 'top_side',
                                    state.cursors['TopSide'],
                                    ewmh.MoveResize.SizeTop)

    def __init__(self, _):
        _FrameBorder.__init__(self)

        self.configure(x=self.pos['x'], y=self.pos['y'],
                       height=self.pos['height'])

    def setup(self):
        self._img_w = 1
        self._img_h = self.pos['height']

        for st in self._imgs:
            self._imgs[st] = image.border(
                self.frame.colors[st]['thinborder'],
                self.frame.colors[st]['bg'],
                self._img_w, self._img_h, 'top')

class TopLeft(_FrameBorder):
    def __new__(cls, frame):
        return _FrameBorder.__new__(cls, frame, 'top_left',
                                    state.cursors['TopLeftCorner'],
                                    ewmh.MoveResize.SizeTopLeft)

    def __init__(self, _):
        _FrameBorder.__init__(self)

        self.configure(x=self.pos['x'], y=self.pos['y'],
                       height=self.pos['height'], width=self.pos['width'])

    def setup(self):
        self._img_w = self.pos['width']
        self._img_h = self.pos['height']

        for st in self._imgs:
            self._imgs[st] = image.corner(
                self.frame.colors[st]['thinborder'],
                self.frame.colors[st]['bg'],
                self._img_w, self._img_h, 'top_left')

class TopRight(_FrameBorder):
    def __new__(cls, frame):
        return _FrameBorder.__new__(cls, frame, 'top_right',
                                    state.cursors['TopRightCorner'],
                                    ewmh.MoveResize.SizeTopRight)

    def __init__(self, _):
        _FrameBorder.__init__(self)

        self.configure(y=self.pos['y'], height=self.pos['height'],
                       width=self.pos['width'])

    def setup(self):
        self._img_w = self.pos['width']
        self._img_h = self.pos['height']

        for st in self._imgs:
            self._imgs[st] = image.corner(
                self.frame.colors[st]['thinborder'],
                self.frame.colors[st]['bg'],
                self._img_w, self._img_h, 'top_right')

class BottomSide(_FrameBorder):
    def __new__(cls, frame):
        return _FrameBorder.__new__(cls, frame, 'bottom_side',
                                    state.cursors['BottomSide'],
                                    ewmh.MoveResize.SizeBottom)

    def __init__(self, _):
        _FrameBorder.__init__(self)

        self.configure(x=self.pos['x'], height=self.pos['height'])

    def setup(self):
        self._img_w = 1
        self._img_h = self.pos['height']

        for st in self._imgs:
            self._imgs[st] = image.border(
                self.frame.colors[st]['thinborder'],
                self.frame.colors[st]['bottomborder'],
                self._img_w, self._img_h, 'bottom')

class BottomLeft(_FrameBorder):
    def __new__(cls, frame):
        return _FrameBorder.__new__(cls, frame, 'bottom_left',
                                    state.cursors['BottomLeftCorner'],
                                    ewmh.MoveResize.SizeBottomLeft)

    def __init__(self, _):
        _FrameBorder.__init__(self)

        self.configure(x=self.pos['x'], height=self.pos['height'],
                       width=self.pos['width'])

    def setup(self):
        self._img_w = self.pos['width']
        self._img_h = self.pos['height']

        for st in self._imgs:
            self._imgs[st] = image.corner(
                self.frame.colors[st]['thinborder'],
                self.frame.colors[st]['bottomborder'],
                self._img_w, self._img_h, 'bottom_left')

class BottomRight(_FrameBorder):
    def __new__(cls, frame):
        return _FrameBorder.__new__(cls, frame, 'bottom_right',
                                    state.cursors['BottomRightCorner'],
                                    ewmh.MoveResize.SizeBottomRight)

    def __init__(self, _):
        _FrameBorder.__init__(self)

        self.configure(height=self.pos['height'], width=self.pos['width'])

    def setup(self):
        self._img_w = self.pos['width']
        self._img_h = self.pos['height']

        for st in self._imgs:
            self._imgs[st] = image.corner(
                self.frame.colors[st]['thinborder'],
                self.frame.colors[st]['bottomborder'],
                self._img_w, self._img_h, 'bottom_right')

class LeftSide(_FrameBorder):
    def __new__(cls, frame):
        return _FrameBorder.__new__(cls, frame, 'left_side',
                                    state.cursors['LeftSide'],
                                    ewmh.MoveResize.SizeLeft)

    def __init__(self, _):
        _FrameBorder.__init__(self)

        self.configure(x=self.pos['x'], y=self.pos['y'],
                       width=self.pos['width'])

    def setup(self):
        self._img_w = self.pos['width']
        self._img_h = 1

        for st in self._imgs:
            self._imgs[st] = image.border(
                self.frame.colors[st]['thinborder'],
                self.frame.colors[st]['bg'],
                self._img_w, self._img_h, 'left')

class LeftTop(_FrameBorder):
    def __new__(cls, frame):
        return _FrameBorder.__new__(cls, frame, 'left_top',
                                    state.cursors['TopLeftCorner'],
                                    ewmh.MoveResize.SizeTopLeft)

    def __init__(self, _):
        _FrameBorder.__init__(self)

        self.configure(x=self.pos['x'], y=self.pos['y'],
                       height=self.pos['height'], width=self.pos['width'])

    def setup(self):
        self._img_w = self.pos['width']
        self._img_h = self.pos['height']

        for st in self._imgs:
            self._imgs[st] = image.corner(
                self.frame.colors[st]['thinborder'],
                self.frame.colors[st]['bg'],
                self._img_w, self._img_h, 'left_top')

class LeftBottom(_FrameBorder):
    def __new__(cls, frame):
        return _FrameBorder.__new__(cls, frame, 'left_bottom',
                                    state.cursors['BottomLeftCorner'],
                                    ewmh.MoveResize.SizeBottomLeft)

    def __init__(self, _):
        _FrameBorder.__init__(self)

        self.configure(x=self.pos['x'], height=self.pos['height'],
                       width=self.pos['width'])

    def setup(self):
        self._img_w = self.pos['width']
        self._img_h = self.pos['height']

        for st in self._imgs:
            self._imgs[st] = image.corner(
                self.frame.colors[st]['thinborder'],
                self.frame.colors[st]['bg'],
                self._img_w, self._img_h, 'left_bottom')

class RightSide(_FrameBorder):
    def __new__(cls, frame):
        return _FrameBorder.__new__(cls, frame, 'right_side',
                                    state.cursors['RightSide'],
                                    ewmh.MoveResize.SizeRight)

    def __init__(self, _):
        _FrameBorder.__init__(self)

        self.configure(y=self.pos['y'], width=self.pos['width'])

    def setup(self):
        self._img_w = self.pos['width']
        self._img_h = 1

        for st in self._imgs:
            self._imgs[st] = image.border(
                self.frame.colors[st]['thinborder'],
                self.frame.colors[st]['bg'],
                self._img_w, self._img_h, 'right')

class RightTop(_FrameBorder):
    def __new__(cls, frame):
        return _FrameBorder.__new__(cls, frame, 'right_top',
                                    state.cursors['TopRightCorner'],
                                    ewmh.MoveResize.SizeTopRight)

    def __init__(self, _):
        _FrameBorder.__init__(self)

        self.configure(y=self.pos['y'], height=self.pos['height'],
                       width=self.pos['width'])

    def setup(self):
        self._img_w = self.pos['width']
        self._img_h = self.pos['height']

        for st in self._imgs:
            self._imgs[st] = image.corner(
                self.frame.colors[st]['thinborder'],
                self.frame.colors[st]['bg'],
                self._img_w, self._img_h, 'right_top')

class RightBottom(_FrameBorder):
    def __new__(cls, frame):
        return _FrameBorder.__new__(cls, frame, 'right_bottom',
                                    state.cursors['BottomRightCorner'],
                                    ewmh.MoveResize.SizeBottomRight)

    def __init__(self, _):
        _FrameBorder.__init__(self)

        self.configure(height=self.pos['height'], width=self.pos['width'])

    def setup(self):
        self._img_w = self.pos['width']
        self._img_h = self.pos['height']

        for st in self._imgs:
            self._imgs[st] = image.corner(
                self.frame.colors[st]['thinborder'],
                self.frame.colors[st]['bg'],
                self._img_w, self._img_h, 'right_bottom')
