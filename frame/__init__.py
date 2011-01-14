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

        events.register_drag(self.frame.client.cb_move_start,
                             self.frame.client.cb_move_drag,
                             self.frame.client.cb_move_end,
                             self.id, 'Mod4-1')
        events.register_drag(self.frame.client.cb_resize_start,
                             self.frame.client.cb_resize_drag,
                             self.frame.client.cb_resize_end,
                             self.id, 'Mod4-3')

        events.register_buttonpress([self.frame.client.cb_focus,
                                     self.frame.client.cb_stack_raise],
                                    self.id, '1', propagate=True)

    def render(self):
        if not self.nada:
            state.conn.core.ChangeWindowAttributes(
                self.id,
                xcb.xproto.CW.BackPixel,
                [0]
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
                  border_width=None, sibling=None, stack_mode=None):
        cw = ch = w = h = None

        # If resizing, update the client's size too. Make sure to use the
        # proper sizes based on the current frame, and validate!
        # Validation is used here so we know when to stop resizing the frame.
        if width or height:
            if width: cw = width + self.pos['client']['width']
            if height: ch = height + self.pos['client']['height']

            w, h = self.client.win.validate_size(cw, ch)

            if w != cw:
                width = (w - self.pos['client']['width'])
            if h != ch:
                height = (h - self.pos['client']['height'])

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

        self.resizing = {
            'root_x': root_x,
            'root_y': root_y,
            'x': self.parent.geom['x'],
            'y': self.parent.geom['y'],
            'w': self.parent.geom['width'],
            'h': self.parent.geom['height'],
            'direction': direction
        }

        return cursor

    def resize_drag(self, root_x, root_y, event_x, event_y):
        # shortcut
        d = self.resizing['direction']
        mr = ewmh.MoveResize

        xs = (mr.SizeLeft, mr.SizeTopLeft, mr.SizeBottomLeft)
        ys = (mr.SizeTop, mr.SizeTopLeft, mr.SizeTopRight)

        ws = (mr.SizeTopLeft, mr.SizeTopRight, mr.SizeRight,
              mr.SizeBottomRight, mr.SizeBottomLeft, mr.SizeLeft)
        hs = (mr.SizeTopLeft, mr.SizeTop, mr.SizeTopRight,
              mr.SizeBottomRight, mr.SizeBottom, mr.SizeBottomLeft)

        diffx = root_x - self.resizing['root_x']
        diffy = root_y - self.resizing['root_y']

        old_x = self.parent.geom['x']
        old_y = self.parent.geom['y']

        new_x = new_y = new_width = new_height = None

        if d in xs:
            new_x = self.resizing['x'] + diffx

        if d in ys:
            new_y = self.resizing['y'] + diffy

        if d in ws:
            if d in xs:
                new_width = self.resizing['w'] - diffx
            else:
                new_width = self.resizing['w'] + diffx

        if d in hs:
            if d in ys:
                new_height = self.resizing['h'] - diffy
            else:
                new_height = self.resizing['h'] + diffy

        w, h = self.validate_size(new_width, new_height)

        # If the width and height didn't change, don't adjust x,y...
        if new_x is not None and w != new_width:
            new_x = self.resizing['x'] + (self.resizing['w'] - w)
        if new_y is not None and h != new_height:
            new_y = self.resizing['y'] + (self.resizing['h'] - h)

        self.configure(x=new_x, y=new_y, width=w, height=h)

    def resize_end(self, root_x, root_y):
        self.resizing = None
        self.configure()

    def move_start(self, wid, root_x, root_y):
        self.moving = {
            'root_x': root_x,
            'root_y': root_y
        }

        return state.cursors['Fleur']

    def move_drag(self, root_x, root_y):
        self.parent.geom['x'] += root_x - self.moving['root_x']
        self.parent.geom['y'] += root_y - self.moving['root_y']

        self.moving['root_x'] = root_x
        self.moving['root_y'] = root_y

        self.configure(x=self.parent.geom['x'], y=self.parent.geom['y'])

    def move_end(self, root_x, root_y):
        self.moving = None

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