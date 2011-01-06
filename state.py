import sys

import xcb, xcb.xproto

import cursor
import keysym

d = open('/home/andrew/pyndow.txt', 'w+')

die = False
conn = xcb.connect()
setup = conn.get_setup()
rsetup = setup.roots[0]
root = rsetup.root

pyndow = conn.generate_id()
conn.core.CreateWindow(rsetup.root_depth, pyndow, root, -1000, -1000, 1,
                       1, 0, xcb.xproto.WindowClass.InputOutput,
                       rsetup.root_visual,
                       xcb.xproto.CW.EventMask |
                       xcb.xproto.CW.OverrideRedirect,
                       [xcb.xproto.EventMask.PropertyChange, 1])
conn.core.MapWindow(pyndow)

grab_pointer = False
grab_keyboard = False

__kbmap = keysym.get_keyboard_mapping(conn)

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

def get_kbmap():
    global __kbmap

    if isinstance(__kbmap, xcb.xproto.GetKeyboardMappingCookie):
        __kbmap = __kbmap.reply()

    return __kbmap

def replay_pointer():
    conn.core.AllowEventsChecked(xcb.xproto.Allow.ReplayPointer,
                                 xcb.xproto.Time.CurrentTime).check()

def root_focus():
    conn.core.SetInputFocusChecked(xcb.xproto.InputFocus.PointerRoot,
                                   root,
                                   xcb.xproto.Time.CurrentTime).check()

def grab():
    conn.core.GrabServerChecked().check()

def ungrab():
    conn.core.UngrabServerChecked().check()

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

def test(e):
    print 'ahoy hoy!'

class Windows(object):
    def __init__(self):
        self.__ordered = []
        self.__mapping = {}

    def get_ordered(self):
        return self.__ordered[:]

    def __len__(self):
        return len(self.__ordered)

    def __setitem__(self, key, value):
        if key not in self.__ordered:
            self.__ordered.append(key)
        self.__mapping[key] = value

    def __delitem__(self, key):
        if key in self.__ordered:
            self.__ordered.remove(key)
            del self.__mapping[key]

    def __getitem__(self, key):
        return self.__mapping[key]

    def __contains__(self, item):
        return item in self.__ordered

    def __iter__(self):
        for client in self.__ordered:
            yield self.__mapping[client]

wins = Windows()