import xcb.xproto

import xpybutil.ewmh as ewmh
import xpybutil.image as image

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

from full import (ButtonBG, Close, Icon, Maximize, Minimize, Restore,
                  ThinBorder, Title, TitleBar)

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
        self.pos['close'] = {
            'x': -22,
            'y': self.__bw + 4,
            'width': 17,
            'height': 17
        }
        self.pos['maximize'] = {
            'x': self.pos['close']['x'] * 2,
            'y': self.pos['close']['y'],
            'width': self.pos['close']['width'],
            'height': self.pos['close']['height']
        }
        self.pos['restore'] = self.pos['maximize']
        self.pos['minimize'] = {
            'x': self.pos['close']['x'] * 3,
            'y': self.pos['close']['y'],
            'width': self.pos['close']['width'],
            'height': self.pos['close']['height']
        }
        self.pos['buttonbg'] = {
            'x': self.pos['minimize']['x'],
            'y': 0,
            'width': - self.pos['minimize']['x'],
            'height': self.__titleheight
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
                'buttonbg': config.get_option('frm_full_button_bg_a'),
                'buttonfg': config.get_option('frm_full_button_fg_a')
            },
            State.Inactive: { # inactive
                'bg': config.get_option('frm_full_bg_i'),
                'title': config.get_option('frm_full_title_i'),
                'thinborder': config.get_option('frm_thinborder_clr'),
                'bottomborder': config.get_option('frm_full_bottom_brdr_i'),
                'buttonbg': config.get_option('frm_full_button_bg_i'),
                'buttonfg': config.get_option('frm_full_button_fg_i')
            }
        }

        # Set the sizes of each side
        self.top = self.pos['client']['y']
        self.left = self.pos['client']['x']
        self.right = self.pos['right_side']['width']
        self.bottom = (self.pos['bottom_side']['height'] +
                       self.pos['bottom_border']['height'])

        _Frame.__init__(self, client, parent)

        # Put all the goodies underneath the borders and stuff
        self.title_bar = TitleBar(self)
        self.title = Title(self)
        self.buttonbg = ButtonBG(self) # Hides title if the window is too small
        self.close = Close(self)
        self.minimize = Minimize(self)
        self.restore = Restore(self)
        self.maximize = Maximize(self)
        self.icon = Icon(self)

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
        self.title_border = ThinBorder(self)
        self.bottom_border = ThinBorder(self)

        self.choose_maximized()

        self.configure_client(width=self.client.win.geom['width'],
                              height=self.client.win.geom['height'])

    def configure(self, x=None, y=None, width=None, height=None,
                  border_width=None, sibling=None, stack_mode=None,
                  ignore_hints=False):
        (x, y, width, height,
         border_width, sibling, stack_mode) = _Frame.configure(
            self, x, y, width, height, border_width, sibling, stack_mode,
            ignore_hints)

        if width:
            self.close.configure(
                x=width + self.pos['close']['x'])
            self.maximize.configure(
                x=width + self.pos['maximize']['x'])
            self.restore.configure(
                x=width + self.pos['restore']['x'])
            self.minimize.configure(
                x=width + self.pos['minimize']['x'])
            self.buttonbg.configure(
                x=width + self.pos['buttonbg']['x'])
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
        self.minimize.render()
        self.restore.render()
        self.maximize.render()
        self.close.render()
        self.buttonbg.render()
        self.icon.render()
        self.parent.render()

        self.choose_maximized()

        state.conn.flush()

    def choose_maximized(self):
        if self.client.maximized:
            self.restore.map()
            self.maximize.unmap()
        else:
            self.restore.unmap()
            self.maximize.map()

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
        self.maximize.destroy()
        self.restore.destroy()
        self.minimize.destroy()
        self.close.destroy()
        self.buttonbg.destroy()
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
            'height': self.__bw
        }
        self.pos['top_left'] = {
            'x': 0,
            'y': 0,
            'width': self.__crnr_sz,
            'height': self.__bw
        }
        self.pos['top_right'] = {
            'x': self.__crnr_sz,
            'y': 0,
            'width': self.__crnr_sz,
            'height': self.__bw
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
                  border_width=None, sibling=None, stack_mode=None,
                  ignore_hints=False):
        (x, y, width, height,
         border_width, sibling, stack_mode) = _Frame.configure(
            self, x, y, width, height, border_width, sibling, stack_mode,
            ignore_hints)

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
                'bg': config.get_option('frm_thinborder_clr'),
                'thinborder': config.get_option('frm_thinborder_clr')
            },
            State.Inactive: { # inactive
                'bg': config.get_option('frm_thinborder_clr'),
                'thinborder': config.get_option('frm_thinborder_clr')
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
                'bg': 0,
                'thinborder': 0
            },
            State.Inactive: { # inactive
                'bg': 0,
                'thinborder': 0
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
