import xcb.xproto

import state

class Layer(object):
    __layers = []
    __default = None

    @staticmethod
    def set_default(default):
        """Sets the default layer.

        This must be called after initializing the layers. Otherwise, it's
        possible that a window may not be in any layer, and that's bad."""
        Layer.__default = default

    def __init__(self):
        """Starts the stack and adds itself to the list of layers."""
        self.__stack = []

        Layer.__layers.append(self)

    def get_bottom_sibling(self):
        """Fetches the top-most window of the layer beneath this layer."""
        ind = Layer.__layers.index(self)

        # Bottom layer has no bottom sibling
        # (Also our base case.)
        if not ind:
            return None

        beneath = Layer.__layers[ind - 1]

        # No windows in this layer... move to the next
        if not len(beneath):
            return beneath.get_bottom_sibling()

        # Return the top most window...
        return beneath.top()

    def get_top_sibling(self):
        """Fetches the top-most window of the current layer."""
        if not len(self):
            ind = Layer.__layers.index(self)

            # Base case
            if not ind:
                return None
            else:
                return Layer.__layers[ind - 1].get_top_sibling()
        else:
            return self.top()

    def stack(self):
        """Stack the windows. Lowest windows first."""
        sibling = self.get_bottom_sibling()

        for client in self.__stack:
            if sibling is None:
                client.configure(stack_mode=xcb.xproto.StackMode.Below)
            else:
                client.configure(sibling=sibling.parent_id(),
                                 stack_mode=xcb.xproto.StackMode.Above)

            sibling = client

    def above(self, win):
        """Moves a window to the top of this layer."""
        assert win in self

        self.__stack.remove(win)
        self.__stack.append(win)

    def below(self, win):
        """Moves a window to the bottom of this layer."""
        assert win in self

        self.__stack.remove(win)
        self.__stack.insert(0, win)

    def add(self, win):
        """
        Adds a window to the top of this layer.
        """
        if win in self:
            return

        for layer in Layer.__layers:
            if layer == self:
                continue

            if win in layer:
                layer.remove(win)

        win.layer = self
        self.__stack.append(win)

    def remove(self, win):
        """
        Removes a window from this layer and puts it in the default layer.
        """
        if win not in self:
            return

        win.layer = None
        self.__stack.remove(win)

        return self

    def top(self):
        """Returns the top most window in this layer."""
        return self.visible()[-1]

    def visible(self):
        return [client for client in self.__stack if client.mapped]

    def __len__(self):
        return len(self.visible())

    def __contains__(self, item):
        return item in self.__stack

# The first layer declared is the bottom layer,
# and the last layer declared is the top layer.
desktop = Layer()
below = Layer()
default = Layer()
dock = Layer()
above = Layer()
fullscreen = Layer()

Layer.set_default(default)
