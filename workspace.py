from collections import OrderedDict

import xcb.xproto as xproto

import state
import focus
import floater

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

    for wid, client in state.windows.items():
        if not client.workspaces:
            continue # empty list => all workspaces

        if (__current in client.workspaces 
            and workspace not in client.workspaces):
            client.unmap(light=True)
        elif workspace in client.workspaces:
            client.maplight()

    __current = workspace

    if focusing:
        focus.fallback()

    return True

def left():
    i = __workspaces.values().index(__current)
    view(__workspaces.values()[(i - 1) % len(__workspaces)])

def right():
    i = __workspaces.values().index(__current)
    view(__workspaces.values()[(i + 1) % len(__workspaces)])

class Workspace(object):
    def __init__(self, name):
        self.__name = name
        self.floating = True
        self.floater = floater.new(self)
        self.layouts = []

    def add(self, client):
        self.floater.add(client)

    def mapped(self, client):
        self.floater.mapped(client)

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, newname):
        if newname != self.__name:
            self.__name = newname
            return True
        return False

__workspaces['one'] = Workspace('one')
__workspaces['two'] = Workspace('two')

__current = __workspaces['one']
__visible = [__workspaces['one']]
__hidden = [__workspaces['two']]

