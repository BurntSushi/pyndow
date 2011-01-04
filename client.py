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

def cb_MapRequestEvent(e):
    manage(e.window)

class Client(object):
    def __init__(self, wid):
        self.win = window.Window(wid)

        self._unmapped = True

        self.frame = self.determine_frame()(self)
        #self.frame = frame.Nada(self)

        state.conn.core.ChangeWindowAttributes(
            self.win.id, xcb.xproto.CW.EventMask,
            [xcb.xproto.EventMask.StructureNotify |
             xcb.xproto.EventMask.FocusChange]
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
            xcb.xproto.FocusInEvent,
            self.cb_FocusInEvent,
            self.win.id
        )
        events.register_callback(
            xcb.xproto.FocusOutEvent,
            self.cb_FocusOutEvent,
            self.win.id
        )
        events.register_drag(self.cb_move_start, self.cb_move_drag,
                             self.cb_move_end, self.win.id,
                             'Mod1-1')
        events.register_drag(self.cb_resize_start, self.cb_resize_drag,
                             self.cb_resize_end, self.win.id, 'Mod1-3')


        events.register_buttonpress([self.cb_focus, self.cb_stack_raise],
                                    self.win.id, '1', propagate=True)
        events.register_buttonpress([self.cb_focus, self.cb_stack_raise],
                                    self.win.id, '2', propagate=True)
        events.register_buttonpress([self.cb_focus, self.cb_stack_raise],
                                    self.win.id, '3', propagate=True)

        self.map()

    def unmanage(self):
        self.frame.destroy()
        events.unregister_window(self.win.id)
        del state.wins[self.win.id]

    def stack_raise(self):
        self.layer.above(self)
        self.layer.stack()

    def focus(self):
        if self.focus_notify():
            packed = struct.pack(
                'BBH7I',
                event.Event.ClientMessageEvent,
                32,
                0,
                self.win.id,
                util.get_atom(state.conn, 'WM_PROTOCOLS'),
                util.get_atom(state.conn, 'WM_TAKE_FOCUS'),
                events.time, 0, 0, 0
            )
            state.conn.core.SendEvent(False, self.win.id, 0, packed)

        if self.can_focus():
            state.conn.core.SetInputFocusChecked(
                xcb.xproto.InputFocus.PointerRoot,
                self.win.id, events.time).check()

        self.focused()

    def focused(self):
        focus.above(self)
        self.frame.activate()

    def unfocused(self):
        self.frame.deactivate()

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
        focus.add(self)
        layers.default.add(self)
        self.layer.stack()
        self.frame.map()
        self.win.map()
        self.focus()

        self._unmapped = False

    def unmap(self):
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

    # Toggling

    def toggle_decorations(self):
        if (isinstance(self.frame, frame.Border) or
            isinstance(self.frame, frame.Full)):
            self.undecorate()
        else:
            self.decorate()

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
        return util.atom('WM_TAKE_FOCUS') in self.win.protocols

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
        return self.frame.resize_drag(e.root_x, e.root_y)

    def cb_resize_end(self, e):
        return self.frame.resize_end(e.root_x, e.root_y)

    def cb_move_start(self, e):
        return self.frame.move_start(e.event, e.root_x, e.root_y)

    def cb_move_drag(self, e):
        return self.frame.move_drag(e.root_x, e.root_y)

    def cb_move_end(self, e):
        return self.frame.move_end(e.root_x, e.root_y)

    def cb_ConfigureRequestEvent(self, e):
        pass

    def cb_MapRequestEvent(self, e):
        self.map()

    def cb_DestroyNotifyEvent(self, e):
        self.unmanage()

    def cb_UnmapNotifyEvent(self, e):
        if self._unmapped:
            return

        self.unmapped()

    def cb_FocusInEvent(self, e):
        if self._unmapped:
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
        if self._unmapped:
            return

        #if e.mode != xcb.xproto.NotifyMode.Normal:
            #return

        #if e.detail not in (xcb.xproto.NotifyDetail.Virtual,
                            #xcb.xproto.NotifyDetail.Nonlinear,
                            #xcb.xproto.NotifyDetail.NonlinearVirtual):
            #return

        if focus.focused() != self:
            self.unfocused()

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