'''
Here's how the cycle window currently works.

Firstly, the parent and inner windows are created when Pyndow starts up. Of
course, they are not mapped yet.

Each icon is itself its own window. All icon windows are created and mapped
when the cycle dialog is display. All icon windows are also *destroyed* when
the cycle dialog goes away.

The only state that is changed while the cylce dialog is visible is that of
cycling through the windows to determine which to focus (i.e., the "active"
icon). Once the dialog is closed, that window is activated.

This means that if state changes somehow occur while the cycle dialog is
visible, they will *not* be reflected. (i.e., if a window is closed, its icon
will still appear on the cycle dialog.) Once the cycle dialog is hidden and
made visible again, the proper state will be accounted for.

I'll probably keep it this way for now, and make sure that when the cycle
dialog is hidden, that the window it wants to give focus to still exists.

'''

import xcb.xproto

import xpybutil.image as image
import xpybutil.event as event

import state
import events
import focus
import window
import config
import rendering
import grab
from popup import _PopupWindow

c_brdr_sz = config.get_option('cycle_brdr_sz')
c_brdr_clr = config.get_option('cycle_brdr_clr')
c_bg = config.get_option('cycle_bg')
c_icn_sz = config.get_option('cycle_icn_sz')

class IconWindow(_PopupWindow):
    def __new__(cls, parent, client):
        self = _PopupWindow.__new__(cls)

        mask = xcb.xproto.CW.BackPixel
        values = [c_bg]
        self.id = window.create(parent.inner.id, mask, values)

        self.parent = parent
        self.client = client

        return self

    def __init__(self, *_):
        _PopupWindow.__init__(self)

        self.width = self.height = c_icn_sz + (2 * c_brdr_sz)

        self.configure(width=self.width, height=self.height)

        icon = self.client.win.get_icon(c_icn_sz, c_icn_sz)

        im = image.get_image(icon['width'], icon['height'], icon['data'])
        im = im.resize((c_icn_sz, c_icn_sz))

        if 'mask' in icon and icon['mask'] and icon['mask'] != icon['data']:
            immask = image.get_bitmap(icon['width'], icon['height'],
                                      icon['mask'])
            immask = immask.resize((c_icn_sz, c_icn_sz))
        else:
            immask = im.copy()

        alpha = 1
        if not self.client.mapped:
            alpha = 0.3
        icon_im = rendering.blend(im, immask, c_bg, c_icn_sz, c_icn_sz, alpha)

        im_inactive = rendering.box(c_bg, self.width, self.height)
        im_inactive.paste(icon_im, box=(c_brdr_sz, c_brdr_sz))

        im_active = rendering.box(c_brdr_clr, self.width, self.height)
        im_active.paste(icon_im, box=(c_brdr_sz, c_brdr_sz))

        self.inactive = image.get_data(im_inactive)
        self.active = image.get_data(im_active)

        self.render_inactive()

        self.map()

    def render_inactive(self):
        rendering.paint_pix(self.id, self.inactive, self.width, self.height)

    def render_active(self):
        rendering.paint_pix(self.id, self.active, self.width, self.height)

class CycleWindow(_PopupWindow):
    def __new__(cls):
        self = _PopupWindow.__new__(cls)

        mask = xcb.xproto.CW.BackPixel | xcb.xproto.CW.EventMask
        values = [c_brdr_clr]
        values.append(xcb.xproto.EventMask.SubstructureRedirect |
                      xcb.xproto.EventMask.ButtonPress |
                      xcb.xproto.EventMask.ButtonRelease)

        self.id = window.create(state.root, mask, values)

        return self

    def __init__(self):
        _PopupWindow.__init__(self)

        # Create the inner window
        inner_id = window.create(self.id, xcb.xproto.CW.BackPixel, [c_bg])
        self.inner = window.GeometryWindow(inner_id)

        self.icons = []
        self.wins = []

        self.current = 0
        self.showing = False

    def set_window_list(self):
        self.wins = focus.get_stack()
        self.wins.reverse()

    def determine_geometry(self):
        sw = state.rsetup.width_in_pixels
        sh = state.rsetup.height_in_pixels

        # c_brdr_sz is used for the border around the window and
        # around each of the icons... meh
        w = (len(self.wins) * (c_icn_sz + (2 * c_brdr_sz))) + 20 + (2 * c_brdr_sz)
        h = c_icn_sz + (2 * c_brdr_sz) + 20 + (2 * c_brdr_sz)

        x = (sw / 2) - (w / 2)
        y = (sh / 2) - (h / 2)

        return {'x': x, 'y': y, 'width': w, 'height': h}

    def show(self):
        self.set_window_list()

        if not self.wins:
            return False

        self.current = self.current % len(self.wins)

        # Force the stack mode to be above.
        # The layers module stacks from the bottom up, so this is okay.
        cargs = {'stack_mode': xcb.xproto.StackMode.Above}
        self.configure(**dict(cargs, **self.determine_geometry()))

        self.inner.configure(x=c_brdr_sz, y=c_brdr_sz,
                             width=self.geom['width'] - 2 * c_brdr_sz,
                             height=self.geom['height'] - 2 * c_brdr_sz)

        self.icons = []
        for i, client in enumerate(self.wins):
            icon = IconWindow(self, client)
            self.icons.append(icon)

            icon.configure(x=10 + i * (c_icn_sz + (2 * c_brdr_sz)), y=10)

            if i == self.current:
                icon.render_active()

        self.inner.map()
        self.map()

        self.showing = True

        return True

    def hide(self):
        self.unmap()
        for icon in self.icons:
            icon.destroy()

        client = self.wins[self.current]

        if client.is_alive():
            if client.mapped:
                client.focus()
                client.stack_raise()
            else:
                client.map()

        self.current = 0
        self.showing = False
        self.wins = []
        del self.icons

    def highlight_next(self):
        self.icons[self.current].render_inactive()
        self.current = (self.current + 1) % len(self.icons)
        self.icons[self.current].render_active()

    def highlight_previous(self):
        self.icons[self.current].render_inactive()
        self.current = (self.current - 1) % len(self.icons)
        self.icons[self.current].render_active()

# Initialize the popup window... Doesn't map it yet, though
cycle = CycleWindow()

# Event callback processing. Fairly straight-forward.

def __start():
    if not cycle.show():
        return { 'grab': False }
    else:
        return { 'grab': True }

def start_next(e):
    if cycle.showing:
        return

    cycle.current = 1
    return __start()

def start_prev(e):
    if cycle.showing:
        return

    cycle.current = -1
    return __start()

def do_next(e):
    cycle.highlight_next()

def do_prev(e):
    cycle.highlight_previous()

def end(e):
    if not cycle.showing:
        return

    cycle.hide()

