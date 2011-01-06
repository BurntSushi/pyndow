import xcb.xproto

import ewmh

import state
import events
import window
import focus

def switch(old_frame, new_frame_cb):
    client = old_frame.client
    parent = old_frame.parent

    old_frame.switch_off()
    client.frame = new_frame_cb(client, parent)
    client.frame.switch_on()

class State:
    Active = 1
    Inactive = 2
    CatchAll = 3

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

        self.nada = False

        mask = xcb.xproto.CW.EventMask
        bg = self.frame.colors[self.frame.state]['bg']
        if bg == -1:
            self.nada = True
            mask |= xcb.xproto.CW.BackPixmap
            values = [xcb.xproto.BackPixmap.ParentRelative]
        else:
            mask |= xcb.xproto.CW.BackPixel
            values = [bg]
        values.append(xcb.xproto.EventMask.SubstructureRedirect |
                      xcb.xproto.EventMask.ButtonPress |
                      xcb.xproto.EventMask.ButtonRelease)

        self.id = window.create(state.root, mask, values)

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
        if not self.nada:
            state.conn.core.ChangeWindowAttributes(
                self.id,
                xcb.xproto.CW.BackPixel,
                [self.frame.colors[self.frame.state]['bg']]
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