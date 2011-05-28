# This is awful. Things will *not* stay like this.
# It's difficult to do mouse bindings in an extensible manner like key bindings.
# In particular, to be extensible, we'd need access to the Pyndow modules
# (just like config/keybind.py does), but those modules would in turn need
# access to this module. The key difference is that mouse bindings are set
# on a per-client basis, whereas key bindings tend to be set globally on the
# root window. (Thus, key bindings can be set in a vacuum, but mouse bindings
# cannot.)
#
# This setup will very like be changed to something like, "What mouse binding
# would you like 'window resizing' to be?" It may even get moved into option.py.

mousebinds = {
    'frame': {
        ('drag', 'Mod4-3'): {
            'start':     'self.frame.client.cb_resize_start',
            'drag':      'self.frame.client.cb_resize_drag',
            'end':       'self.frame.client.cb_resize_end',
            'grab':      True,
            'propagate': False,
            },
        ('drag', 'Mod4-1'): {
            'start':     'self.frame.client.cb_move_start',
            'drag':      'self.frame.client.cb_move_drag',
            'end':       'self.frame.client.cb_move_end',
            'grab':      True,
            'propagate': False,
            },
        ('click', '1'): {
            'action':    '[self.frame.client.cb_focus, ' + \
                         'self.frame.client.cb_stack_raise]',
            'grab':      True,
            'propagate': True,
            }
        },
    'non-client': {
        ('click', '1'): {
            'action':    'self.cb_stack_raise',
            'grab':      True,
            'propagate': True,
            }
        },
    'title': {
        ('drag', '1'): {
            'start':     'self.frame.client.cb_move_start',
            'drag':      'self.frame.client.cb_move_drag',
            'end':       'self.frame.client.cb_move_end',
            'grab':      True,
            'propagate': False,
            }
        },
    'button': {
        ('click', '1'): {
            'action':    'self.cb_buttonpress',
            'grab':      False,
            'propagate': False,
            },
        ('unclick', '1'): {
            'action':    '[self.cb_buttonrelease, self.cb_action]',
            'grab':      False,
            'propagate': False,
            }
        }
    }

