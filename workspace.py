from collections import OrderedDict

import xcb.xproto as xproto

import state
import hooks
import focus
import layout

__workspaces = OrderedDict()
__current = __visible = __hidden = None

def current():
    return __current

def visible():
    return __visible

def hidden():
    return __hidden

def all():
    return __workspaces

def names():
    return [w.name for w in __workspaces]

def view_name(name, focusing=True):
    if name not in __workspaces:
        return False
    return view(__workspaces[name], focusing=focusing)

def view(workspace, focusing=True):
    global __current, __visible, __hidden
    if workspace not in __workspaces.values() or workspace == __current:
        return False

    old = __current
    __current = workspace

    for wid, client in state.windows.iteritems():
        if client.workspace is None:
            continue # None => all workspaces

        if old == client.workspace and __current != client.workspace:
            client.unmap(light=True)
        elif __current == client.workspace:
            client.maplight()

    if focusing:
        focus.fallback()

    return True

def get_clients(workspace):
    for _, client in state.windows.iteritems():
        if workspace == client.workspace:
            yield client

def tile():
    __current.tile()

def untile():
    __current.untile()

def with_left(client):
    work = __get_left()
    if __current.remove(client):
        work.add_and_assign_layout(client)
        view(work)

def with_right(client):
    work = __get_right()
    if __current.remove(client):
        work.add_and_assign_layout(client)
        view(work)

def left():
    view(__get_left())

def right():
    view(__get_right())

def __get_left():
    i = __workspaces.values().index(__current)
    return __workspaces.values()[(i - 1) % len(__workspaces)]

def __get_right():
    i = __workspaces.values().index(__current)
    return __workspaces.values()[(i + 1) % len(__workspaces)]

class Workspace(object):
    def __init__(self, name):
        self.__name = name
        self.floater = layout.floater.FloatLayout(self)
        self.layouts = [layout.tile.VerticalLayout(self)]
        self.alternate = None

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

        self.hide(client)
        client.workspace = None

        return True

    def hide(self, client):
        # Ensure that it is no longer in any layout
        if client in self.floater:
            self.floater.remove(client)
        for lay in self.layouts:
            if client in lay:
                lay.remove(client)

    def assign_layout(self, client):
        if client not in self.floater:
            self.floater.add(client)
            self.floater.save(client)

        if self.alternate is not None and client not in self.alternate:
            self.alternate.add(client)

    def get_layout(self, client):
        if self.alternate is not None and client in self.alternate:
            return self.alternate
        return self.floater

    def tile(self):
        self.floater.save_all()
        self.alternate = self.layouts[0]
        for client in self.floater.clients():
            self.alternate.add(client)

        self.alternate.place()

    def untile(self):
        if self.alternate is None:
            return

        self.alternate = None
        self.floater.restore_all()
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

__workspaces['one'] = Workspace('one')
__workspaces['two'] = Workspace('two')

__current = __workspaces['one']
__visible = [__workspaces['one']]
__hidden = [__workspaces['two']]


# hooks.attach('client_manage', lambda client: current().add(client)) 

