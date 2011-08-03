from functools import partial

import state
import focus
import workspace
import misc
import popup.cycle

from client import Client, NormalClient
from layout.tile import VerticalLayout, HorizontalLayout

def with_focused(fun):
    def _with_focused():
        client = focus.focused()
        if client is not None:
            fun(client)

    return _with_focused

def with_focused_attr(meth_name):
    def _with_focused():
        client = focus.focused()
        if client is not None:
            if hasattr(client, meth_name):
                getattr(client, meth_name)()

    return _with_focused

def with_layout_attr(meth_name):
    def _with_layout():
        client = focus.focused()
        if client is not None:
            layout = client.layout()
            if hasattr(layout, meth_name):
                getattr(layout, meth_name)()

    return _with_layout

def quit():
    state.die = True
    misc.spawn('killall Xephyr')

wf  = with_focused
wfa = with_focused_attr
wla = with_layout_attr

keybinds = {
    'Mod4-e':           '`dolphin`',
    'Mod4-t':           '`konsole`',
    'Mod4-g':           '`geany`',
    'Mod4-r':           '`gmrun`',
    'Mod4-b':           '`chromium`',
    'Mod4-i':           '`gimp`',
    
    'Mod4-c':           wfa('close'),
    'Mod1-g':           wfa('toggle_catchall'),
    'Mod1-d':           wfa('toggle_decorations'),

    'Mod4-Right':       workspace.right,
    'Mod4-Left':        workspace.left,
    'Mod4-Shift-Right': wf(workspace.with_right),
    'Mod4-Shift-Left':  wf(workspace.with_left),

    'Mod1-a':           workspace.tile,
    'Mod1-u':           workspace.untile,
    'Mod1-z':           workspace.cycle,
    'Mod1-Mod4-v':      partial(workspace.tile, VerticalLayout),
    'Mod1-Mod4-h':      partial(workspace.tile, HorizontalLayout),
    'Mod1-h':           wla('master_size_decrease'),
    'Mod1-l':           wla('master_size_increase'),
    'Mod1-j':           wla('previous'),
    'Mod1-k':           wla('next'),
    'Mod1-Shift-j':     wla('move_previous'),
    'Mod1-Shift-k':     wla('move_next'),
    'Mod1-comma':       wla('master_decrement'),
    'Mod1-period':      wla('master_increment'),

    'Control-Mod1-c':   quit,
    }

keygrabs = {
    'Mod1-Tab':       (popup.cycle.start_next, popup.cycle.do_next, 
                       popup.cycle.end),
    'Mod1-Shift-Tab': (popup.cycle.start_prev, popup.cycle.do_prev,
                       popup.cycle.end),
    }

