import xcb, xcb.xproto

import Image, ImageDraw, ImageEnhance

import ewmh
import image

import state
import events
import window
import rendering

from frame import _FrameWindow

class Title(_FrameWindow):
    def __new__(cls, frame):
        self = _FrameWindow.__new__(cls, frame)
        self.id = window.create(self.frame.parent.id,
                          xcb.xproto.CW.BackPixmap,
                          [xcb.xproto.BackPixmap.ParentRelative])

        return self

    def __init__(self, _):
        _FrameWindow.__init__(self)

        self._imgs = dict([(st, None) for st in self.frame.allowed_states])
        self._fwidth = 0
        self._fheight = 0

        self.pos = {'x': self.frame.pos['title']['x'],
                    'y': self.frame.pos['title']['y'],
                    'width': self.frame.pos['title']['width'],
                    'height': self.frame.pos['title']['height']}

        self.configure(x=self.pos['x'], y=self.pos['y'],
                       height=self.pos['height'])

        events.register_drag(self.frame.client.cb_move_start,
                             self.frame.client.cb_move_drag,
                             self.frame.client.cb_move_end,
                             self.id, '1')

        self.set_text(self.frame.client.win.wmname)

        self.map()

    def set_text(self, txt):
        font_file = '/usr/share/fonts/TTF/DejaVuSans-Bold.ttf'
        font = rendering.create_font(font_file, 15)

        for st in self._imgs:
            im = rendering.draw_text_bgcolor(font, txt,
                                             self.frame.colors[st]['bg'],
                                             self.frame.colors[st]['title'],
                                             self.pos['width'],
                                             self.pos['height'])

            width, height = im.size
            self._imgs[st] = image.get_data(im)

        self._fwidth, self._fheight = width, height

        self.configure(width=self._fwidth)

    def render(self):
        rendering.paint_pix(self.id, self._imgs[self.frame.state],
                            self._fwidth, self._fheight)

class TitleBar(_FrameWindow):
    def __new__(cls, frame):
        self = _FrameWindow.__new__(cls, frame)
        self.id = window.create(self.frame.parent.id,
                          xcb.xproto.CW.BackPixel,
                          [self.frame.colors[self.frame.state]['bg']])

        return self

    def __init__(self, _):
        _FrameWindow.__init__(self)

        self.pos = {'x': self.frame.pos['title_bar']['x'],
                    'y': self.frame.pos['title_bar']['y'],
                    'width': self.frame.pos['title_bar']['width'],
                    'height': self.frame.pos['title_bar']['height']}

        self.configure(x=self.pos['x'], y=self.pos['y'],
                       height=self.pos['height'])

        events.register_drag(self.frame.client.cb_move_start,
                             self.frame.client.cb_move_drag,
                             self.frame.client.cb_move_end,
                             self.id, '1')

        self.map()

    def render(self):
        state.conn.core.ChangeWindowAttributes(
            self.id,
            xcb.xproto.CW.BackPixel,
            [self.frame.colors[self.frame.state]['bg']]
        )
        self.clear()

class ButtonBG(_FrameWindow):
    def __new__(cls, frame):
        self = _FrameWindow.__new__(cls, frame)
        self.id = window.create(self.frame.parent.id,
                          xcb.xproto.CW.BackPixel,
                          [self.frame.colors[self.frame.state]['bg']])

        return self

    def __init__(self, _):
        _FrameWindow.__init__(self)

        self.pos = {'x': self.frame.pos['buttonbg']['x'],
                    'y': self.frame.pos['buttonbg']['y'],
                    'width': self.frame.pos['buttonbg']['width'],
                    'height': self.frame.pos['buttonbg']['height']}

        self.configure(y=self.pos['y'], width=self.pos['width'],
                       height=self.pos['height'])

        self.map()

    def render(self):
        state.conn.core.ChangeWindowAttributes(
            self.id,
            xcb.xproto.CW.BackPixel,
            [self.frame.colors[self.frame.state]['bg']]
        )
        self.clear()

class ThinBorder(_FrameWindow):
    def __new__(cls, frame):
        self = _FrameWindow.__new__(cls, frame)
        self.id = window.create(self.frame.parent.id,
                          xcb.xproto.CW.BackPixel,
                          [self.frame.colors[self.frame.state]['thinborder']])

        return self

    def __init__(self, _):
        _FrameWindow.__init__(self)

        self.pos = {'x': self.frame.pos['title_border']['x'],
                    'y': self.frame.pos['title_border']['y'],
                    'width': self.frame.pos['title_border']['width'],
                    'height': self.frame.pos['title_border']['height']}

        self.configure(x=self.pos['x'], y=self.pos['y'],
                       height=self.pos['height'])

        events.register_drag(self.frame.client.cb_move_start,
                             self.frame.client.cb_move_drag,
                             self.frame.client.cb_move_end,
                             self.id, '1')

        self.map()

    def render(self):
        state.conn.core.ChangeWindowAttributes(
            self.id,
            xcb.xproto.CW.BackPixel,
            [self.frame.colors[self.frame.state]['thinborder']]
        )
        self.clear()

class _WindowButton(_FrameWindow):
    def __new__(cls, frame, ident):
        self = _FrameWindow.__new__(cls, frame)
        self.id = window.create(self.frame.parent.id,
                          xcb.xproto.CW.BackPixmap | xcb.xproto.CW.EventMask,
                          [xcb.xproto.BackPixmap.ParentRelative,
                           xcb.xproto.EventMask.ButtonPress |
                           xcb.xproto.EventMask.ButtonRelease |
                           xcb.xproto.EventMask.EnterWindow |
                           xcb.xproto.EventMask.LeaveWindow])

        self.ident = ident

        return self

    def __init__(self, *_):
        _FrameWindow.__init__(self)

        self._imgs = {st: {'normal': None, 'hover': None, 'click': None}
                      for st in self.frame.allowed_states}
        self._secondary = set()

        self.pos = {'x': self.frame.pos[self.ident]['x'],
                    'y': self.frame.pos[self.ident]['y'],
                    'width': self.frame.pos[self.ident]['width'],
                    'height': self.frame.pos[self.ident]['height']}

        self.configure(y=self.pos['y'], width=self.pos['width'],
                       height=self.pos['height'])

        events.register_callback(xcb.xproto.EnterNotifyEvent,
                                 self.cb_enter, self.id)
        events.register_callback(xcb.xproto.LeaveNotifyEvent,
                                 self.cb_leave, self.id)
        events.register_buttonpress(self.cb_buttonpress, self.id, '1',
                                    grab=False)
        events.register_buttonrelease([self.cb_buttonrelease, self.cb_action],
                                      self.id, '1', grab=False)

        self.setup()
        self.map()

    # Defined in sub-class!
    def cb_action(self, e):
        return 'hover' in self._secondary

    def cb_enter(self, e):
        self._secondary.add('hover')

        if 'click' not in self._secondary:
            self.render()

    def cb_leave(self, e):
        if 'hover' not in self._secondary:
            return

        self._secondary.remove('hover')

        if 'click' not in self._secondary:
            self.render()

    def cb_buttonpress(self, e):
        self._secondary.add('click')

        self.render()

    def cb_buttonrelease(self, e):
        if 'click' not in self._secondary:
            return

        self._secondary.remove('click')

        self.render()

    def setup(self):
        for st in self._imgs:
            w, h = self.pos['width'], self.pos['height']
            x = (w - self._img_source.size[0]) / 2
            y = (h - self._img_source.size[1]) / 2

            buttonbg = image.hex_to_rgb(self.frame.colors[st]['buttonbg'])
            buttonfg = image.hex_to_rgb(self.frame.colors[st]['buttonfg'])

            # Create the "base" image
            normal = Image.new('RGBA', (w, h), color=buttonbg)
            normal.paste(self._img_source, box=(x, y), mask=self._img_source)

            imgd = ImageDraw.Draw(normal)
            imgd.bitmap((x, y), self._img_source, fill=buttonfg)

            # Make other two states before beveling
            hover = normal.copy()
            click = normal.copy()

            # Now add effects that differentiate the states
            rendering.bevel_up(normal)

            bright = ImageEnhance.Brightness(click)
            click = bright.enhance(1.2)
            rendering.bevel_down(click)

            bright = ImageEnhance.Brightness(hover)
            hover = bright.enhance(1.2)
            rendering.bevel_up(hover)

            self._imgs[st]['normal'] = image.get_data(normal)
            self._imgs[st]['click'] = image.get_data(click)
            self._imgs[st]['hover'] = image.get_data(hover)

    def render(self):
        imgs = self._imgs[self.frame.state]
        img = imgs['normal']
        if 'click' in self._secondary:
            img = imgs['click']
        elif 'hover' in self._secondary:
            img = imgs['hover']

        rendering.paint_pix(self.id, img, self.pos['width'],
                            self.pos['height'])

class Close(_WindowButton):
    def __new__(cls, frame):
        return _WindowButton.__new__(cls, frame, 'close')

    def __init__(self, *_):
        self._img_source = rendering.close

        _WindowButton.__init__(self)

    def cb_action(self, e):
        if not _WindowButton.cb_action(self, e):
            return

        self.frame.client.close()

class Maximize(_WindowButton):
    def __new__(cls, frame):
        return _WindowButton.__new__(cls, frame, 'maximize')

    def __init__(self, *_):
        self._img_source = rendering.maximize

        _WindowButton.__init__(self)

    def cb_action(self, e):
        if not _WindowButton.cb_action(self, e):
            return

        self.frame.client.maximized = True

        # I shouldn't need this here in the future, since the process of
        # *actually* maximizing a window should render the frame at some point.
        self.frame.render()

class Restore(_WindowButton):
    def __new__(cls, frame):
        return _WindowButton.__new__(cls, frame, 'restore')

    def __init__(self, *_):
        self._img_source = rendering.restore

        _WindowButton.__init__(self)

    def cb_action(self, e):
        if not _WindowButton.cb_action(self, e):
            return

        self.frame.client.maximized = False

        # I shouldn't need this here in the future, since the process of
        # *actually* maximizing a window should render the frame at some point.
        self.frame.render()

class Minimize(_WindowButton):
    def __new__(cls, frame):
        return _WindowButton.__new__(cls, frame, 'minimize')

    def __init__(self, *_):
        self._img_source = rendering.minimize

        _WindowButton.__init__(self)

    def cb_action(self, e):
        if not _WindowButton.cb_action(self, e):
            return

        self.frame.client.minimize()

class Icon(_FrameWindow):
    def __new__(cls, frame):
        self = _FrameWindow.__new__(cls, frame)
        self.id = window.create(self.frame.parent.id,
                          xcb.xproto.CW.BackPixmap,
                          [xcb.xproto.BackPixmap.ParentRelative])

        return self

    def __init__(self, _):
        _FrameWindow.__init__(self)

        self._imgs = dict([(st, None) for st in self.frame.allowed_states])

        self.pos = {'x': self.frame.pos['icon']['x'],
                    'y': self.frame.pos['icon']['y'],
                    'width': self.frame.pos['icon']['width'],
                    'height': self.frame.pos['icon']['height']}

        self.configure(x=self.pos['x'], y=self.pos['y'],
                       width=self.pos['width'], height=self.pos['height'])

        events.register_drag(self.frame.client.cb_move_start,
                             self.frame.client.cb_move_drag,
                             self.frame.client.cb_move_end,
                             self.id, '1')

        self.setup()

        self.map()

    def setup(self):
        icon = self.frame.client.win.get_icon(self.pos['width'],
                                              self.pos['height'])

        # If for some reason we couldn't get an icon...
        if icon is None or not icon['width'] or not icon['height']:
            for st in self._imgs:
                self._imgs[st] = rendering.box(self.frame.colors[st]['bg'],
                                               self.pos['width'],
                                               self.pos['height'])

            return

        # Blending time... yuck
        im = image.get_image(icon['width'], icon['height'], icon['data'])
        im = im.resize((self.pos['width'], self.pos['height']))

        if 'mask' in icon and icon['mask'] and icon['mask'] != icon['data']:
            immask = image.get_bitmap(icon['width'], icon['height'],
                                      icon['mask'])
            immask = immask.resize((self.pos['width'], self.pos['height']))
        else:
            immask = im.copy()

        for st in self._imgs:
            im = rendering.blend(im, immask, self.frame.colors[st]['bg'],
                                 self.pos['width'], self.pos['height'])

            self._imgs[st] = image.get_data(im)

    def render(self):
        rendering.paint_pix(self.id, self._imgs[self.frame.state],
                            self.pos['width'], self.pos['height'])

