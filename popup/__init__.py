import state
import window
import events

class _PopupWindow(window.GeometryWindow):
    def __init__(self):
        window.GeometryWindow.__init__(self, self.id)

    def destroy(self):
        events.unregister_window(self.id)
        state.conn.core.DestroyWindow(self.id)

    def clear(self):
        state.conn.core.ClearArea(0, self.id, 0, 0, 0, 0)

    def map(self):
        window.GeometryWindow.map(self)
        self.render()

    def render(self):
        pass