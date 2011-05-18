from collections import OrderedDict
import sys

import xcb
import xcb.xproto as xproto

import xpybutil.cursor as cursor
import xpybutil.keysym as keysym

d = open('/home/andrew/pyndow.txt', 'w+')

die    = False
conn   = xcb.connect()
core   = conn.core
setup  = conn.get_setup()
rsetup = setup.roots[0]
root   = rsetup.root

# Temporary hack
rsetup.width_in_pixels  = 1920
rsetup.height_in_pixels = 1080

pyndow = conn.generate_id()
core.CreateWindow(rsetup.root_depth, pyndow, root, -1000, -1000, 1,
                       1, 0, xproto.WindowClass.InputOutput, rsetup.root_visual,
                       xproto.CW.EventMask | xproto.CW.OverrideRedirect,
                       [xproto.EventMask.PropertyChange, 1])
core.MapWindow(pyndow)

grab_pointer  = False
grab_keyboard = False

__kbmap = keysym.get_keyboard_mapping(conn)
__keystomods = keysym.get_keys_to_mods(conn)

FC = cursor.FontCursor
cursors = {
    'LeftPtr': cursor.create_font_cursor(conn, FC.LeftPtr),
    'Fleur': cursor.create_font_cursor(conn, FC.Fleur),
    'Watch': cursor.create_font_cursor(conn, FC.Watch),
    'TopSide': cursor.create_font_cursor(conn, FC.TopSide),
    'TopRightCorner': cursor.create_font_cursor(conn, FC.TopRightCorner),
    'RightSide': cursor.create_font_cursor(conn, FC.RightSide),
    'BottomRightCorner': cursor.create_font_cursor(conn, FC.BottomRightCorner),
    'BottomSide': cursor.create_font_cursor(conn, FC.BottomSide),
    'BottomLeftCorner': cursor.create_font_cursor(conn, FC.BottomLeftCorner),
    'LeftSide': cursor.create_font_cursor(conn, FC.LeftSide),
    'TopLeftCorner': cursor.create_font_cursor(conn, FC.TopLeftCorner)
}

# The set of all windows being managed.
windows = OrderedDict()

# The set of all existing workspaces.
workspaces = []

def reconnect():
    global conn

    conn = xcb.connect()

def get_kbmap():
    global __kbmap

    if isinstance(__kbmap, xproto.GetKeyboardMappingCookie):
        __kbmap = __kbmap.reply()

    return __kbmap

def set_kbmap(kbmap):
    global __kbmap

    __kbmap = kbmap

def get_mod_for_key(keycode):
    return keycode in __keystomods and __keystomods[keycode] or 0

def set_keys_to_mods(ktom):
    global __keystomods

    __keystomods = ktom

def replay_pointer():
    core.AllowEventsChecked(xproto.Allow.ReplayPointer,
                            xproto.Time.CurrentTime).check()

def root_focus():
    core.SetInputFocusChecked(xproto.InputFocus.PointerRoot, root,
                              xproto.Time.CurrentTime).check()

def grab():
    core.GrabServerChecked().check()

def ungrab():
    core.UngrabServerChecked().check()

def sync():
    core.GetInputFocus().reply()

def debug(s):
    print >> d, s
    d.flush()

def debug_obj(o, f=False):
    out = sys.stdout
    if f:
        out = d

    print >> out, o
    for i in dir(o):
        if i.startswith('__'): continue
        print >> out, i, getattr(o, i)
    print >> out, '-' * 45

    out.flush()

