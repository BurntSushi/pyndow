import xcb.xproto as xproto

import state

def new(workspace):
    return FloatLayout(workspace)

class FloatLayout(object): # Should inherit from abstract class 'Layout'
    def __init__(self, workspace):
        self.__workspace = workspace
        self.x = self.y = 0

    def add(self, client):
        pass

    def mapped(self, client):
        client.configure(x=self.x, y=self.y)
        self.x += 50
        self.y += 50

    @property
    def workspace(self):
        return self.__workspace

    @workspace.setter
    def workspace(self, newwork):
        if newwork != self.__workspace:
            self.__workspace = newwork
            return True
        return False

