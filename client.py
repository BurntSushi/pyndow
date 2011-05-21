from functools import partial
import struct
import sys

import xcb.xproto

import xpybutil.util as util
import xpybutil.icccm as icccm
import xpybutil.ewmh as ewmh
import xpybutil.event as event

import state
import window
import events
import focus
import layers
import frame
import misc
import workspace

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
    """
    This is an abstract class that represents *all* managed windows; otherwise
    known as "clients" in the X world.

    This class ought to be subclassed with the different kinds of windows.
    They may roughly correspond to the types legal in the '_NET_WM_WINDOW_TYPE'
    atom---although it is likely that one class may represent more than one
    type if Pyndow wants to treat them similarly. Chief among different kinds
    of clients would be your typical or "normal" clients, desktops and docks.
    """
    def __init__(self, wid):
        self.win = window.Window(wid)

        self.workspaces = []
        self.mapped = False
        self.__unmap_ignore = 0

        state.conn.core.ChangeWindowAttributes(
            self.win.id, xcb.xproto.CW.EventMask,
            [xcb.xproto.EventMask.StructureNotify |
             xcb.xproto.EventMask.PropertyChange]
        )

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
            xcb.xproto.PropertyNotifyEvent,
            self.cb_PropertyNotifyEvent,
            self.win.id
        )
        events.register_callback(
            xcb.xproto.ClientMessageEvent,
            self.cb_ClientMessageEvent,
            self.win.id
        )

        self.win.configure(border_width=0)

    # Sub class responsibilities
    def map(self):
        assert False, 'subclass responsibility'

    def unmapped(self, light=False):
        assert False, 'subclass responsibility'

    # Sub class optional responsibilities
    def focus(self):
        pass

    def focused(self):
        pass

    def unfocused(self):
        pass

    def parent_id(self):
        return self.win.id

    def unlisten(self):
        state.conn.core.ChangeWindowAttributes(self.win.id,
                                               xcb.xproto.CW.EventMask, [])

    def unmanage(self):
        # No more..!
        focus.remove(self) # It might not be here, but do it anyway
        self.layer.remove(self)
        self.unlisten()
        self.stop_timeout()
        icccm.set_wm_state(state.conn, self.win.id, icccm.State.Withdrawn, 0)
        events.unregister_window(self.win.id)
        del state.windows[self.win.id]

    def configure(self, **kwargs):
        self.win.configure(**kwargs)

    def close(self):
        if aid('WM_DELETE_WINDOW') in self.win.protocols:
            event.send_event(state.conn, self.win.id, 0,
                event.pack_client_message(self.win.id, aid('WM_PROTOCOLS'),
                                          aid('WM_DELETE_WINDOW')))
        else:
            state.conn.core.KillClientChecked(self.win.id)

    def stack_raise(self):
        self.layer.above(self)
        self.layer.stack()

    def stack_lower(self):
        self.layer.below(self)
        self.layer.stack()

    def is_focusable(self):
        """
        If a client is focusable, it will show up in alt-tab and be added to
        the focus stack.
        By default, a client is not focusable. (i.e., desktops and docks.)
        """
        return False

    def unmap(self, light=False):
        """
        Hides a window. If a client initiates an unmap request, then we no
        longer manage the client---but within Pyndow, an unmap request is
        equivalent to hiding/iconifying/minimizing the window.
        """
        # I could de-select UnmapNotify events from being sent before unmap,
        # but there are occasions (like reparenting a mapped window) when
        # this might not be feasible.
        #state.grab()
        self.__unmap_ignore += 1
        self.win.unmap()
        self.unmapped(light=light)

    def stop_timeout(self):
        state.conn.core.ChangeProperty(xcb.xproto.PropMode.Replace,
                                       self.win.id, aid('_PYNDOW_CMD_TIMEOUT'),
                                       xcb.xproto.Atom.CARDINAL, 32, 1, [0])
        state.conn.flush()

    def is_in_timeout(self):
        cookie = util.get_property(state.conn, self.win.id,
                                   aid('_PYNDOW_CMD_TIMEOUT'))
        check = util.PropertyCookieSingle(cookie).reply()

        if check is None:
            return False

        check = int(check)

        return check == 1

    def is_alive(self):
        """
        A useful auxiliary method to determine if a client is alive and can
        still be used. This is achieved at peeking to see if an unmap event
        has been queued up.
        """
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

    def update_title(self, atom):
        """
        Updates the 'wmname' attribute of a window object. Prefers EWMH and
        falls back to ICCCM if necessary. If no name can be found, use an empty
        string.
        """
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

    # Event callbacks

    def cb_stack_raise(self, e):
        """
        Raises a window to the top of its current layer *and* replays the
        pointer click. Therefore, this callback is intended to be used in
        response to a button event.
        The "replay pointer" is used so that the button click isn't lost.
        """
        self.stack_raise()
        state.replay_pointer()

    def cb_focus(self, e):
        """
        Brings a window to the top of the focus stack and gives it focus, and
        replays the pointer click. Therefore, this callback is intended to be 
        used in response to a button event.
        The "replay pointer" is used so that the button click isn't lost.
        """
        self.focus()
        state.replay_pointer()

    def cb_ConfigureRequestEvent(self, e):
        """
        This callback occurs when a managed client wants to configure itself.
        As of right now, simply pass it along. (But it does get validated if
        it's in a frame.)
        """
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

        self.configure(x=x, y=y, width=width, height=height, 
                       border_width=border_width, sibling=sibling, 
                       stack_mode=stack_mode)

    def cb_MapRequestEvent(self, e):
        """
        This occurs when a managed client specifically requests to map itself.
        As of right now, simply grant its request.
        """
        self.map()

    def cb_DestroyNotifyEvent(self, e):
        """
        Although we typically won't get to this point (since we unmanage a
        client at Unmap), if we do, simple unmanage it.
        """
        self.unmanage()

    def cb_UnmapNotifyEvent(self, e):
        """
        If we get an unmap event and there are no unmap events to ignore,
        stop managing the client immediately.
        """
        if not self.mapped:
            return

        if self.__unmap_ignore > 0:
            self.__unmap_ignore -= 1
            return

        self.unmapped()
        self.unmanage()

    def cb_PropertyNotifyEvent(self, e):
        """
        Respond to any added, changed or deleted properties on the client.
        """
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
        """
        Respond to any client messages sent to the client.
        """
        if aname(e.type) == '_PYNDOW_CMD':
            atom_name = aname(e.data.data32[0])
            cmd = 'cmd_%s' % atom_name.replace('_PYNDOW_CMD_', '').lower()

            if hasattr(self, cmd):
                getattr(self, cmd)()

    # Commands

    def cmd_close(self):
        self.close()

    # Nice debug function
    def __str__(self):
        return self.win.wmname

class DockClient(Client):
    def __init__(self, wid):
        Client.__init__(self, wid)

        events.register_buttonpress(self.cb_stack_raise, self.win.id, '1',
                                    propagate=True)

    def map(self):
        """
        Mapping a docked client is similar to mapping a normal client, except
        it is not included in the focus stack. Also, it is added to the "dock"
        layer, where it will typically reside above most other clients.
        """
        if self.mapped:
            return

        icccm.set_wm_state(state.conn, self.win.id, icccm.State.Normal, 0)

        layers.dock.add(self)
        self.stack_raise()

        # START GRAB
        state.grab()
        self.win.map()
        state.ungrab()
        # END GRAB

        self.mapped = True

    def maplight(self):
        """
        Mapping a docked client is similar to mapping a normal client, except
        it is not included in the focus stack. Also, it is added to the "dock"
        layer, where it will typically reside above most other clients.
        """
        if self.mapped:
            return

        icccm.set_wm_state(state.conn, self.win.id, icccm.State.Normal, 0)

        # START GRAB
        state.grab()
        self.win.map()
        state.ungrab()
        # END GRAB

        self.mapped = True

    def unmapped(self, light=False):
        icccm.set_wm_state(state.conn, self.win.id, icccm.State.Iconic, 0)

        self.mapped = False

        state.conn.flush()

class NormalClient(Client):
    def __init__(self, wid):
        Client.__init__(self, wid)

        self.catchall = False # Temp
        self.maximized = False # Temp
        self.iconified = False

        x, y = self.win.geom['x'], self.win.geom['y']
        self.frame = self.get_frame()(self)
        self.frame.configure_client(x=x, y=y)

        # Only one of these lines should exist.
        # Leaning toward the second.
        self.workspaces = [workspace.current()]
        workspace.current().add(self)

        ewmh.set_supported(state.conn, self.win.id, [aid('_NET_WM_MOVERESIZE')])

    def map(self):
        if self.mapped:
            return

        icccm.set_wm_state(state.conn, self.win.id, icccm.State.Normal, 0)

        if self.is_focusable():
            focus.add(self)

        layers.default.add(self)
        self.stack_raise()

        self.iconified = False

        self.workspaces[0].mapped(self)

        # START GRAB
        state.grab()
        self.win.map()
        self.frame.map()
        self.focus()
        state.ungrab()
        # END GRAB

        self.mapped = True

    def maplight(self):
        if self.mapped:
            return

        icccm.set_wm_state(state.conn, self.win.id, icccm.State.Normal, 0)

        # START GRAB
        state.grab()
        self.win.map()
        self.frame.map()
        state.ungrab()
        # END GRAB

        self.mapped = True

    def unmapped(self, light=False):
        icccm.set_wm_state(state.conn, self.win.id, icccm.State.Iconic, 0)
        fallback = focus.focused() is self
        self.frame.unmap()

        self.mapped = False

        if not light and fallback:
            focus.fallback()

        state.conn.flush()

    def focus(self):
        if self.win.hints['input'] == 1:
            state.conn.core.SetInputFocusChecked(
                xcb.xproto.InputFocus.PointerRoot,
                self.win.id, xcb.xproto.Time.CurrentTime).check()

            self.focused()
        elif aid('WM_TAKE_FOCUS') in self.win.protocols:
            packed = event.pack_client_message(self.win.id,
                                               aid('WM_PROTOCOLS'),
                                               aid('WM_TAKE_FOCUS'),
                                               events.time)
            event.send_event(state.conn, self.win.id, 0, packed)

            self.focused()

    def focused(self):
        # If this client's workspace is not the current workspace,
        # then change to this client's workspace.
        if self.workspaces and workspace.current() != self.workspaces[0]:
            workspace.view(self.workspaces[0], focusing=False)
            self.stack_raise()

        focus.above(self)
        self.attention_stop()
        self.frame.set_state(frame.State.Active)

        for client in focus.get_stack()[:-1]:
            client.unfocused()

    def unfocused(self):
        Client.unfocused(self)

        if (self.catchall and
            frame.State.CatchAll not in self.frame.allowed_states):
            self.catchall = False

        self.frame.set_state(
            frame.State.CatchAll if self.catchall else
            frame.State.Inactive)

    def parent_id(self):
        return self.frame.parent.id

    def unmanage(self):
        if self.mapped:
            self.unmapped()

        self.frame.destroy()

        Client.unmanage(self)

    def configure(self, **kwargs):
        self.frame.configure_client(**kwargs)

    def is_focusable(self):
        return (aid('WM_TAKE_FOCUS') in self.win.protocols
                or self.win.hints['input'] == 1)

    # Start NormalClient specific methods

    def decorate(self, border=False, slim=False):
        if border:
            frame.switch(self.frame, frame.Border)
        elif slim:
            frame.switch(self.frame, frame.SlimBorder)
        else:
            frame.switch(self.frame, frame.Full)

    def undecorate(self):
        frame.switch(self.frame, frame.Nada)

    def minimize(self):
        self.unmap()

    def attention_start(self):
        if self.is_in_timeout():
            return

        misc.command('toggle_framestate', self.win.id, 500, 100)

    def attention_stop(self):
        if not self.is_in_timeout():
            return

        self.stop_timeout()

        if self is focus.focused():
            self.focused()
        else:
            self.unfocused()

    def toggle_decorations(self):
        if (isinstance(self.frame, frame.Border) or
            isinstance(self.frame, frame.Full) or
            isinstance(self.frame, frame.SlimBorder)):
            self.undecorate()
        else:
            self.decorate()

    def toggle_framestate(self):
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

    def get_frame(self):
        # Layout ought to take precedence... layout will be responsible
        # for handling odd cases like windows that should float or transients

        test = self.win.desires_decor()
        if not test:
            if test is None:
                return frame.Nada
            return frame.SlimBorder

        return frame.Full

    # I think a lot of these callbacks are a bit awkward here.
    # I don't think they'll stay.
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

    # Normal client specific commands

    def cmd_toggle_framestate(self):
        self.toggle_framestate()

def get(wid):
    return state.windows.setdefault(wid, None)

def manage(wid):
    windowtypes = ewmh.get_wm_window_type(state.conn, wid).reply()
    if windowtypes:
        primary = aname(windowtypes[0])
        if primary == '_NET_WM_WINDOW_TYPE_DOCK':
            client = DockClient(wid)
        else:
            client = NormalClient(wid)
    else:
        client = NormalClient(wid)

    # If the initial state is iconic, don't map...
    if (not client.win.hints['flags']['State'] or
        client.win.hints['initial_state'] != icccm.State.Iconic):
        client.map()

    state.windows[wid] = client
    return state.windows[wid]

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
