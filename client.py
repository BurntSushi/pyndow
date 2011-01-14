from functools import partial
import struct
import sys

import xcb.xproto

import util
import icccm
import ewmh
import event

import state
import window
import events
import focus
import layers
import frame
import misc

# An alias for easy atom grabbing
# Get atom makes use of an atom cache
aname = partial(util.get_atom_name, state.conn)
aid = partial(util.get_atom, state.conn)

def cb_MapRequestEvent(e):
    manage(e.window)

def cb_FocusInEvent(e):
    pass

def cb_FocusOutEvent(e):
    pass

class Client(object):
    def __init__(self, wid):
        self.win = window.Window(wid)

        self._unmapped = True
        self.__net_wm_name = False
        self.catchall = False # Temp
        self.__unmap_ignore = 0

        state.conn.core.ChangeWindowAttributes(
            self.win.id, xcb.xproto.CW.EventMask,
            [xcb.xproto.EventMask.StructureNotify |
             xcb.xproto.EventMask.SubstructureNotify |
             xcb.xproto.EventMask.FocusChange |
             xcb.xproto.EventMask.PropertyChange]
        )
        state.conn.flush()

        x, y = self.win.geom['x'], self.win.geom['y']
        self.frame = self.determine_frame()(self)
        self.frame.configure_client(x=x, y=y)

        events.register_callback(
            xcb.xproto.ConfigureRequestEvent,
            self.cb_ConfigureRequestEvent,
            self.win.id
        )
        events.register_callback(
            xcb.xproto.MapRequestEvent,
            self.cb_MapRequestEvent,
            self.win.id
        )
        events.register_callback(
            xcb.xproto.DestroyNotifyEvent,
            self.cb_DestroyNotifyEvent,
            self.win.id
        )
        events.register_callback(
            xcb.xproto.UnmapNotifyEvent,
            self.cb_UnmapNotifyEvent,
            self.win.id
        )
        events.register_callback(
            xcb.xproto.FocusInEvent,
            self.cb_FocusInEvent,
            self.win.id
        )
        events.register_callback(
            xcb.xproto.FocusOutEvent,
            self.cb_FocusOutEvent,
            self.win.id
        )
        events.register_callback(
            xcb.xproto.PropertyNotifyEvent,
            self.cb_PropertyNotifyEvent,
            self.win.id
        )
        events.register_callback(
            xcb.xproto.ClientMessageEvent,
            self.cb_ClientMessageEvent,
            self.win.id
        )

        #ewmh.set_wm_allowed_actions_checked(state.conn, self.win.id, map(aid, [
            #'_NET_WM_ACTION_MOVE', '_NET_WM_ACTION_RESIZE',
            #'_NET_WM_ACTION_MINIMIZE', '_NET_WM_ACTION_SHADE',
            #'_NET_WM_ACTION_MAXIMIZE_HORZ', '_NET_WM_ACTION_MAXIMIZE_VERT',
            #'_NET_WM_ACTION_FULLSCREEN', '_NET_WM_ACTION_CHANGE_DESKTOP',
            #'_NET_WM_ACTION_CLOSE', '_NET_WM_ACTION_ABOVE',
            #'_NET_WM_ACTION_BELOW'])).check()

        self.win.configure(border_width=0)

        # If the initial state is iconic, don't map...
        if (self.win.hints['flags']['State'] and
            self.win.hints['initial_state'] == icccm.State.Iconic):
            return

        self.map()

    def unlisten(self):
        state.conn.core.ChangeWindowAttributes(self.win.id,
                                               xcb.xproto.CW.EventMask, [])

    def unmanage(self):
        # No more..!
        self.unlisten()
        self.stop_timeout()
        icccm.set_wm_state(state.conn, self.win.id, icccm.State.Withdrawn, 0)
        self.frame.destroy()
        events.unregister_window(self.win.id)
        del state.wins[self.win.id]

    def close(self):
        if self.can_delete():
            event.send_event(state.conn, self.win.id, 0,
                event.pack_client_message(self.win.id, aid('WM_PROTOCOLS'),
                                          aid('WM_DELETE_WINDOW')))
        else:
            state.conn.core.KillClientChecked(self.win.id)

    def stack_raise(self):
        self.layer.above(self)
        self.layer.stack()

    def focus(self):
        if self.focus_notify():
            event.send_event(state.conn, self.win.id, 0,
                event.pack_client_message(self.win.id, aid('WM_PROTOCOLS'),
                                          aid('WM_TAKE_FOCUS'), events.time))

        if self.can_focus():
            state.conn.core.SetInputFocusChecked(
                xcb.xproto.InputFocus.PointerRoot,
                self.win.id, xcb.xproto.Time.CurrentTime).check()

        self.focused()

    def focused(self):
        self.attention_stop()
        focus.above(self)
        self.frame.set_state(frame.State.Active)

    def unfocused(self):
        if (self.catchall and
            frame.State.CatchAll not in self.frame.allowed_states):
            self.catchall = False

        self.frame.set_state(
            frame.State.CatchAll if self.catchall else
            frame.State.Inactive)

    def attention_start(self):
        if self.in_timeout():
            return

        misc.command('toggle_state', self.win.id, 500, 100)

    def attention_stop(self):
        if not self.in_timeout():
            return

        self.stop_timeout()

        if self is focus.focused():
            self.focused()
        else:
            self.unfocused()

    def decorate(self, border=False, slim=False):
        if border:
            frame.switch(self.frame, frame.Border)
        elif slim:
            frame.switch(self.frame, frame.SlimBorder)
        else:
            frame.switch(self.frame, frame.Full)

    def undecorate(self):
        frame.switch(self.frame, frame.Nada)

    def map(self):
        if not self._unmapped:
            return

        icccm.set_wm_state(state.conn, self.win.id, icccm.State.Normal, 0)
        layers.default.add(self)
        self.layer.stack()

        # START GRAB
        state.grab()
        self.win.map()
        self.frame.map()

        focus.add(self)
        self.focus()
        state.ungrab()
        # END GRAB

        self._unmapped = False

    def unmap(self):
        # I could de-select UnmapNotify events from being sent before unmap,
        # but there are occasions (like reparenting a mapped window) when
        # this might not be feasible.
        #state.grab()
        self.__unmap_ignore += 1
        self.win.unmap()
        self.unmapped()

    def unmapped(self):
        icccm.set_wm_state(state.conn, self.win.id, icccm.State.Iconic, 0)
        fallback = focus.focused() is self
        self.frame.unmap()
        self.layer.remove(self)
        focus.remove(self)
        if fallback:
            focus.fallback()

        self._unmapped = True

        state.conn.flush()

    def stop_timeout(self):
        state.conn.core.ChangeProperty(xcb.xproto.PropMode.Replace,
                                       self.win.id, aid('_PYNDOW_CMD_TIMEOUT'),
                                       xcb.xproto.Atom.CARDINAL, 32, 1, [0])
        state.conn.flush()

    # Toggling

    def toggle_decorations(self):
        if (isinstance(self.frame, frame.Border) or
            isinstance(self.frame, frame.Full) or
            isinstance(self.frame, frame.SlimBorder)):
            self.undecorate()
        else:
            self.decorate()

    def toggle_state(self):
        if self.frame.state == frame.State.Active:
            if (self.catchall and
                frame.State.CatchAll not in self.frame.allowed_states):
                self.catchall = False

            self.frame.set_state(
                frame.State.CatchAll if self.catchall else
                frame.State.Inactive)
        else:
            self.frame.set_state(frame.State.Active)

    def toggle_catchall(self):
        if frame.State.CatchAll not in self.frame.allowed_states:
            return

        self.catchall = not self.catchall
        if self is not focus.focused():
            self.frame.set_state(
                frame.State.CatchAll if self.catchall else
                frame.State.Inactive)

    # Determinations

    def determine_frame(self):
        # Layout ought to take precedence... layout will be responsible
        # for handling odd cases like windows that should float or transients

        test = self.win.desires_decor()
        if not test:
            if test is None:
                return frame.Nada
            return frame.SlimBorder

        return frame.Full

    # Booleans

    def can_focus(self):
        return self.win.hints['input'] == 1

    def focus_notify(self):
        return aid('WM_TAKE_FOCUS') in self.win.protocols

    def can_delete(self):
        return aid('WM_DELETE_WINDOW') in self.win.protocols

    def is_alive(self):
        state.sync()

        event.read(state.conn)
        ignore = self.__unmap_ignore

        for e in event.peek():
            if (isinstance(e, xcb.xproto.UnmapNotifyEvent) and
                e.window == self.win.id):
                if not ignore:
                    return False

                ignore = max(ignore - 1, 0)

        return True

    def in_timeout(self):
        cookie = util.get_property(state.conn, self.win.id,
                                   aid('_PYNDOW_CMD_TIMEOUT'))
        check = util.PropertyCookieSingle(cookie).reply()

        if check is None:
            return False

        check = int(check)

        return check == 1

    # Updates

    def update_title(self, atom):
        assert atom in ('_NET_WM_NAME', 'WM_NAME')

        # If the window has a _NET_WM_NAME property, ignore WM_NAME
        if atom == 'WM_NAME' and aid('_NET_WM_NAME') in self.win.properties:
            return

        new_name = ''
        if atom == '_NET_WM_NAME':
            new_name = ewmh.get_wm_name(state.conn, self.win.id).reply()
        elif atom == 'WM_NAME':
            new_name = icccm.get_wm_name(state.conn, self.win.id).reply()

        # Don't update if it's the same...
        if new_name == self.win.wmname:
            return

        self.win.wmname = new_name
        if isinstance(self.frame, frame.Full):
            self.frame.title.set_text(self.win.wmname)
            self.frame.title.render()

    # Event callbacks

    def cb_stack_raise(self, e):
        self.stack_raise()
        state.replay_pointer()

    def cb_focus(self, e):
        self.focus()
        state.replay_pointer()

    def cb_resize_start(self, e, direction=None):
        return self.frame.resize_start(e.event, e.root_x, e.root_y, e.event_x,
                                       e.event_y, direction)

    def cb_resize_drag(self, e):
        return self.frame.resize_drag(e.root_x, e.root_y, e.event_x, e.event_y)

    def cb_resize_end(self, e):
        return self.frame.resize_end(e.root_x, e.root_y)

    def cb_move_start(self, e):
        return self.frame.move_start(e.event, e.root_x, e.root_y)

    def cb_move_drag(self, e):
        return self.frame.move_drag(e.root_x, e.root_y)

    def cb_move_end(self, e):
        return self.frame.move_end(e.root_x, e.root_y)

    def cb_ConfigureRequestEvent(self, e):
        x = y = width = height = border_width = sibling = stack_mode = None
        conf = xcb.xproto.ConfigWindow
        mask = e.value_mask

        if conf.X & mask:
            x = e.x
        if conf.Y & mask:
            y = e.y
        if conf.Width & mask:
            width = e.width
        if conf.Height & mask:
            height = e.height
        if conf.BorderWidth & mask:
            border_width = e.border_width
        if conf.Sibling & mask:
            sibling = e.sibling
        if conf.StackMode & mask:
            stack_mode = e.stack_mode

        self.frame.configure_client(x, y, width, height, border_width, sibling,
                                    stack_mode)

    def cb_MapRequestEvent(self, e):
        self.map()

    def cb_DestroyNotifyEvent(self, e):
        self.unmanage()

    def cb_UnmapNotifyEvent(self, e):
        if self._unmapped:
            return

        if self.__unmap_ignore > 0:
            self.__unmap_ignore -= 1
            return

        self.unmapped()
        self.unmanage()

    def cb_FocusInEvent(self, e):
        if not self.is_alive():
            return

        if e.mode != xcb.xproto.NotifyMode.Normal:
            return

        if e.detail not in (xcb.xproto.NotifyDetail.Inferior,
                            xcb.xproto.NotifyDetail.Virtual,
                            xcb.xproto.NotifyDetail.Nonlinear,
                            xcb.xproto.NotifyDetail.NonlinearVirtual):
            return

        self.focused()

    def cb_FocusOutEvent(self, e):
        if not self.is_alive():
            return

        #if e.mode != xcb.xproto.NotifyMode.Normal:
            #return

        #if e.detail not in (xcb.xproto.NotifyDetail.Virtual,
                            #xcb.xproto.NotifyDetail.Nonlinear,
                            #xcb.xproto.NotifyDetail.NonlinearVirtual):
            #return

        if focus.focused() != self:
            self.unfocused()

    def cb_PropertyNotifyEvent(self, e):
        if not self.is_alive():
            return

        if (e.state == xcb.xproto.Property.NewValue and
            e.atom not in self.win.properties):
            self.win.properties.append(e.atom)

        a = aname(e.atom)

        if a in ('_NET_WM_NAME', 'WM_NAME'):
            self.update_title(a)
        elif a == 'WM_NORMAL_HINTS':
            self.win.normal_hints = icccm.get_wm_normal_hints(state.conn,
                                                              self.win.id)

        if (e.state == xcb.xproto.Property.Delete and
            e.atom in self.win.properties):
            self.win.properties.remove(e.atom)

    def cb_ClientMessageEvent(self, e):
        if aname(e.type) == '_PYNDOW_CMD':
            atom_name = aname(e.data.data32[0])
            cmd = 'cmd_%s' % atom_name.replace('_PYNDOW_CMD_', '').lower()

            if hasattr(self, cmd):
                getattr(self, cmd)()

    # Commands

    def cmd_toggle_state(self):
        self.toggle_state()

    def cmd_close(self):
        self.close()

    # Nice debug functions
    def __str__(self):
        return ewmh.get_wm_name(state.conn, self.win.id).reply()

def get(wid):
    return state.wins.setdefault(wid, None)

def manage(wid):
    state.wins[wid] = Client(wid)

    return state.wins[wid]

#def manage_existing(wid):
    #try:
        #attrs = state.conn.core.GetWindowAttributes(wid).reply()
    #except xcb.xproto.BadWindow:
        #return False

    #state.debug('Got window attrs: %d' % wid)

    #if attrs.map_state is not xcb.xproto.MapState.Viewable:
        #return False

    #try:
        #hints = icccm.get_wm_hints(state.conn, wid).reply()
    #except xcb.xproto.BadWindow:
        #return False

    #state.debug('Got window hints: %d' % wid)

    #if hints['initial_state'] not in (icccm.State.Normal, icccm.State.Iconic):
        #return False

    #manage(wid)