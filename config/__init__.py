options = None

# This needs to be smarter
execfile('/home/andrew/clones/pyndow/config/default/option.py')

assert isinstance(options, dict)

def option(name):
    assert name in options

    return options[name]

get_option = option

