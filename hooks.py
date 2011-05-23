import state

__hooks = {
    'client_manage': [],
    'client_unmanage': [],
    'client_mapped': [],
    'client_unmapped': [],
    'client_iconified': [],
    'client_deiconified': [],
}

def attach(hook, fun):
    assert hook in __hooks, '%s is not a valid hook' % hook

    __hooks[hook].append(fun)

def fire(hook, *args, **kwargs):
    assert hook in __hooks, '%s is not a valid hook' % hook

    for fun in __hooks[hook]:
        fun(*args, **kwargs)

