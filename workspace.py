import traceback
from collections import OrderedDict

import xcb.xproto as xproto

import state
import hooks
import focus
import layout
import monitor

state.workspaces = OrderedDict()
_current = __visible = __hidden = None

def determine_focus():
    client = focus.focused()
    if client:
        if client.workspace is not None:
            client.workspace.focused()
        else:
            geom = client.frame.parent.geom
            monitor_focus(monitor.which(geom['x'], geom['y']))
    else:
        qp = state.core.QueryPointer(state.root).reply()
        monitor_focus(monitor.which(qp.root_x, qp.root_y))

def monitor_focus(monitor):
    for workspace in state.workspaces.itervalues():
        if workspace.monitor is monitor:
            workspace.focused()
            return True

    return False

def current():
    return _current

def visible():
    return __visible

def hidden():
    return __hidden

def names():
    return [w.name for w in state.workspaces]

def view_name(name, focusing=True):
    if name not in state.workspaces:
        return False
    return view(state.workspaces[name], focusing=focusing)

def view(workspace, focusing=True):
    global _current, __visible, __hidden
    if workspace not in state.workspaces.values() or workspace == _current:
        return False

    old = _current
    _current = workspace

    old.replace(_current)

    if focusing:
        focus.fallback()

    return True

def get_clients(workspace):
    for _, client in state.windows.iteritems():
        if workspace == client.workspace:
            yield client

def tile(layoutClass=None):
    _current.tile(layoutClass=layoutClass)

def untile():
    _current.untile()

def cycle():
    _current.cycle()

def with_left(client):
    work = __get_left()
    if _current.remove(client):
        view(work)
        work.add_and_assign_layout(client)

def with_right(client):
    work = __get_right()
    if _current.remove(client):
        view(work)
        work.add_and_assign_layout(client)

def left():
    view(__get_left())

def right():
    view(__get_right())

def __get_left():
    i = state.workspaces.values().index(_current)
    return state.workspaces.values()[(i - 1) % len(state.workspaces)]

def __get_right():
    i = state.workspaces.values().index(_current)
    return state.workspaces.values()[(i + 1) % len(state.workspaces)]

class Workspace(object):
    def __init__(self, name):
        self.__name = name
        self.monitor = None
        self.__workarea = {}
        self.floater = layout.floater.FloatLayout(self)
        self.layouts = []
        self.cycle_lays = [layout.tilers['VerticalLayout'](self),
                           layout.tilers['HorizontalLayout'](self)]
        self.alternate = None

        for lay in reversed(self.cycle_lays):
            self._add_layout(lay)

    @property
    def workarea(self):
        if self.monitor is None:
            return None
        
        wa = monitor.workarea(self.monitor)

        self.__workarea['x'], self.__workarea['y'] = wa[0], wa[1]
        self.__workarea['width'], self.__workarea['height'] = wa[2], wa[3]
        return self.__workarea

    def workarea_changed(self):
        if self.alternate is None:
            self.floater.workarea_changed()
        else:
            self.alternate.workarea_changed()

    def show(self, monitor):
        self.monitor = monitor
        if self.alternate is None:
            self.floater.restore_all()
        else:
            self.alternate.place()

        for client in state.windows.itervalues():
            if client.workspace is self:
                client.maplight()

    def hide(self):
        if self.alternate is None:
            self.floater.save_all()

        for client in state.windows.itervalues():
            if client.workspace is self:
                client.unmap(light=True)
        self.monitor = None

    def replace(self, workspace):
        if self is workspace:
            return

        monitor = self.monitor
        self.hide()
        workspace.show(monitor)

    def focus(self):
        client = focus.focus_workspace(self)
        if client:
            client.focus()
        else:
            state.root_focus()
            self.focused()

    def focused(self):
        global _current
        _current = self

    def add(self, client):
        assert client.workspace is None, \
               '%s is already on workspace %s' % (client, client.workspace)

        client.workspace = self

    def add_and_assign_layout(self, client):
        self.add(client)
        self.assign_layout(client)

    def remove(self, client):
        if self != client.workspace:
            return False

        self.hide_client(client)
        client.workspace = None

        return True

    def hide_client(self, client):
        # Ensure that it is no longer in any layout
        if client in self.floater:
            self.floater.remove_one(client)
        for lay in self.layouts:
            if client in lay:
                lay.remove_one(client)

    def assign_layout(self, client):
        if client not in self.floater:
            self.floater.add(client)

        if self.alternate is not None and client not in self.alternate:
            self.alternate.add(client)

    def get_layout(self, client):
        if self.alternate is not None and client in self.alternate:
            return self.alternate
        return self.floater

    def _find_layout(self, layoutClass):
        for lay in self.layouts:
            if isinstance(lay, layoutClass):
                return lay

        return layoutClass(self)

    def _add_layout(self, lay):
        if lay in self.layouts:
            self.layouts.remove(lay)
        self.layouts.append(lay)

    def cycle(self):
        if self.alternate is None or self.alternate not in self.cycle_lays:
            return

        nextLayout = self.cycle_lays[(self.cycle_lays.index(self.alternate) + 1) 
                                     % len(self.cycle_lays)]
        self.tile(layoutClass=nextLayout.__class__)

    def tile(self, layoutClass=None):
        if layoutClass is not None:
            self._add_layout(self._find_layout(layoutClass))
        else:
            if not self.layouts:
                self._add_layout(self.cycle_lays[0])

        self.alternate = self.layouts[-1]
        for client in self.floater.clients():
            force_master = True if client is focus.focused() else False
            self.alternate.add(client, doplace=False, force_master=force_master)

        self.alternate.place()

    def untile(self):
        if self.alternate is None:
            return

        self.alternate.remove_all()
        self.alternate = None

        if focus.focused():
            focus.focused().stack_raise()

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, newname):
        if newname != self.__name:
            self.__name = newname
            return True
        return False

    def __str__(self):
        return self.__name

state.workspaces['one'] = Workspace('one')
state.workspaces['two'] = Workspace('two')

state.workspaces['one'].monitor = 0

_current = state.workspaces['one']
__visible = [state.workspaces['one']]
__hidden = [state.workspaces['two']]

