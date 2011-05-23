import state

class Layout(object):
    def __init__(self, workspace):
        self._windows = {}
        self._workspace = workspace

    def place(self, client):
        assert False, 'subclass responsibility'

    def add(self, client):
        if client.win.id in self._windows:
            return
        self._windows[client.win.id] = {
            'x': None, 'y': None, 'width': None, 'height': None,
        }

    def remove(self, client):
        if client.win.id not in self._windows:
            return
        del self._windows[client.win.id]

    def clients(self):
        for wid in self._windows.iterkeys():
            if not state.windows[wid].iconified:
                yield state.windows[wid]

    def resize_start(self, client, root_x, root_y, event_x, event_y,
                     direction=None):
        return { 'grab': False }

    def resize_drag(self, client, root_x, root_y, event_x, event_y):
        pass

    def resize_end(self, client, root_x, root_y):
        pass

    def move_start(self, client, root_x, root_y):
        return { 'grab': False }

    def move_drag(self, client, root_x, root_y):
        pass

    def move_end(self, client, root_x, root_y):
        pass

    @property
    def workspace(self):
        return self._workspace

    @workspace.setter
    def workspace(self, newwork):
        if newwork != self._workspace:
            self._workspace = newwork
            return True
        return False

    def __contains__(self, client):
        return client in self.clients()

import layout.floater

