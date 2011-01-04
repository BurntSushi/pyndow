from functools import partial
import traceback

import xcb.xproto
import Image

import ewmh
import image
import keysym

import config
import state
import events
import window
import focus
import rendering

def _create(parent, mask, values):
    wid = state.conn.generate_id()
    state.conn.core.CreateWindow(state.rsetup.root_depth, wid, parent, 0, 0, 1,
                                 1, 0, xcb.xproto.WindowClass.InputOutput,
                                 state.rsetup.root_visual,
                                 mask, values)

    return wid

def switch(old_frame, new_frame_cb):
    client = old_frame.client
    parent = old_frame.parent

    old_frame.switch_off()
    client.frame = new_frame_cb(client, parent)
    client.frame.switch_on()

class _FrameWindow(window.GeometryWindow):
    def __new__(cls, frame):
        self = window.GeometryWindow.__new__(cls, frame)
        self.frame = frame

        return self

    def __init__(self):
        window.GeometryWindow.__init__(self, self.id)

    def destroy(self):
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
        self.id = _create(state.root,
                          xcb.xproto.CW.BackPixel | xcb.xproto.CW.EventMask,
                          [self.frame.colors[self.frame.active]['bg'],
                           xcb.xproto.EventMask.SubstructureRedirect |
                            xcb.xproto.EventMask.ButtonPress |
                            xcb.xproto.EventMask.ButtonRelease])

        return self

    def __init__(self, _):
        _FrameWindow.__init__(self)

        events.register_drag(self.frame.client.cb_move_start,
                             self.frame.client.cb_move_drag,
                             self.frame.client.cb_move_end,
                             self.id, '1', grab=False)
        events.register_drag(self.frame.client.cb_move_start,
                             self.frame.client.cb_move_drag,
                             self.frame.client.cb_move_end,
                             self.id, 'Mod1-1', grab=False)
        events.register_drag(self.frame.client.cb_resize_start,
                             self.frame.client.cb_resize_drag,
                             self.frame.client.cb_resize_end,
                             self.id, 'Mod1-3', grab=False)

        events.register_buttonpress([self.frame.client.cb_focus,
                                     self.frame.client.cb_stack_raise],
                                    self.id, '1', grab=False)

    def render(self):
        state.conn.core.ChangeWindowAttributes(
            self.id,
            xcb.xproto.CW.BackPixel,
            [self.frame.colors[self.frame.active]['bg']]
        )
        self.clear()

class TopSide(_FrameWindow):
    def __new__(cls, frame):
        self = _FrameWindow.__new__(cls, frame)
        self.id = _create(self.frame.parent.id,
                          xcb.xproto.CW.BackPixmap | xcb.xproto.CW.EventMask |
                          xcb.xproto.CW.Cursor,
                          [xcb.xproto.BackPixmap.ParentRelative,
                           xcb.xproto.EventMask.ButtonPress |
                            xcb.xproto.EventMask.ButtonRelease,
                           state.cursors['TopSide']])

        return self

    def __init__(self, _):
        _FrameWindow.__init__(self)

        self._active_img = None
        self._inactive_img = None

        self.pos = {'x': self.frame.pos['top_side']['x'],
                    'y': self.frame.pos['top_side']['y'],
                    'width': self.frame.pos['top_side']['width'],
                    'height': self.frame.pos['top_side']['height']}

        self.configure(x=self.pos['x'], y=self.pos['y'],
                       height=self.pos['height'])

        events.register_drag(partial(self.frame.client.cb_resize_start,
                                     direction=ewmh.MoveResize.SizeTop),
                             self.frame.client.cb_resize_drag,
                             self.frame.client.cb_resize_end,
                             self.id, '1', grab=False)
        events.register_drag(self.frame.client.cb_move_start,
                             self.frame.client.cb_move_drag,
                             self.frame.client.cb_move_end,
                             self.id, 'Mod1-1', grab=False)
        events.register_drag(self.frame.client.cb_resize_start,
                             self.frame.client.cb_resize_drag,
                             self.frame.client.cb_resize_end,
                             self.id, 'Mod1-3', grab=False)

        self.__setup()

        self.map()

    def __setup(self):
        self._active_img = image.border(
            self.frame.colors[True]['thinborder'],
            self.frame.colors[True]['bg'], 1, self.pos['height'], 'top')

        self._inactive_img = image.border(
            self.frame.colors[False]['thinborder'],
            self.frame.colors[False]['bg'], 1, self.pos['height'], 'top')

    # Let's abstract this, shall we?
    def render(self):
        if self.frame.active:
            data = self._active_img
        else:
            data = self._inactive_img

        rendering.paint_pix(self.id, data, 1, self.pos['height'])

class BottomSide(_FrameWindow):
    def __new__(cls, frame):
        self = _FrameWindow.__new__(cls, frame)
        self.id = _create(self.frame.parent.id,
                          xcb.xproto.CW.BackPixmap | xcb.xproto.CW.EventMask |
                          xcb.xproto.CW.Cursor,
                          [xcb.xproto.BackPixmap.ParentRelative,
                           xcb.xproto.EventMask.ButtonPress |
                            xcb.xproto.EventMask.ButtonRelease,
                           state.cursors['BottomSide']])

        return self

    def __init__(self, _):
        _FrameWindow.__init__(self)

        self._active_img = None
        self._inactive_img = None

        self.pos = {'x': self.frame.pos['bottom_side']['x'],
                    'y': self.frame.pos['bottom_side']['y'],
                    'width': self.frame.pos['bottom_side']['width'],
                    'height': self.frame.pos['bottom_side']['height']}

        self.configure(x=self.pos['x'], height=self.pos['height'])

        events.register_drag(partial(self.frame.client.cb_resize_start,
                                     direction=ewmh.MoveResize.SizeBottom),
                             self.frame.client.cb_resize_drag,
                             self.frame.client.cb_resize_end,
                             self.id, '1', grab=False)
        events.register_drag(self.frame.client.cb_move_start,
                             self.frame.client.cb_move_drag,
                             self.frame.client.cb_move_end,
                             self.id, 'Mod1-1', grab=False)
        events.register_drag(self.frame.client.cb_resize_start,
                             self.frame.client.cb_resize_drag,
                             self.frame.client.cb_resize_end,
                             self.id, 'Mod1-3', grab=False)

        self.__setup()

        self.map()

    def __setup(self):
        self._active_img = image.border(
            self.frame.colors[True]['thinborder'],
            self.frame.colors[True]['bottomborder'], 1, self.pos['height'],
            'bottom')

        self._inactive_img = image.border(
            self.frame.colors[False]['thinborder'],
            self.frame.colors[False]['bottomborder'], 1, self.pos['height'],
            'bottom')

    # Let's abstract this, shall we?
    def render(self):
        if self.frame.active:
            data = self._active_img
        else:
            data = self._inactive_img

        rendering.paint_pix(self.id, data, 1, self.pos['height'])

class Title(_FrameWindow):
    def __new__(cls, frame):
        self = _FrameWindow.__new__(cls, frame)
        self.id = _create(self.frame.parent.id,
                          xcb.xproto.CW.BackPixmap,
                          [xcb.xproto.BackPixmap.ParentRelative])

        return self

    def __init__(self, _):
        _FrameWindow.__init__(self)

        self._active_img = None
        self._inactive_img = None
        self._fwidth = 0
        self._fheight = 0

        self.pos = {'x': self.frame.pos['title']['x'],
                    'y': self.frame.pos['title']['y'],
                    'width': self.frame.pos['title']['width'],
                    'height': self.frame.pos['title']['height']}

        self.gc = state.conn.generate_id()
        state.conn.core.CreateGC(self.gc, state.root, 0, [])

        self.configure(x=self.pos['x'], y=self.pos['y'],
                       height=self.pos['height'])

        self.set_text(self.frame.client.win.wmname)

        self.map()

    def set_text(self, txt):
        self._active_img, width, height = image.draw_text_bgcolor(
            txt, '/usr/share/fonts/TTF/arialbd.ttf', 15,
            self.frame.colors[True]['bg'],
            self.frame.colors[True]['title'],
            self.pos['width'], self.pos['height']
        )
        self._inactive_img, _, _ = image.draw_text_bgcolor(
            txt, '/usr/share/fonts/TTF/arialbd.ttf', 15,
            self.frame.colors[False]['bg'],
            self.frame.colors[False]['title'],
            self.pos['width'], self.pos['height']
        )

        self._fwidth, self._fheight = width, height

        self.configure(width=self._fwidth)

    def render(self):
        if self.frame.active:
            data = self._active_img
        else:
            data = self._inactive_img

        rendering.paint_pix(self.id, data, self._fwidth, self._fheight)

class Icon(_FrameWindow):
    def __new__(cls, frame):
        self = _FrameWindow.__new__(cls, frame)
        self.id = _create(self.frame.parent.id,
                          xcb.xproto.CW.BackPixmap,
                          [xcb.xproto.BackPixmap.ParentRelative])

        return self

    def __init__(self, _):
        _FrameWindow.__init__(self)

        self._active_img = None
        self._inactive_img = None

        self.pos = {'x': self.frame.pos['icon']['x'],
                    'y': self.frame.pos['icon']['y'],
                    'width': self.frame.pos['icon']['width'],
                    'height': self.frame.pos['icon']['height']}

        self.configure(x=self.pos['x'], y=self.pos['y'],
                       width=self.pos['width'], height=self.pos['height'])

        self.__setup()

        self.map()

    def __setup(self):
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
                icon['alpha'] = True
                icon['data'] = image.parse_net_wm_icon(icon['data'])

        # The ICCCM way...
        if icon is None:
            pixid = self.frame.client.win.hints['icon_pixmap']

            w, h, d = image.get_image_from_pixmap(state.conn, pixid)
            icon = {'alpha': False, 'width': w, 'height': h, 'data': d}

        # Default icon...
        if icon is None:
            pass

        # Last resort... a simple solid box
        if icon is None or not icon['width'] or not icon['height']:
            self._active_img = image.box(self.frame.colors[True]['bg'],
                                         self.pos['width'],
                                         self.pos['height'])

            self._inactive_img = image.box(self.frame.colors[False]['bg'],
                                           self.pos['width'],
                                           self.pos['height'])

            return

        # Blending time... yuck
        im = image.get_image(icon['width'], icon['height'], icon['data'])
        im = im.resize((self.pos['width'], self.pos['height']))
        data = image.get_data(im)

        self._active_img = image.blend_bgcolor(data,
                                 self.frame.colors[True]['bg'],
                                 self.pos['width'], self.pos['height'],
                                 icon['alpha'])

        self._inactive_img = image.blend_bgcolor(data,
                                 self.frame.colors[False]['bg'],
                                 self.pos['width'], self.pos['height'],
                                 icon['alpha'])

    def render(self):
        if self.frame.active:
            data = self._active_img
        else:
            data = self._inactive_img

        rendering.paint_pix(self.id, data, self.pos['width'],
                            self.pos['height'])

    def __icon_diff(self, icn_w, icn_h):
        return abs(self.pos['width'] - icn_w) + abs(self.pos['height'] - icn_h)

    def __icon_size(self, icn_w, icn_h):
        return icn_w * icn_h

class _Frame(object):
    def __init__(self, client, parent):
        # Some colors...
        self.colors = {
            True: { # active
                'bg': config.get_option('decor_bg_active'),
                'title': config.get_option('decor_title_active'),
                'thinborder': config.get_option('decor_thinborder_color'),
                'bottomborder': config.get_option('decor_bottom_border_color'),
            },
            False: { # inactive
                'bg': config.get_option('decor_bg_inactive'),
                'title': config.get_option('decor_title_inactive'),
                'thinborder': config.get_option('decor_thinborder_color'),
                'bottomborder': config.get_option('decor_bottom_border_color'),
            }
        }

        # Start activated
        self.active = focus.focused() == client

        self.client = client
        self.parent = parent or Parent(self)

        # State variables
        self._moving = None
        self._resizing = None

        if parent is None:
            state.conn.core.ReparentWindow(self.client.win.id, self.parent.id,
                                           self.pos['client']['x'],
                                           self.pos['client']['y'])
        else:
            parent.frame = self
            self.client.win.configure(x=self.pos['client']['x'],
                                      y=self.pos['client']['y'])

    def render(self):
        pass

    def configure(self, x=None, y=None, width=None, height=None,
                  border_width=None, sibling=None, stack_mode=None):
        self.parent.configure(x, y, width, height, border_width, sibling,
                              stack_mode)

        cw = ch = None
        if width:
            cw = width + self.pos['client']['width']
        if height:
            ch = height + self.pos['client']['height']

        if cw or ch:
            self.client.win.configure(width=cw,
                                      height=ch)

    def resize_start(self, wid, root_x, root_y, event_x, event_y,
                     direction=None):
        # shortcuts
        w = self.parent.geom['width']
        h = self.parent.geom['height']
        mr = ewmh.MoveResize

        if direction is None:
            # Left
            if event_x < w / 3:
                # Top
                if event_y < h / 3:
                    direction = mr.SizeTopLeft
                # Bottom
                elif event_y > h * 2 / 3:
                    direction = mr.SizeBottomLeft
                # Middle
                else: # event_y >= h / 3 and event_y <= h * 2 / 3
                    direction = mr.SizeLeft
            # Right
            elif event_x > w * 2 / 3:
                # Top
                if event_y < h / 3:
                    direction = mr.SizeTopRight
                # Bottom
                elif event_y > h * 2 / 3:
                    direction = mr.SizeBottomRight
                # Middle
                else: # event_y >= h / 3 and event_y <= h * 2 / 3
                    direction = mr.SizeRight
            # Middle
            else: # event_x >= w / 3 and event_x <= w * 2 / 3
                # Top
                if event_y < h / 2:
                    direction = mr.SizeTop
                # Bottom
                else: # event_y >= h / 2
                    direction = mr.SizeBottom

            assert direction is not None

        cursor = {
            mr.SizeTop: state.cursors['TopSide'],
            mr.SizeTopRight: state.cursors['TopRightCorner'],
            mr.SizeRight: state.cursors['RightSide'],
            mr.SizeBottomRight: state.cursors['BottomRightCorner'],
            mr.SizeBottom: state.cursors['BottomSide'],
            mr.SizeBottomLeft: state.cursors['BottomLeftCorner'],
            mr.SizeLeft: state.cursors['LeftSide'],
            mr.SizeTopLeft: state.cursors['TopLeftCorner']
        }.setdefault(direction, state.cursors['LeftPtr'])

        self._resizing = {
            'root_x': root_x,
            'root_y': root_y,
            'direction': direction
        }

        return cursor

    def resize_drag(self, root_x, root_y):
        # shortcut
        d = self._resizing['direction']
        mr = ewmh.MoveResize

        xs = (mr.SizeLeft, mr.SizeTopLeft, mr.SizeBottomLeft)
        ys = (mr.SizeTop, mr.SizeTopLeft, mr.SizeTopRight)

        ws = (mr.SizeTopLeft, mr.SizeTopRight, mr.SizeRight,
              mr.SizeBottomRight, mr.SizeBottomLeft, mr.SizeLeft)
        hs = (mr.SizeTopLeft, mr.SizeTop, mr.SizeTopRight,
              mr.SizeBottomRight, mr.SizeBottom, mr.SizeBottomLeft)

        if d in xs:
            self.parent.geom['x'] += root_x - self._resizing['root_x']

        if d in ys:
            self.parent.geom['y'] += root_y - self._resizing['root_y']

        if d in ws:
            if d in xs:
                self.parent.geom['width'] -= root_x - self._resizing['root_x']
            else:
                self.parent.geom['width'] += root_x - self._resizing['root_x']

        if d in hs:
            if d in ys:
                self.parent.geom['height'] -= (root_y -
                                               self._resizing['root_y'])
            else:
                self.parent.geom['height'] += (root_y -
                                               self._resizing['root_y'])

        self._resizing['root_x'] = root_x
        self._resizing['root_y'] = root_y

        self.configure(x=self.parent.geom['x'], y=self.parent.geom['y'],
                              width=self.parent.geom['width'],
                              height=self.parent.geom['height'])

    def resize_end(self, root_x, root_y):
        self._resizing = None

    def move_start(self, wid, root_x, root_y):
        self._moving = {
            'root_x': root_x,
            'root_y': root_y
        }

        return state.cursors['Fleur']

    def move_drag(self, root_x, root_y):
        self.parent.geom['x'] += root_x - self._moving['root_x']
        self.parent.geom['y'] += root_y - self._moving['root_y']

        self._moving['root_x'] = root_x
        self._moving['root_y'] = root_y

        self.configure(x=self.parent.geom['x'], y=self.parent.geom['y'])

    def move_end(self, root_x, root_y):
        self._moving = None

    def render(self):
        try:
            state.conn.core.GetGeometry(self.client.win.id).reply()
        except:
            return False

        return True

    def activate(self):
        if self.active:
            return False
        self.active = True

        return True

    def deactivate(self):
        if not self.active:
            return False
        self.active = False

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

class Nada(_Frame):
    def __init__(self, client, parent=None):
        # Setup some hints and options before calling the parent constructor

        self.pos = {
            'client': {'x': 0, 'y': 0, 'width': 0, 'height': 0}
        }

        _Frame.__init__(self, client, parent)

        self.configure(
            width=client.win.geom['width'] - self.pos['client']['width'],
            height=client.win.geom['height'] - self.pos['client']['height'])

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

        _Frame.__init__(self, client, parent)

        # Override the border color
        c = config.get_option('decor_thinborder_color')
        self.colors[True]['bg'] = self.colors[False]['bg'] = c

        self.configure(
            width=client.win.geom['width'] - self.pos['client']['width'],
            height=client.win.geom['height'] - self.pos['client']['height'])

    def render(self):
        if not _Frame.render(self):
            return

        # Grabbing makes this process a bit quicker...
        state.grab()
        self.parent.render()
        state.conn.flush()
        state.ungrab()

class Border(_Frame):
    def __init__(self, client, parent=None):
        # Setup some hints and options before calling the parent constructor

        # Some size hints
        self.__bw = config.get_option('decor_border_size')

        self.pos = {
            'client': {'x': self.__bw, 'y': self.__bw,
                       'width': - (self.__bw * 2),
                       'height': - (self.__bw * 2)}
        }

        _Frame.__init__(self, client, parent)

        self.configure(
            width=client.win.geom['width'] - self.pos['client']['width'],
            height=client.win.geom['height'] - self.pos['client']['height'])

    def render(self):
        if not _Frame.render(self):
            return

        # Grabbing makes this process a bit quicker...
        state.grab()
        self.parent.render()
        state.conn.flush()
        state.ungrab()

    def activate(self):
        if not _Frame.activate(self):
            return

        self.render()

    def deactivate(self):
        if not _Frame.deactivate(self):
            return

        self.render()

class Full(_Frame):
    def __init__(self, client, parent=None):
        # Setup some hints and options before calling the parent constructor

        # Some size hints
        self.__bw = config.get_option('decor_border_size')
        self.__bottom_bw = config.get_option('decor_bottom_border_size')
        self.__titleheight = 24

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
                                    self.__titleheight)},
            'icon': {'x': 2, 'y': 2, 'width': 20, 'height': 20},
            'buttons': {'x': -75, 'y': 2, 'width': 75, 'height': 20},
        }
        self.pos['title'] = {
            'x': self.pos['icon']['x'] + self.pos['icon']['width'] + 2,
            'y': 4,
            'width': 800, # Max width
            'height': 20 # Max height
        }
        self.pos['top_side'] = {
            'x': self.pos['title']['x'],
            'y': 0,
            'width': - (self.pos['title']['x'] * 2),
            'height': 5
        }
        self.pos['bottom_side'] = {
            'x': self.pos['title']['x'],
            'y': self.__bw + self.__titleheight,
            'width': - (self.pos['title']['x'] * 2),
            'height': self.__bottom_bw
        }

        _Frame.__init__(self, client, parent)

        self.icon = Icon(self)
        self.top_side = TopSide(self)
        self.bottom_side = BottomSide(self)
        self.title = Title(self)

        # CHANGE THIS
        # This is bad because we're changing the width/height of the client
        # on map without good reason. This needs to be a function of the
        # current layout.
        self.configure(
            width=client.win.geom['width'] - self.pos['client']['width'],
            height=client.win.geom['height'] - self.pos['client']['height'])

    def configure(self, x=None, y=None, width=None, height=None,
                  border_width=None, sibling=None, stack_mode=None):
        _Frame.configure(self, x, y, width, height, border_width, sibling,
                         stack_mode)

        if width:
            self.top_side.configure(
                width=width + self.pos['top_side']['width'])
            self.bottom_side.configure(
                width=width + self.pos['bottom_side']['width'])

        if height:
            self.bottom_side.configure(
                y=self.client.win.geom['height'] +
                  self.pos['bottom_side']['y'])

    def render(self):
        if not _Frame.render(self):
            return

        # Grabbing makes this process a bit quicker...
        state.grab()
        self.top_side.render()
        self.bottom_side.render()
        self.title.render()
        self.icon.render()
        self.parent.render()
        state.conn.flush()
        state.ungrab()

    def activate(self):
        if not _Frame.activate(self):
            return

        self.render()

    def deactivate(self):
        if not _Frame.deactivate(self):
            return

        self.render()

    def switch_off(self):
        self.bottom_side.destroy()
        self.top_side.destroy()
        self.title.destroy()
        self.icon.destroy()
