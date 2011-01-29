import struct

import xcb.xproto

import util
import icccm
import ewmh
import motif
import event
import image

import state
import events
import layers
import focus
import rendering

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
                x = 2 ** 32 + x
            values.append(x)
        if y is not None:
            self.geom['y'] = y

            mask |= conf.Y

            if y < 0:
                y = 2 ** 32 + y
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
        if self._geom is None:
            self._geom = state.conn.core.GetGeometry(self.id)

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

        self._properties = state.conn.core.ListProperties(self.id)
        self._protocols = icccm.get_wm_protocols(state.conn, self.id)
        self._hints = icccm.get_wm_hints(state.conn, self.id)
        self._normal_hints = icccm.get_wm_normal_hints(state.conn, self.id)
        self._class = icccm.get_wm_class(state.conn, self.id)
        self._motif = motif.get_hints(state.conn, self.id)
        self._wmname = ewmh.get_wm_name(state.conn, self.id)
        self._wmclass = icccm.get_wm_class(state.conn, self.id)

    def validate_size(self, width, height):
        nm = self.normal_hints

        if nm['flags']['PResizeInc']:
            if width is not None and nm['width_inc'] > 1:
                base = nm['base_width'] or nm['min_width']
                inc = nm['width_inc'] or 1
                i = round((width - base) / float(inc))
                width = base + int(i) * inc
            if height is not None and nm['height_inc'] > 1:
                base = nm['base_height'] or nm['min_height']
                inc = nm['height_inc'] or 1
                j = round((height - base) / float(inc))
                height = base + int(j) * inc

        if nm['flags']['PMinSize']:
            if width is not None and width < nm['min_width']:
                width = nm['min_width']
            if height is not None and height < nm['min_height']:
                height = nm['min_height']
        else:
            if width is not None and width < 1:
                width = 1
            if height is not None and height < 1:
                height = 1

        if nm['flags']['PMaxSize']:
            if width is not None and width > nm['max_width']:
                width = nm['max_width']
            if height is not None and height > nm['max_height']:
                height = nm['max_height']

        return width, height

    def configure(self, x=None, y=None, width=None, height=None,
                  border_width=None, sibling=None, stack_mode=None,
                  ignore_hints=False):
        nm = self.normal_hints

        if not ignore_hints:
            width, height = self.validate_size(width, height)

        GeometryWindow.configure(self, x, y, width, height, 0,
                                 sibling, stack_mode)

    # Window desires

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

    # Properties

    @property
    def properties(self):
        if isinstance(self._properties, xcb.xproto.ListPropertiesCookie):
            self._properties = list(self._properties.reply().atoms)

        return self._properties

    @property
    def protocols(self):
        if isinstance(self._protocols, util.PropertyCookie):
            self._protocols = self._protocols.reply()

            if self._protocols is None:
                self._protocols = []

        return self._protocols

    @property
    def hints(self):
        if isinstance(self._hints, icccm.HintsCookie):
            self._hints = self._hints.reply()

            if self._hints is None:
                self._hints = {
                    'flags': {'Input': True, 'State': True,
                              'IconPixmap': False, 'IconWindow': False,
                              'IconPosition': False, 'IconMask': False,
                              'WindowGroup': False, 'Message': False,
                              'Urgency': False},
                    'input': 1, 'initial_state': icccm.State.Normal,
                    'icon_pixmap': 0, 'icon_window': 0, 'icon_x': 0,
                    'icon_y': 0, 'icon_mask': 0, 'window_group': 0
                }

        return self._hints

    @property
    def normal_hints(self):
        if isinstance(self._normal_hints, icccm.NormalHintsCookie):
            self._normal_hints = self._normal_hints.reply()

            if self._normal_hints is None:
                self._normal_hints = {
                    'flags': {'USPosition': False, 'USSize': False,
                              'PPosition': False, 'PSize': False,
                              'PMinSize': False, 'PMaxSize': False,
                              'PResizeInc': False, 'PAspect': False,
                              'PBaseSize': False, 'PWinGravity': False},
                    'x': 0, 'y': 0, 'width': 1, 'height': 1,
                    'min_width': 1, 'min_height': 1, 'max_width': 0,
                    'max_height': 0, 'width_inc': 1, 'height_inc': 1,
                    'min_aspect_num': 0, 'min_aspect_den': 0,
                    'max_aspect_num': 0, 'max_aspect_den': 0, 'base_width': 0,
                    'base_height': 0,
                    'win_gravity': xcb.xproto.Gravity.NorthWest}

        return self._normal_hints

    @normal_hints.setter
    def normal_hints(self, value):
        self._normal_hints = value

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

            # If nothing, check WM_NAME...
            if self._wmname is None:
                self._wmname = icccm.get_wm_name(state.conn, self.id).reply()

            # Still nothing... empty string
            if self._wmname is None:
                self._wmname = ''

        return self._wmname

    @wmname.setter
    def wmname(self, value):
        self._wmname = value

    @property
    def wmclass(self):
        if isinstance(self._wmclass, util.PropertyCookie):
            self._wmclass = self._wmclass.reply()

        return self._wmclass

    # This returns the raw image data of an icon
    def get_icon(self, width, height):
        def icon_diff(icn_w, icn_h):
            return abs(width - icn_w) + abs(height - icn_h)

        def icon_size(icn_w, icn_h):
            return icn_w * icn_h

        icons = ewmh.get_wm_icon(state.conn, self.id).reply()

        # Find a valid icon...
        icon = None

        # The EWMH way... find an icon closest to our desired size
        # Bigger is better!
        if icons:
            size = icon_size(width, height)

            for icn in icons:
                if icon is None:
                    icon = icn
                else:
                    old = icon_diff(icon['width'], icon['height'])
                    new = icon_diff(icn['width'], icn['height'])

                    old_size = icon_size(icon['width'], icon['height'])
                    new_size = icon_size(icn['width'], icn['height'])

                    if ((new < old and new_size > old_size) or
                        (size > old_size and size < new_size)):
                        icon = icn

            if icon is not None:
                icon['data'] = image.parse_net_wm_icon(icon['data'])
                icon['mask'] = icon['data']

        # The ICCCM way...
        if (icon is None and
            self.hints['flags']['IconPixmap'] and
            self.hints['icon_pixmap'] is not None and
            self.hints['icon_mask'] is not None):
            pixid = self.hints['icon_pixmap']
            maskid = self.hints['icon_mask']

            w, h, d = image.get_image_from_pixmap(state.conn, pixid)
            icon = {'width': w, 'height': h, 'data': d}

            _, _, icon['mask'] = image.get_image_from_pixmap(state.conn,
                                                             maskid)

        # Default icon...
        # Stealing from Openbox for now... I swear I'll make my own soon :P
        if icon is None:
            icon = {
                'data': image.get_data(rendering.openbox),
                'mask': image.get_data(rendering.openbox),
                'width': rendering.openbox.size[0],
                'height': rendering.openbox.size[1]
            }

        return icon

def cb_ConfigureRequestEvent(e):
    values = []
    conf = xcb.xproto.ConfigWindow
    mask = e.value_mask

    if conf.X & mask:
        if e.x < 0:
            e.x = 2 ** 32 + e.x
        values.append(e.x)
    if conf.Y & mask:
        if e.y < 0:
            e.y = 2 ** 32 + e.y
        values.append(e.y)
    if conf.Width & mask:
        if e.width < 1:
            e.width = 1
        values.append(e.width)
    if conf.Height & mask:
        if e.height < 1:
            e.height = 1
        values.append(e.height)
    if conf.BorderWidth & mask:
        values.append(e.border_width)
    if conf.Sibling & mask:
        values.append(e.sibling)
    if conf.StackMode & mask:
        values.append(e.stack_mode)

    state.conn.core.ConfigureWindow(e.window, mask, values)