import ConfigParser
import distutils.sysconfig
import os
import os.path
import pwd
import re
import sys

class PyndowConfigParser(ConfigParser.SafeConfigParser):
    def optionxform(self, s):
        return s

    def getboolean(self, section, option):
        if self.get(section, option).lower() == 'yes':
            return True
        return False

    def gethex(self, section, option):
        return int(self.get(section, option), 16)

    def getlist(self, section, option):
        def clean(s):
            return s.replace('"', '').replace("'", '')

        return map(
            clean,
            self.get(section, option).split()
        )

    def getfloatlist(self, section, option):
        try:
            return map(
                float,
                self.getlist(section, option)
            )
        except ValueError:
            return self.getlist(section, option)

    def getintlist(self, section, option):
        try:
            return map(
                int,
                self.getlist(section, option)
            )
        except ValueError:
            return self.getlist(section, option)

    def get_option(self, section, option):
        assert option in option_types

        return option_types[option]['exec'](self, section, option)

    def get_global_configs(self):
        retval = {}

        if 'Global' in self.sections():
            for option in self.options('Global'):
                retval[option] = self.get_option('Global', option)

        return retval

    def get_keybindings(self):
        retval = {}

        if 'Keybindings' in self.sections():
            for option in self.options('Keybindings'):
                retval[option] = self.get('Keybindings', option)

        return retval

    def get_wmt_configs(self):
        retval = {}

        all_tilers = self.get_option('Global', 'all_tilers')

        for section in self.sections():
            for tiler in all_tilers:
                m = re.match(
                    '^(Workspace([0-9]+)-?|Monitor([0-9]+)-?|' + tiler + '-?){1,3}$',
                    section
                )
                if m:
                    wsid = int(m.group(2)) if m.group(2) else None
                    mid = int(m.group(3)) if m.group(3) else None
                    tiler = tiler if tiler.lower() in section.lower() else None

                    retval[(wsid, mid, tiler)] = {}

                    for option in self.options(m.group(0)):
                        retval[(wsid, mid, tiler)][option] = self.get_option(
                            m.group(0),
                            option
                        )

        return retval

config_path = os.path.join('/home/andrew/')
config_filename = 'config.ini'

# A list of supported options independent of section header.
# Please do not change settings here. The settings specified here
# are the minimal required for PyTyle to function properly.
option_types = {
    'decor_bg_active': {
        'exec': PyndowConfigParser.gethex,
        'default': 0x000000
    },
    'decor_bg_inactive': {
        'exec': PyndowConfigParser.gethex,
        'default': 0xffffff
    },
    'decor_title_active': {
        'exec': PyndowConfigParser.gethex,
        'default': 0xffffff
    },
    'decor_title_inactive': {
        'exec': PyndowConfigParser.gethex,
        'default': 0x000000
    },
    'decor_border_size': {
        'exec': PyndowConfigParser.getint,
        'default': 1
    },
    'decor_bottom_border_size': {
        'exec': PyndowConfigParser.getint,
        'default': 5
    },
    'decor_bottom_border_color': {
        'exec': PyndowConfigParser.gethex,
        'default': 0xffffff
    },
    'decor_thinborder_color': {
        'exec': PyndowConfigParser.gethex,
        'default': 0x000000
    },
    'all_tilers': {
        'exec': PyndowConfigParser.getlist,
        'default': ['Vertical']
    },
    'movetime_offset': {
        'exec': PyndowConfigParser.getfloat,
        'default': 0.5
    },
    'tilers': {
        'exec': PyndowConfigParser.getlist,
        'default': ['Vertical']
    },
    'ignore': {
        'exec': PyndowConfigParser.getlist,
        'default': []
    },
    'decorations': {
        'exec': PyndowConfigParser.getboolean,
        'default': True
    },
    'borders': {
        'exec': PyndowConfigParser.getboolean,
        'default': True
    },
    'border_width': {
        'exec': PyndowConfigParser.getint,
        'default': 2
    },
    'borders_active_color': {
        'exec': PyndowConfigParser.gethex,
        'default': 0xff0000,
    },
    'borders_inactive_color': {
        'exec': PyndowConfigParser.gethex,
        'default': 0x008800,
    },
    'borders_catchall_color': {
        'exec': PyndowConfigParser.gethex,
        'default': 0x3366ff,
    },
    'placeholder_bg_color': {
        'exec': PyndowConfigParser.gethex,
        'default': 0x000000,
    },
    'margin': {
        'exec': PyndowConfigParser.getintlist,
        'default': []
    },
    'padding': {
        'exec': PyndowConfigParser.getintlist,
        'default': []
    },
    'tile_on_startup': {
        'exec': PyndowConfigParser.getboolean,
        'default': False
    },
    'step_size': {
        'exec': PyndowConfigParser.getfloat,
        'default': 0.05
    },
    'width_factor': {
        'exec': PyndowConfigParser.getfloat,
        'default': 0.5
    },
    'height_factor': {
        'exec': PyndowConfigParser.getfloat,
        'default': 0.5
    },
    'rows': {
        'exec': PyndowConfigParser.getint,
        'default': 2
    },
    'columns': {
        'exec': PyndowConfigParser.getint,
        'default': 2
    },
    'push_down': {
        'exec': PyndowConfigParser.getint,
        'default': 25
    },
    'push_over': {
        'exec': PyndowConfigParser.getint,
        'default': 0
    },
    'horz_align': {
        'exec': PyndowConfigParser.get,
        'default': 'left'
    },
    'shallow_resize': {
        'exec': PyndowConfigParser.getboolean,
        'default': True
    }
}

# Specified in the "(Auto|Manual)Keybindings" section
keybindings = {}

# Settings specified in the "Global" section
glbls = {}

# Loads the configuration file. This is called automatically when
# this module is imported, but it can also be called again when
# the settings ought to be refreshed.
# If no configuration file exists, create one.
def load_config_file():
    global glbls, keybindings, wmt, paths

    config_file = os.path.join(config_path, config_filename)
    conf = PyndowConfigParser()
    conf.read(config_file)

    glbls = conf.get_global_configs()
    keybindings = conf.get_keybindings()

# Just a public accessor to get a list of all the keybindings
def get_keybindings():
    global keybindings

    return keybindings

# A public accessor to obtain a value for an option. It takes
# precedence into account, therefore, this function should
# always be called with the most information available, unless
# otherwise desired.
def get_option(option, wsid=None, mid=None, tiler=None):
    global glbls, option_types

    if option in glbls:
        return glbls[option]
    else:
        return option_types[option]['default']

    return None

load_config_file()
