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
        if not client.workspaces:
            continue # empty list => all workspaces

        if (old in client.workspaces 
            and __current not in client.workspaces):
            client.unmap(light=True)
        elif __current in client.workspaces:
            client.maplight()

    if focusing:
        focus.fallback()

    return True

def get_clients(workspace):
    for _, client in state.windows.iteritems():
        if not client.workspaces or workspace in client.workspaces:
            yield client

def tile():
    __current.tile()

def untile():
    __current.untile()

def with_left(client):
    work = __get_left()
    if __current.remove(client):
        work.add(client)
        view(work)

def with_right(client):
    work = __get_right()
    if __current.remove(client):
        work.add(client)
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
        self.layouts = []
        self.alternate = None

    def add(self, client):
        if self in client.workspaces:
            return
        client.workspaces.append(self)
        self.floater.add(client)

        if self.alternate is not None:
            self.alternate.add(client)

    def remove(self, client):
        if self not in client.workspaces:
            return False

        client.workspaces.remove(self)
        self.floater.remove(client)
        for lay in self.layouts:
            lay.remove(client)

        return True

    def get_layout(self, client):
        if self.alternate is not None and client in self.alternate:
            return self.alternate
        return self.floater

    def tile(self):
        self.floater.save()
        for client in self.floater.clients():
            self.layouts[0].add(client)
            self.layouts[0].place(client)
        self.alternate = self.layouts[0]

    def untile(self):
        if self.alternate is None:
            return

        self.floater.restore()
        self.alternate = None

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

