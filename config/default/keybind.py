import state
import focus
from client import Client, NormalClient
from layout.tile import VerticalLayout
import workspace
import misc

def with_focused(fun):
    def _with_focused():
        client = focus.focused()
        if client is not None:
            fun(client)

    return _with_focused

def with_layout(fun):
    def _with_layout():
        client = focus.focused()
        if client is not None:
            fun(client.layout())

    return _with_layout

def quit():
    state.die = True
    misc.spawn('killall Xephyr')

keybinds = {
    'Mod4-e':           '`dolphin`',
    'Mod4-t':           '`konsole`',
    'Mod4-g':           '`geany`',
    'Mod4-r':           '`gmrun`',
    'Mod4-b':           '`chromium`',
    'Mod4-i':           '`gimp`',
    
    'Mod4-c':           with_focused(Client.close),
    'Mod1-g':           with_focused(NormalClient.toggle_catchall),
    'Mod1-d':           with_focused(NormalClient.toggle_decorations),

    'Mod4-Right':       workspace.right,
    'Mod4-Left':        workspace.left,
    'Mod4-Shift-Right': with_focused(workspace.with_right),
    'Mod4-Shift-Left':  with_focused(workspace.with_left),

    'Mod1-a':           workspace.tile,
    'Mod1-u':           workspace.untile,
    'Mod1-h':           with_layout(VerticalLayout.master_size_decrease),
    'Mod1-l':           with_layout(VerticalLayout.master_size_increase),
    'Mod1-j':           with_layout(VerticalLayout.previous),
    'Mod1-k':           with_layout(VerticalLayout.next),
    'Mod1-Shift-j':     with_layout(VerticalLayout.move_previous),
    'Mod1-Shift-k':     with_layout(VerticalLayout.move_next),
    'Mod1-comma':       with_layout(VerticalLayout.master_decrement),
    'Mod1-period':      with_layout(VerticalLayout.master_increment),

    'Control-Mod1-c':   quit,
}
