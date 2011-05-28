import events

mousebinds = None

# This needs to be smarter.
execfile('/home/andrew/clones/pyndow/config/default/mousebind.py')

assert isinstance(mousebinds, dict)

def register(section, self, winid):
    assert section in mousebinds

    for (bindtype, bindkey) in mousebinds[section]:
        opt = mousebinds[section][(bindtype, bindkey)]

        if bindtype == 'drag':
            events.register_drag(eval(opt['start']), eval(opt['drag']),
                                eval(opt['end']), winid, bindkey,
                                propagate=opt['propagate'], grab=opt['grab'])
        elif bindtype == 'click':
            events.register_buttonpress(eval(opt['action']), winid, bindkey,
                                       propagate=opt['propagate'],
                                       grab=opt['grab'])
        elif bindtype == 'unclick':
            events.register_buttonrelease(eval(opt['action']), winid, bindkey,
                                         propagate=opt['propagate'],
                                         grab=opt['grab'])
        else:
            assert False, '"%s" is not a valid mouse binding type' % bindtype

