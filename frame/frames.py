import xcb.xproto

import ewmh
import image

import config
import state
import events
import window
import rendering

from frame import _FrameWindow
from frame import Parent
from frame import _Frame
from frame import State

from borders import TopSide, BottomSide, LeftSide, RightSide
from borders import TopLeft, TopRight, BottomLeft, BottomRight
from borders import LeftTop, LeftBottom, RightTop, RightBottom

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
        for st in self._imgs:
            self._imgs[st], width, height = image.draw_text_bgcolor(
                txt, '/usr/share/fonts/TTF/DejaVuSans-Bold.ttf', 15,
                self.frame.colors[st]['bg'],
                self.frame.colors[st]['title'],
                self.pos['width'], self.pos['height']
            )

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
        icons = ewmh.get_wm_icon(state.conn, self.frame.client.win.id).reply()

        # Find a valid icon...
        # This code doesn't belong in here. It should be in client.
        icon = None

        # The EWMH way... find an icon closest to our desired size
        # Bigger is better!
        if icons:
            size = self.__icon_size(self.pos['width'], self.pos['height'])

            for icn in icons:
                if icon is None:
                    icon = icn
                else:
                    old = self.__icon_diff(icon['width'], icon['height'])
                    new = self.__icon_diff(icn['width'], icn['height'])

                    old_size = self.__icon_size(icon['width'], icon['height'])
                    new_size = self.__icon_size(icn['width'], icn['height'])

                    if ((new < old and new_size > old_size) or
                        (size > old_size and size < new_size)):
                        icon = icn

            if icon is not None:
                icon['data'] = image.parse_net_wm_icon(icon['data'])
                icon['mask'] = icon['data']

        # The ICCCM way...
        if (icon is None and
            self.frame.client.win.hints['flags']['IconPixmap'] and
            self.frame.client.win.hints['icon_pixmap'] is not None and
            self.frame.client.win.hints['icon_mask'] is not None):
            pixid = self.frame.client.win.hints['icon_pixmap']
            maskid = self.frame.client.win.hints['icon_mask']

            w, h, d = image.get_image_from_pixmap(state.conn, pixid)
            icon = {'width': w, 'height': h, 'data': d}

            _, _, icon['mask'] = image.get_image_from_pixmap(state.conn,
                                                             maskid)

        # Default icon...
        if icon is None:
            pass

        # Last resort... a simple solid box
        if icon is None or not icon['width'] or not icon['height']:
            for st in self._imgs:
                self._imgs[st] = image.box(self.frame.colors[st]['bg'],
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
            self._imgs[st] = image.blend(im, immask,
                                 self.frame.colors[st]['bg'],
                                 self.pos['width'], self.pos['height'])

    def render(self):
        rendering.paint_pix(self.id, self._imgs[self.frame.state],
                            self.pos['width'], self.pos['height'])

    def __icon_diff(self, icn_w, icn_h):
        return abs(self.pos['width'] - icn_w) + abs(self.pos['height'] - icn_h)

    def __icon_size(self, icn_w, icn_h):
        return icn_w * icn_h

class Full(_Frame):
    def __init__(self, client, parent=None):
        # Setup some hints and options before calling the parent constructor

        # Some size hints
        self.__bw = 1
        self.__bottom_bw = config.get_option('frm_full_bottom_brdr_sz')
        self.__titleheight = 26

        # Dictionary that determines the relative layout of each
        # window in the frame
        # NOTE: The values here can be both static and dynamic. For example,
        # a static position might be "2" whereas a dynamic position might be
        # "1/2". Whether a value is static or dynamic depends on how it is
        # used.
        self.pos = {
            'client': {'x': self.__bw, 'y': self.__bw + self.__titleheight,
                       'width': - (self.__bw * 2),
                       'height': - (self.__bw + self.__bottom_bw +
                                    self.__titleheight + 1)},
            'icon': {'x': self.__bw + 3, 'y': self.__bw + 3,
                     'width': 20, 'height': 20},
            'buttons': {'x': -75, 'y': 2, 'width': 75, 'height': 20},
        }
        self.pos['title_bar'] = {
            'x': 0,
            'y': 0,
            'width': 0,
            'height': self.__titleheight
        }
        self.pos['title'] = {
            'x': self.pos['icon']['x'] + self.pos['icon']['width'] + 2,
            'y': self.pos['icon']['y'] + 2,
            'width': 800, # Max width
            'height': 20 # Max height
        }
        self.pos['title_border'] = {
            'x': 0,
            'y': self.__titleheight,
            'width': 0,
            'height': 1
        }
        self.pos['bottom_border'] = {
            'x': 0,
            'y': self.__bw + self.__titleheight,
            'width': 0,
            'height': 1
        }
        self.pos['top_side'] = {
            'x': self.pos['title']['x'],
            'y': 0,
            'width': - (self.pos['title']['x'] * 2),
            'height': 5
        }
        self.pos['top_left'] = {
            'x': 0,
            'y': 0,
            'width': self.pos['title']['x'],
            'height': 5
        }
        self.pos['top_right'] = {
            'x': self.pos['top_left']['width'],
            'y': 0,
            'width': self.pos['title']['x'],
            'height': 5
        }
        self.pos['bottom_side'] = {
            'x': self.pos['title']['x'],
            'y': self.__bw + self.__titleheight + 1,
            'width': - (self.pos['title']['x'] * 2),
            'height': self.__bottom_bw
        }
        self.pos['bottom_left'] = {
            'x': 0,
            'y': 0,
            'width': self.pos['top_left']['width'],
            'height': self.pos['bottom_side']['height']
        }
        self.pos['bottom_right'] = {
            'x': self.pos['bottom_left']['width'],
            'y': 0,
            'width': self.pos['top_right']['width'],
            'height': self.pos['bottom_side']['height']
        }
        self.pos['left_side'] = {
            'x': 0,
            'y': self.__bw + self.__titleheight,
            'width': self.__bw,
            'height': - (2 * (self.__bw + self.__titleheight))
        }
        self.pos['left_top'] = {
            'x': 0,
            'y': 0,
            'width': 5,
            'height': self.pos['left_side']['y']
        }
        self.pos['left_bottom'] = {
            'x': 0,
            'y': self.pos['left_top']['height'],
            'width': self.__bw,
            'height': self.pos['left_side']['y']
        }
        self.pos['right_side'] = {
            'x': self.__bw,
            'y': self.__bw + self.__titleheight,
            'width': self.__bw,
            'height': - (2 * (self.__bw + self.__titleheight))
        }
        self.pos['right_top'] = {
            'x': self.__bw - 5,
            'y': 0,
            'width': 5,
            'height': self.pos['right_side']['y']
        }
        self.pos['right_bottom'] = {
            'x': self.__bw,
            'y': self.pos['right_top']['height'],
            'width': self.__bw,
            'height': self.pos['right_side']['y']
        }

        # Some colors...
        self.colors = {
            State.Active: { # active
                'bg': config.get_option('frm_full_bg_a'),
                'title': config.get_option('frm_full_title_a'),
                'thinborder': config.get_option('frm_thinborder_clr'),
                'bottomborder': config.get_option('frm_full_bottom_brdr_a'),
            },
            State.Inactive: { # inactive
                'bg': config.get_option('frm_full_bg_i'),
                'title': config.get_option('frm_full_title_i'),
                'thinborder': config.get_option('frm_thinborder_clr'),
                'bottomborder': config.get_option('frm_full_bottom_brdr_i'),
            }
        }

        # Set the sizes of each side
        self.top = self.pos['client']['y']
        self.left = self.pos['client']['x']
        self.right = self.pos['right_side']['width']
        self.bottom = (self.pos['bottom_side']['height'] +
                       self.pos['bottom_border']['height'])

        _Frame.__init__(self, client, parent)

        self.title_bar = TitleBar(self)
        self.top_side = TopSide(self)
        self.top_left = TopLeft(self)
        self.top_right = TopRight(self)
        self.bottom_side = BottomSide(self)
        self.bottom_left = BottomLeft(self)
        self.bottom_right = BottomRight(self)
        self.left_side = LeftSide(self)
        self.left_top = LeftTop(self)
        self.left_bottom = LeftBottom(self)
        self.right_side = RightSide(self)
        self.right_top = RightTop(self)
        self.right_bottom = RightBottom(self)
        self.title = Title(self)
        self.title_border = ThinBorder(self)
        self.bottom_border = ThinBorder(self)
        self.icon = Icon(self)

        self.configure_client(width=self.client.win.geom['width'],
                              height=self.client.win.geom['height'])

        # CHANGE THIS
        # This is bad because we're changing the width/height of the client
        # on map without good reason. This needs to be a function of the
        # current layout.
        #x, y = self.gravitize(client.win.geom['x'], client.win.geom['y'])
        #self.configure(
            #x=x, y=y,
            #width=client.win.geom['width'] - self.pos['client']['width'],
            #height=client.win.geom['height'] - self.pos['client']['height'])

    def configure(self, x=None, y=None, width=None, height=None,
                  border_width=None, sibling=None, stack_mode=None):
        (x, y, width, height,
         border_width, sibling, stack_mode) = _Frame.configure(
            self, x, y, width, height, border_width, sibling, stack_mode)

        if width:
            self.top_side.configure(
                width=width + self.pos['top_side']['width'])
            self.top_right.configure(
                x=self.pos['top_right']['x'] + self.top_side.geom['width'])
            self.bottom_side.configure(
                width=width + self.pos['bottom_side']['width'])
            self.bottom_right.configure(
                x=self.pos['bottom_right']['x'] +
                  self.bottom_side.geom['width'])
            self.right_side.configure(
                x=self.client.win.geom['width'] + self.pos['right_side']['x'])
            self.right_top.configure(
                x=self.pos['right_top']['x'] + self.right_side.geom['x'])
            self.right_bottom.configure(
                x=self.right_side.geom['x'])
            self.title_bar.configure(
                width=width + self.pos['title_bar']['width'])
            self.title_border.configure(
                width=width + self.pos['title_border']['width'])
            self.bottom_border.configure(
                width=width + self.pos['bottom_border']['width'])

        if height:
            self.bottom_side.configure(
                y=self.client.win.geom['height'] +
                  self.pos['bottom_side']['y'])
            self.bottom_left.configure(
                y=self.pos['bottom_left']['y'] + self.bottom_side.geom['y'])
            self.bottom_right.configure(
                y=self.pos['bottom_right']['y'] + self.bottom_side.geom['y'])
            self.left_side.configure(
                height=height + self.pos['left_side']['height'])
            self.left_bottom.configure(
                y=self.pos['left_bottom']['y'] + self.left_side.geom['height'])
            self.right_side.configure(
                height=height + self.pos['right_side']['height'])
            self.right_bottom.configure(
                y=self.pos['right_bottom']['y'] +
                  self.right_side.geom['height'])
            self.bottom_border.configure(
                y=self.client.win.geom['height'] +
                  self.pos['bottom_border']['y'])

    def render(self):
        if not _Frame.render(self):
            return

        self.title_bar.render()
        self.bottom_border.render()
        self.title_border.render()
        self.top_side.render()
        self.top_left.render()
        self.top_right.render()
        self.bottom_side.render()
        self.bottom_left.render()
        self.bottom_right.render()
        self.left_side.render()
        self.left_top.render()
        self.left_bottom.render()
        self.right_side.render()
        self.right_top.render()
        self.right_bottom.render()
        self.title.render()
        self.icon.render()
        self.parent.render()
        state.conn.flush()

    def set_state(self, st):
        if not _Frame.set_state(self, st):
            return

        self.render()

    def switch_off(self):
        self.bottom_border.destroy()
        self.title_border.destroy()
        self.right_bottom.destroy()
        self.right_top.destroy()
        self.right_side.destroy()
        self.left_bottom.destroy()
        self.left_top.destroy()
        self.left_side.destroy()
        self.bottom_right.destroy()
        self.bottom_left.destroy()
        self.bottom_side.destroy()
        self.top_right.destroy()
        self.top_left.destroy()
        self.top_side.destroy()
        self.title.destroy()
        self.title_bar.destroy()
        self.icon.destroy()

class Border(_Frame):
    def __init__(self, client, parent=None):
        # Setup some hints and options before calling the parent constructor

        # Some size hints
        self.__bw = config.get_option('frm_border_brdr_sz')
        self.__crnr_sz = self.__bw + 24

        self.pos = {
            'client': {'x': self.__bw, 'y': self.__bw,
                       'width': - (self.__bw * 2),
                       'height': - (self.__bw * 2)}
        }
        self.pos['top_side'] = {
            'x': self.__crnr_sz,
            'y': 0,
            'width': - (self.__crnr_sz * 2),
            'height': 5
        }
        self.pos['top_left'] = {
            'x': 0,
            'y': 0,
            'width': self.__crnr_sz,
            'height': 5
        }
        self.pos['top_right'] = {
            'x': self.__crnr_sz,
            'y': 0,
            'width': self.__crnr_sz,
            'height': 5
        }
        self.pos['bottom_side'] = {
            'x': self.__crnr_sz,
            'y': self.__bw,
            'width': - (self.__crnr_sz * 2),
            'height': self.__bw
        }
        self.pos['bottom_left'] = {
            'x': 0,
            'y': 0,
            'width': self.__crnr_sz,
            'height': self.__bw
        }
        self.pos['bottom_right'] = {
            'x': self.__crnr_sz,
            'y': 0,
            'width': self.__crnr_sz,
            'height': self.__bw
        }
        self.pos['left_side'] = {
            'x': 0,
            'y': self.__crnr_sz,
            'width': self.__bw,
            'height': - (self.__crnr_sz * 2)
        }
        self.pos['left_top'] = {
            'x': 0,
            'y': 0,
            'width': self.__bw,
            'height': self.__crnr_sz
        }
        self.pos['left_bottom'] = {
            'x': 0,
            'y': self.__crnr_sz,
            'width': self.__bw,
            'height': self.__crnr_sz
        }
        self.pos['right_side'] = {
            'x': self.__bw,
            'y': self.__crnr_sz,
            'width': self.__bw,
            'height': - (self.__crnr_sz * 2)
        }
        self.pos['right_top'] = {
            'x': self.__bw,
            'y': 0,
            'width': self.__bw,
            'height': self.__crnr_sz
        }
        self.pos['right_bottom'] = {
            'x': self.__bw,
            'y': self.__crnr_sz,
            'width': self.__bw,
            'height': self.__crnr_sz
        }

        # Some colors...
        self.colors = {
            State.Active: {
                'bg': config.get_option('frm_border_bg_a'),
                'thinborder': config.get_option('frm_border_thin_clr'),
                'bottomborder': config.get_option('frm_border_bg_a'),
            },
            State.Inactive: {
                'bg': config.get_option('frm_border_bg_i'),
                'thinborder': config.get_option('frm_border_thin_clr'),
                'bottomborder': config.get_option('frm_border_bg_i'),
            },
            State.CatchAll: {
                'bg': config.get_option('frm_border_bg_c'),
                'thinborder': config.get_option('frm_border_thin_clr'),
                'bottomborder': config.get_option('frm_border_bg_c'),
            }
        }

        # Set the sizes of each side
        self.top = self.pos['client']['y']
        self.left = self.pos['client']['x']
        self.right = self.pos['right_side']['width']
        self.bottom = self.pos['bottom_side']['height']

        _Frame.__init__(self, client, parent)

        # Add CatchAll to allowed states
        self.allowed_states.append(State.CatchAll)

        self.top_side = TopSide(self)
        self.top_left = TopLeft(self)
        self.top_right = TopRight(self)
        self.bottom_side = BottomSide(self)
        self.bottom_left = BottomLeft(self)
        self.bottom_right = BottomRight(self)
        self.left_side = LeftSide(self)
        self.left_top = LeftTop(self)
        self.left_bottom = LeftBottom(self)
        self.right_side = RightSide(self)
        self.right_top = RightTop(self)
        self.right_bottom = RightBottom(self)

        self.configure_client(width=self.client.win.geom['width'],
                              height=self.client.win.geom['height'])

    def configure(self, x=None, y=None, width=None, height=None,
                  border_width=None, sibling=None, stack_mode=None):
        (x, y, width, height,
         border_width, sibling, stack_mode) = _Frame.configure(
            self, x, y, width, height, border_width, sibling, stack_mode)

        if width:
            self.top_side.configure(
                width=width + self.pos['top_side']['width'])
            self.top_right.configure(
                x=self.pos['top_right']['x'] + self.top_side.geom['width'])
            self.bottom_side.configure(
                width=width + self.pos['bottom_side']['width'])
            self.bottom_right.configure(
                x=self.pos['bottom_right']['x'] +
                  self.bottom_side.geom['width'])
            self.right_side.configure(
                x=self.client.win.geom['width'] + self.pos['right_side']['x'])
            self.right_top.configure(
                x=self.right_side.geom['x'])
            self.right_bottom.configure(
                x=self.right_side.geom['x'])

        if height:
            self.bottom_side.configure(
                y=self.client.win.geom['height'] +
                  self.pos['bottom_side']['y'])
            self.bottom_left.configure(
                y=self.pos['bottom_left']['y'] + self.bottom_side.geom['y'])
            self.bottom_right.configure(
                y=self.pos['bottom_right']['y'] + self.bottom_side.geom['y'])
            self.left_side.configure(
                height=height + self.pos['left_side']['height'])
            self.left_bottom.configure(
                y=self.pos['left_bottom']['y'] + self.left_side.geom['height'])
            self.right_side.configure(
                height=height + self.pos['right_side']['height'])
            self.right_bottom.configure(
                y=self.pos['right_bottom']['y'] +
                  self.right_side.geom['height'])

    def render(self):
        if not _Frame.render(self):
            return

        self.top_side.render()
        self.top_left.render()
        self.top_right.render()
        self.bottom_side.render()
        self.bottom_left.render()
        self.bottom_right.render()
        self.left_side.render()
        self.left_top.render()
        self.left_bottom.render()
        self.right_side.render()
        self.right_top.render()
        self.right_bottom.render()
        self.parent.render()
        state.conn.flush()

    def set_state(self, st):
        if not _Frame.set_state(self, st):
            return

        self.render()

    def switch_off(self):
        self.right_bottom.destroy()
        self.right_top.destroy()
        self.right_side.destroy()
        self.left_bottom.destroy()
        self.left_top.destroy()
        self.left_side.destroy()
        self.bottom_right.destroy()
        self.bottom_left.destroy()
        self.bottom_side.destroy()
        self.top_right.destroy()
        self.top_left.destroy()
        self.top_side.destroy()

class SlimBorder(_Frame):
    def __init__(self, client, parent=None):
        # Setup some hints and options before calling the parent constructor

        # Some size hints
        self.__bw = 1

        self.pos = {
            'client': {'x': self.__bw, 'y': self.__bw,
                       'width': - (self.__bw * 2),
                       'height': - (self.__bw * 2)}
        }

        # Some colors...
        self.colors = {
            State.Active: { # active
                'bg': config.get_option('frm_thinborder_clr')
            },
            State.Inactive: { # inactive
                'bg': config.get_option('frm_thinborder_clr')
            }
        }

        # Set the sizes of each side
        self.top = self.left = self.right = self.bottom = self.__bw

        _Frame.__init__(self, client, parent)

        self.configure_client(width=self.client.win.geom['width'],
                              height=self.client.win.geom['height'])

    def render(self):
        if not _Frame.render(self):
            return

        self.parent.render()
        state.conn.flush()

    # No state changing necessary...
    def set_state(self, st):
        return

class Nada(_Frame):
    def __init__(self, client, parent=None):
        # Setup some hints and options before calling the parent constructor

        self.pos = {
            'client': {'x': 0, 'y': 0, 'width': 0, 'height': 0}
        }

        # Some colors... doesn't matter, they aren't seen
        self.colors = {
            State.Active: { # active
                'bg': -1
            },
            State.Inactive: { # inactive
                'bg': -1
            }
        }

        # Set the sizes of each side
        self.top = self.left = self.right = self.bottom = 0

        _Frame.__init__(self, client, parent)

        self.configure_client(width=self.client.win.geom['width'],
                              height=self.client.win.geom['height'])

    # No state changing necessary...
    def set_state(self, st):
        return