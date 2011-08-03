import state
import events
import misc

from config.keybind import keybinds, keygrabs

def init():
    for key_string in keybinds:
        cmds = keybinds[key_string]

        if not isinstance(cmds, list):
            cmds = [cmds]
        
        for cmd in cmds:
            # I want to close over 'cmd', but it's mutable. I've used
            # a nastry trick that's explained here:
            # http://stackoverflow.com/questions/233673/lexical-closures-in-python/235764#235764
            if (isinstance(cmd, basestring) 
                and cmd.startswith('`') and cmd.endswith('`')):
                def callback(e, cmd=cmd):
                    misc.spawn(cmd[1:-1])
            else:
                def callback(e, cmd=cmd):
                    cmd()

            if not events.register_keypress(callback, state.root, key_string):
                print 'Could not bind %s to %s' % (key_string, cmd)

    for key_string in keygrabs:
        (start, step, end) = keygrabs[key_string]
        events.register_keygrab(start, step, end, state.root, key_string)

