#!/usr/bin/env python2
#    TerminatorConfig - layered config classes
#    Copyright (C) 2006-2010  cmsj@tenshu.net
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, version 2 only.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

"""Terminator by Chris Jones <cmsj@tenshu.net>

Classes relating to configuration

>>> DEFAULTS['global_config']['focus']
'click'
>>> config = Config()
>>> config['focus'] = 'sloppy'
>>> config['focus']
'sloppy'
>>> DEFAULTS['global_config']['focus']
'click'
>>> config2 = Config()
>>> config2['focus']
'sloppy'
>>> config2['focus'] = 'click'
>>> config2['focus']
'click'
>>> config['focus']
'click'
>>> config['geometry_hinting'].__class__.__name__
'bool'
>>> plugintest = {}
>>> plugintest['foo'] = 'bar'
>>> config.plugin_set_config('testplugin', plugintest)
>>> config.plugin_get_config('testplugin')
{'foo': 'bar'}
>>> config.plugin_get('testplugin', 'foo')
'bar'
>>> config.plugin_get('testplugin', 'foo', 'new')
'bar'
>>> config.plugin_get('testplugin', 'algo')
Traceback (most recent call last):
...
KeyError: 'ConfigBase::get_item: unknown key algo'
>>> config.plugin_get('testplugin', 'algo', 1)
1
>>> config.plugin_get('anothertestplugin', 'algo', 500)
500
>>> config.get_profile()
'default'
>>> config.set_profile('my_first_new_testing_profile')
>>> config.get_profile()
'my_first_new_testing_profile'
>>> config.del_profile('my_first_new_testing_profile')
>>> config.get_profile()
'default'
>>> config.list_profiles().__class__.__name__
'list'
>>> config.options_set({})
>>> config.options_get()
{}
>>>

"""

import platform
import os
from copy import copy
from configobj.configobj import ConfigObj, flatten_errors
from configobj.validate import Validator
from borg import Borg
from util import dbg, err, DEBUG, get_config_dir, dict_diff
#import pout
#pout.inject()
from gi.repository import Gio

DEFAULTS = {
        'global_config':   {
            'dbus'                  : False,
            'focus'                 : 'click',
            'handle_size'           : -1,
            'geometry_hinting'      : False,
            'window_state'          : 'normal',
            'borderless'            : False,
            'extra_styling'         : True,
            'tabs_hidden'           : False,
            'tab_position'          : 'bottom',
            'broadcast_default'     : 'off',
            'close_button_on_tab'   : False,
            'hide_tabbar'           : False,
            'scroll_tabbar'         : False,
            'homogeneous_tabbar'    : True,
            'hide_from_taskbar'     : False,
            'always_on_top'         : False,
            'hide_on_lose_focus'    : False,
            'sticky'                : False,
            'use_custom_url_handler': False,
            'custom_url_handler'    : '',
            'disable_real_transparency' : False,
            'do_not_save_dotnew'    : True,
            'title_hide_tabcaption' : True,
            'title_hide_path'       : False,
            'title_hide_userhost'   : False,
            'title_hide_sizetext'   : False,
            'title_transmit_bg_color' : '#3d4b05',
            'title_transmit_fg_color' : '#edd400',
            'title_receive_bg_color'  : '#204a87',
            'title_receive_fg_color'  : '#fce94f',
            'title_inactive_bg_color' : '#191d07',
            'title_inactive_fg_color' : '#4e9a06',
            'inactive_color_offset': 0.8,
            'enabled_plugins'       : ['LaunchpadBugURLHandler',
                                       'LaunchpadCodeURLHandler',
                                       'APTURLHandler'],
            #'suppress_multiple_term_dialog': False,
            'suppress_multiple_term_dialog': True, # XXX DEBUG
            'always_split_with_profile': True,
            'title_use_system_font' : True,
            'title_font'            : 'Sans 11',
            'putty_paste_style'     : False,
            'smart_copy'            : True,
        },
        'keybindings': {
            'zoom_in'          : '<Control>plus',
            'zoom_out'         : '<Control>minus',
            'zoom_normal'      : '<Control>0',
            'new_tab'          : '<Shift><Control>t',
            'cycle_next'       : '<Control>Tab',
            'cycle_prev'       : '<Shift><Control>Tab',
            'go_next'          : '<Shift><Control>n',
            'go_prev'          : '<Shift><Control>p',
            'go_up'            : '<Alt>Up',
            'go_down'          : '<Alt>Down',
            'go_left'          : '<Alt>Left',
            'go_right'         : '<Alt>Right',
            'rotate_cw'        : '<Super>r',
            'rotate_ccw'       : '<Super><Shift>r',
            'split_horiz'      : '<Shift><Control>o',
            'split_vert'       : '<Shift><Control>e',
            'close_term'       : '<Shift><Control>w',
            'copy'             : '<Shift><Control>c',
            'paste'            : '<Shift><Control>v',
            'toggle_scrollbar' : '<Shift><Control>s',
            'search'           : '<Shift><Control>f',
            'page_up'          : '',
            'page_down'        : '',
            'page_up_half'     : '',
            'page_down_half'   : '',
            'line_up'          : '',
            'line_down'        : '',
            'close_window'     : '<Shift><Control>q',
            'resize_up'        : '<Shift><Control>Up',
            'resize_down'      : '<Shift><Control>Down',
            'resize_left'      : '<Shift><Control>Page_Up',
            'resize_right'     : '<Shift><Control>Page_Down',
            'move_tab_right'   : '<Shift><Control>Right',
            'move_tab_left'    : '<Shift><Control>Left',
            'toggle_zoom'      : '<Shift><Control>x',
            'scaled_zoom'      : '<Shift><Control>z',
            'next_tab'         : '<Control>Right',
            'prev_tab'         : '<Control>Left',
            'switch_to_tab_1'  : '',
            'switch_to_tab_2'  : '',
            'switch_to_tab_3'  : '',
            'switch_to_tab_4'  : '',
            'switch_to_tab_5'  : '',
            'switch_to_tab_6'  : '',
            'switch_to_tab_7'  : '',
            'switch_to_tab_8'  : '',
            'switch_to_tab_9'  : '',
            'switch_to_tab_10' : '',
            'full_screen'      : 'F11',
            'reset'            : '<Shift><Control>r',
            'reset_clear'      : '<Shift><Control>g',
            #'hide_window'      : '<Shift><Control><Alt>a',
            'hide_window'      : '',
            # no group bindings, it can wreak havoc for user that does know
            # nothing 'bout. One who uses grouping will re-bind by self.
            #'group_all'        : '<Super>g',
            #'group_all_toggle' : '',
            #'ungroup_all'      : '<Shift><Super>g',
            #'group_tab'        : '<Super>t',
            #'group_tab_toggle' : '',
            #'ungroup_tab'      : '<Shift><Super>t',
            #'broadcast_group'  : '<Alt>g',
            #'broadcast_all'    : '<Alt>a',
            #'broadcast_off'    : '<Alt>o',
            'group_all'        : '',
            'group_all_toggle' : '',
            'ungroup_all'      : '',
            'group_tab'        : '',
            'group_tab_toggle' : '',
            'ungroup_tab'      : '',
            'broadcast_group'  : '',
            'broadcast_all'    : '',
            'broadcast_off'    : '',
            'insert_number'    : '<Super>1',
            'insert_padded'    : '<Super>0',
            'new_window'       : '<Shift><Control>i',
            'new_terminator'   : '<Super>i',
            'edit_window_title': '<Control><Alt>w',
            'edit_tab_title'   : '<Control><Alt>a',
            'hide_tab_bar'     : '<Control><Alt>t',
            'edit_terminal_title': '<Control><Alt>x',
            'layout_launcher'  : '<Alt>l',
            'next_profile'     : '',
            'previous_profile' : '',
            'help'             : 'F1'
        },
        'profiles': {
            'default':  {
                'allow_bold'            : True,
                'audible_bell'          : False,
                'visible_bell'          : False,
                'urgent_bell'           : False,
                'icon_bell'             : True,
                'background_color'      : '#191d07',
                'background_darkness'   : 0.9,
                'background_type'       : 'solid',
                'backspace_binding'     : 'ascii-del',
                'delete_binding'        : 'escape-sequence',
                'color_scheme'          : 'grey_on_black',
                'cursor_blink'          : True,
                'cursor_shape'          : 'block',
                'cursor_color'          : '#73d216',
                'cursor_color_fg'       : True,
                'term'                  : 'xterm-256color',
                'colorterm'             : 'truecolor',
                'font'                  : 'Source Code Pro 15',
                'foreground_color'      : '#fce94f',
                'show_titlebar'         : True,
                'scrollbar_position'    : 'hidden',
                'scroll_background'     : True,
                'scroll_on_keystroke'   : True,
                'scroll_on_output'      : False,
                'scrollback_lines'      : 1000,
                'scrollback_infinite'   : False,
                'exit_action'           : 'close',
                # no fancy palettes as default, please. Use math then let user fiddle.
                'palette' : "#000000:#aa0000:#00aa00:#aa5500:#0000aa:#aa00aa:#00aaaa:#aaaaaa:#555555:#ff5555:#55ff55:#ffff55:#5555ff:#ff55ff:#55ffff:#ffffff",
                'word_chars'            : '-,./?%&#:_',
                'mouse_autohide'        : True,
                'login_shell'           : False,
                'use_custom_command'    : False,
                'custom_command'        : '',
                'use_system_font'       : True,
                'use_theme_colors'      : False,
                'encoding'              : 'UTF-8',
                'active_encodings'      : ['UTF-8', 'ISO-8859-1'],
                'focus_on_close'        : 'auto',
                'force_no_bell'         : False,
                'cycle_term_tab'        : True,
                'copy_on_selection'     : False,
                'rewrap_on_resize'      : True,
                'split_to_group'        : False,
                'autoclean_groups'      : True,
                'http_proxy'            : '',
                'ignore_hosts'          : ['localhost','127.0.0.0/8','*.local'],
            },
        },
        'layouts': {
                'default': {
                    'NewT': {
                        'parent': '',
                        'type': 'Defstub',
                        'caption': 'NC',
                        'directory': '',
                        '_lastwdir': '',
                        'dirfixed': False,
                        'title': '',
                        'titlefixed': False,
                        'term_env': '',
                        'term_command': '',
                        'profile': 'default',
                        'histfile': '',
                        '_histfile': '',
                        'envfile': '',
                        '_envfile': '',
                        '_tabnext': 0,
                    },
                    'c00w': {
                        'type': 'Window',
                        'title': '',
                        'parent': ''
                        },
                    'c01t': {
                        'type': 'Terminal',
                        'parent': 'c00w',
                        'profile': 'default',
                        'caption': '',
                        'title': '',
                        'titlefixed': False,
                        'directory': '',
                        'dirfixed': '',
                        'term_env': '',
                        'term_command': '',
                        'histfile': '',
                        'envfile': '',
                        },
                    }
                },
        'plugins': {
        },
}

class Config(object):
    """Class to provide a slightly richer config API above ConfigBase"""
    base = None
    profile = None
    system_mono_font = None
    system_prop_font = None
    system_focus = None
    namenum = 0

    def __init__(self, profile='default'):

        self.base = ConfigBase()
        self.set_profile(profile)
        self.connect_gsetting_callbacks()

    def __getitem__(self, key, default=None):
        """Look up a configuration item"""
        return(self.base.get_item(key, self.profile, default=default))

    def __setitem__(self, key, value):
        """Set a particular configuration item"""
        return(self.base.set_item(key, value, self.profile))

    # FIXME wontfix: names are properly sortable up to 99. Thats plenty.
    def name_next(self, reset=False):
        if reset:
            Config.namenum = -1
            return
        Config.namenum = Config.namenum + 1
        if Config.namenum > 9:
            return "c%d" % Config.namenum
        else:
            return "c0%d" % Config.namenum

    def get_profile(self):
        """Get our profile"""
        return(self.profile)

    def set_profile(self, profile, force=False):
        """Set our profile (which usually means change it)"""
        options = self.options_get()
        if not force and options and options.profile and profile == 'default':
            dbg('overriding default profile to %s' % options.profile)
            profile = options.profile
        dbg('Config::set_profile: Changing profile to %s' % profile)
        self.profile = profile
        if not self.base.profiles.has_key(profile):
            dbg('Config::set_profile: %s does not exist, creating' % profile)
            self.base.profiles[profile] = copy(DEFAULTS['profiles']['default'])

    def add_profile(self, profile):
        """Add a new profile"""
        return(self.base.add_profile(profile))

    def del_profile(self, profile):
        """Delete a profile"""
        if profile == self.profile:
            # FIXME: We should solve this problem by updating terminals when we
            # remove a profile
            err('Config::del_profile: Deleting in-use profile %s.' % profile)
            self.set_profile('default')
        if self.base.profiles.has_key(profile):
            del(self.base.profiles[profile])
        options = self.options_get()
        if options and options.profile == profile:
            options.profile = None
            self.options_set(options)

    def rename_profile(self, profile, newname):
        """Rename a profile"""
        if self.base.profiles.has_key(profile):
            self.base.profiles[newname] = self.base.profiles[profile]
            del(self.base.profiles[profile])
            if profile == self.profile:
                self.profile = newname

    def list_profiles(self):
        """List all configured profiles"""
        return(self.base.profiles.keys())

    def add_layout(self, name, layout):
        """Add a new layout"""
        return(self.base.add_layout(name, layout))

    def replace_layout(self, name, layout):
        """Replace an existing layout"""
        return(self.base.replace_layout(name, layout))

    def del_layout(self, layout):
        """Delete a layout"""
        if self.base.layouts.has_key(layout):
            del(self.base.layouts[layout])

    def rename_layout(self, layout, newname):
        """Rename a layout"""
        if self.base.layouts.has_key(layout):
            self.base.layouts[newname] = self.base.layouts[layout]
            del(self.base.layouts[layout])

    def list_layouts(self):
        """List all configured layouts"""
        return(self.base.layouts.keys())

    def connect_gsetting_callbacks(self):
        """Get system settings and create callbacks for changes"""
        dbg("GSetting connects for system changes")
        # Have to preserve these to self, or callbacks don't happen
        self.gsettings_interface=Gio.Settings.new('org.gnome.desktop.interface')
        self.gsettings_interface.connect("changed::font-name", self.on_gsettings_change_event)
        self.gsettings_interface.connect("changed::monospace-font-name", self.on_gsettings_change_event)
        self.gsettings_wm=Gio.Settings.new('org.gnome.desktop.wm.preferences')
        self.gsettings_wm.connect("changed::focus-mode", self.on_gsettings_change_event)

    def get_system_prop_font(self):
        """Look up the system font"""
        if self.system_prop_font is not None:
            return(self.system_prop_font)
        elif 'org.gnome.desktop.interface' not in Gio.Settings.list_schemas():
            return
        else:
            gsettings=Gio.Settings.new('org.gnome.desktop.interface')
            value = gsettings.get_value('font-name')
            if value:
                self.system_prop_font = value.get_string()
            else:
                self.system_prop_font = "Sans 11"
            return(self.system_prop_font)

    def get_system_mono_font(self):
        """Look up the system font"""
        if self.system_mono_font is not None:
            return(self.system_mono_font)
        elif 'org.gnome.desktop.interface' not in Gio.Settings.list_schemas():
            return
        else:
            gsettings=Gio.Settings.new('org.gnome.desktop.interface')
            value = gsettings.get_value('monospace-font-name')
            if value:
                self.system_mono_font = value.get_string()
            else:
                self.system_mono_font = "Mono 13"
            return(self.system_mono_font)

    def get_system_focus(self):
        """Look up the system focus setting"""
        if self.system_focus is not None:
            return(self.system_focus)
        elif 'org.gnome.desktop.interface' not in Gio.Settings.list_schemas():
            return
        else:
            gsettings=Gio.Settings.new('org.gnome.desktop.wm.preferences')
            value = gsettings.get_value('focus-mode')
            if value:
                self.system_focus = value.get_string()
            return(self.system_focus)

    def on_gsettings_change_event(self, settings, key):
        """Handle a gsetting change event"""
        dbg('GSetting change event received. Invalidating caches')
        self.system_focus = None
        self.system_font = None
        self.system_mono_font = None
        # Need to trigger a reconfigure to change active terminals immediately
        if "Terminator" not in globals():
            from terminator import Terminator
        Terminator().reconfigure()

    def save(self):
        """Cause ConfigBase to save our config to file"""
        return(self.base.save())

    def set_nosave(self, val=True):
        """No file writes if set to True"""
        self.base._nosave = val
        dbg('~set: NOSAVE is now: %s' % val)

    # FIXME do we need all these forwarders? Why?
    def commit(self, who, key, value):
        """Update config"""
        if not who:
            dbg('~DISCARD SET %s to %s. Unknown who.' % (key, value))
            return
        self.base.commit_layout_change(who, key, value)

    def options_set(self, options):
        """Set the command line options"""
        self.base.command_line_options = options

    def options_get(self):
        """Get the command line options"""
        return(self.base.command_line_options)

    def plugin_get(self, pluginname, key, default=None):
        """Get a plugin config value, if doesn't exist
            return default if specified
        """
        return(self.base.get_item(key, plugin=pluginname, default=default))

    def plugin_set(self, pluginname, key, value):
        """Set a plugin config value"""
        return(self.base.set_item(key, value, plugin=pluginname))

    def plugin_get_config(self, plugin):
        """Return a whole config tree for a given plugin"""
        return(self.base.get_plugin(plugin))

    def plugin_set_config(self, plugin, tree):
        """Set a whole config tree for a given plugin"""
        return(self.base.set_plugin(plugin, tree))

    def plugin_del_config(self, plugin):
        """Delete a whole config tree for a given plugin"""
        return(self.base.del_plugin(plugin))

    def layout_get_config(self, layout, key=None):
        """Return a layout"""
        return(self.base.get_layout(layout, key))

    def layout_set_config(self, layout, tree):
        """Set a layout"""
        return(self.base.set_layout(layout, tree))

    def get_defstub(self):
        """Return customized layout for new terminals"""
        return self.base.get_defstub()

    def get_term_config(self, parent, terminal):
        """Prepare new terminal presets. Either clone or copy defaults"""
        if not terminal:
            return self.get_defstub()
        if not self.base.global_config['always_split_with_profile']:
            r = self.get_defstub()
            r['_tabnext'] = terminal.get_tabnum() + 1
            return r
        cfg = terminal.forclone()
        cfg['parent'] = parent
        t = cfg['title']
        if t and t != '' and not t.endswith('.new'):   # mark clone
            cfg['title'] = "%s.new" % t
        t = cfg['term_command']
        if t and t[0] != '!':       # do not run command at clone. Should we?
            cfg['term_command'] = "!%s" % t
        return cfg

    def set_dirty(self, val=True):
        self.base._dirty = val

    def set_building(self, val=True):
        self.base._building = val

class ConfigBase(Borg):
    """Class to provide access to our user configuration"""
    loaded = None
    whined = None
    sections = None
    global_config = None
    profiles = None
    keybindings = None
    plugins = None
    layouts = None
    command_line_options = None
    _curlayoutname = 'default'
    _dirty = None
    _nosave = None
    _building = None

    def __init__(self):
        """Class initialiser"""

        Borg.__init__(self, self.__class__.__name__)

        self.prepare_attributes()
        import optionparse
        self.command_line_options = optionparse.options
        self.load()
        self._dirty = False
        self._nosave = False

    def prepare_attributes(self):
        """Set up our borg environment"""
        if self.loaded is None:
            self.loaded = False
        if self.whined is None:
            self.whined = False
        if self.sections is None:
            self.sections = ['global_config', 'keybindings', 'profiles',
                             'layouts', 'plugins']
        if self.global_config is None:
            self.global_config = copy(DEFAULTS['global_config'])
        if self.profiles is None:
            self.profiles = {}
            self.profiles['default'] = copy(DEFAULTS['profiles']['default'])
        if self.keybindings is None:
            self.keybindings = copy(DEFAULTS['keybindings'])
        if self.plugins is None:
            self.plugins = {}
        if self.layouts is None:
            self.layouts = {}
            for layout in DEFAULTS['layouts']:
                self.layouts[layout] = copy(DEFAULTS['layouts'][layout])

    # XXX prefseditor Cancel feature preparation
    def get_undo_tree(self):
        r = {}
        for k in self.sections:
            r[k] = getattr(self, k)
        return r

    # FIXME this all configspec thing needs to be purged off. No mere user
    # run terminal under terminal to get a chance to read what this 'validator'
    # whines about. Here already is DEFAULTS dict to get sane value from if the
    # conf file lacks a key. An user who can do vim ~/.config/terminator/config
    # will know what to do if she'd do a typo there. Mortals have prefseditor.
    # This mess will stay for a while due to plugins and time. (ohir)
    def defaults_to_configspec(self):
        """Convert our tree of default values into a ConfigObj validation
        specification"""
        configspecdata = {}

        keymap = {
                'int': 'integer',
                'str': 'string',
                'bool': 'boolean',
                }

        section = {}
        for key in DEFAULTS['global_config']:
            keytype = DEFAULTS['global_config'][key].__class__.__name__
            value = DEFAULTS['global_config'][key]
            if keytype in keymap:
                keytype = keymap[keytype]
            elif keytype == 'list':
                value = 'list(%s)' % ','.join(value)

            keytype = '%s(default=%s)' % (keytype, value)

            if key == 'custom_url_handler':
                keytype = 'string(default="")'

            section[key] = keytype
        configspecdata['global_config'] = section

        section = {}
        for key in DEFAULTS['keybindings']:
            value = DEFAULTS['keybindings'][key]
            if value is None or value == '':
                continue
            section[key] = 'string(default=%s)' % value
        configspecdata['keybindings'] = section

        section = {}
        for key in DEFAULTS['profiles']['default']:
            keytype = DEFAULTS['profiles']['default'][key].__class__.__name__
            value = DEFAULTS['profiles']['default'][key]
            if keytype in keymap:
                keytype = keymap[keytype]
            elif keytype == 'list':
                value = 'list(%s)' % ','.join(value)
            if keytype == 'string':
                value = '"%s"' % value

            keytype = '%s(default=%s)' % (keytype, value)

            section[key] = keytype
        configspecdata['profiles'] = {}
        configspecdata['profiles']['__many__'] = section

        section = {}
        section['type'] = 'string'
        section['parent'] = 'string'
        section['profile'] = 'string(default=default)'
        section['position'] = 'string(default="")'
        #section['size'] = 'list(default=list(-1,-1))'
        #section['size'] = 'list'
        configspecdata['layouts'] = {}
        configspecdata['layouts']['__many__'] = {}
        configspecdata['layouts']['__many__']['__many__'] = section

        configspecdata['plugins'] = {}

        configspec = ConfigObj(configspecdata)
        if DEBUG == True:
            configspec.write(open('/tmp/terminator_configspec_debug.txt', 'w'))
        return(configspec)

    def load(self):
        """Load configuration data from our various sources"""
        if self.loaded is True:
            dbg('ConfigBase::load: config already loaded')
            return

        if self.command_line_options:
            if not self.command_line_options.config:
                self.command_line_options.config = os.path.join(get_config_dir(), 'config92')
            filename = self.command_line_options.config
        else:
            #filename = os.path.join(get_config_dir(), 'config')
            filename = os.path.join(get_config_dir(), 'config92')

        dbg('looking for config file: %s' % filename)
        try:
            configfile = open(filename, 'r')
        except Exception, ex:
            if not self.whined:
                err('ConfigBase::load: Unable to open %s (%s)' % (filename, ex))
                self.whined = True
            return
        # If we have successfully loaded a config, allow future whining
        self.whined = False

        try:
            configspec = self.defaults_to_configspec()
            parser = ConfigObj(configfile, configspec=configspec)
            validator = Validator()
            result = parser.validate(validator, preserve_errors=True)
        except Exception, ex:
            err('Unable to load configuration: %s' % ex)
            return

        if result != True:
            err('ConfigBase::load: config format is not valid')
            for (section_list, key, _other) in flatten_errors(parser, result):
                if key is not None:
                    err('[%s]: %s is invalid' % (','.join(section_list), key))
                else:
                    err('[%s] missing' % ','.join(section_list))
        else:
            dbg('config validated successfully')

        for section_name in self.sections:
            dbg('ConfigBase::load: Processing section: %s' % section_name)
            section = getattr(self, section_name)
            if section_name == 'profiles':
                for profile in parser[section_name]:
                    dbg('ConfigBase::load: Processing profile: %s' % profile)
                    if not section.has_key(section_name):
                        # FIXME: Should this be outside the loop?
                        section[profile] = copy(DEFAULTS['profiles']['default'])
                    section[profile].update(parser[section_name][profile])
            elif section_name == 'plugins':
                if not parser.has_key(section_name):
                    continue
                for part in parser[section_name]:
                    dbg('ConfigBase::load: Processing %s: %s' % (section_name,
                                                                 part))
                    section[part] = parser[section_name][part]
            elif section_name == 'layouts':
                for layout in parser[section_name]:
                    dbg('ConfigBase::load: Processing %s: %s' % (section_name,
                                                                 layout))
                    if layout == 'default' and \
                       parser[section_name][layout] == {}:
                           continue
                    section[layout] = parser[section_name][layout]
            elif section_name == 'keybindings':
                if not parser.has_key(section_name):
                    continue
                for part in parser[section_name]:
                    dbg('ConfigBase::load: Processing %s: %s' % (section_name,
                                                                 part))
                    if parser[section_name][part] == 'None':
                        section[part] = None
                    else:
                        section[part] = parser[section_name][part]
            else:
                try:
                    section.update(parser[section_name])
                except KeyError, ex:
                    dbg('ConfigBase::load: skipping missing section %s' %
                            section_name)

        self.loaded = True

    def reload(self):
        """Force a reload of the base config"""
        self.loaded = False
        self.load()

    # FIXED we can write all changes for ourselves. No session manager needed.
    # With SM it ultimateliy also ends with almost immediate disk write either
    # to gconf database or straight to the separate file in a SM cache. (ohir)
    def save(self, force=False):
        """Save the config to a file"""
        if self._nosave:
            dbg('~ConfigBase::save: WRITE SUPRESSED')
            return(True)
        elif force:
            dbg('~ConfigBase::save: WRITE FORCED')
            pass
        elif not self._dirty:
            dbg('~ConfigBase::save: CONFIG CLEAN')
            return(True)

        dbg('~ConfigBase::save: WRITE CONFIG')
        self._dirty = False


        # FIXME this craziness must be purged asap.
        parser = ConfigObj()
        parser.indent_type = '  '

        for section_name in ['global_config', 'keybindings']:
            dbg('ConfigBase::save: Processing section: %s' % section_name)
            section = getattr(self, section_name)
            parser[section_name] = dict_diff(DEFAULTS[section_name], section)

        parser['profiles'] = {}
        for profile in self.profiles:
            dbg('ConfigBase::save: Processing profile: %s' % profile)
            parser['profiles'][profile] = dict_diff(
                    DEFAULTS['profiles']['default'], self.profiles[profile])

        parser['layouts'] = {}
        for layout in self.layouts:
            dbg('ConfigBase::save: Processing layout: %s' % layout)
            parser['layouts'][layout] = self.cleancfg(self.layouts[layout])

        parser['plugins'] = {}
        for plugin in self.plugins:
            dbg('ConfigBase::save: Processing plugin: %s' % plugin)
            parser['plugins'][plugin] = self.plugins[plugin]

        config_dir = get_config_dir()
        if not os.path.isdir(config_dir):
            os.makedirs(config_dir)
        try:
            parser.write(open(self.command_line_options.config, 'w'))
        except Exception, ex:
            err('ConfigBase::save: Unable to save config: %s' % ex)

        self._dirty = False

    def cleancfg(self, indict):
        """Make saved config tidy. Layout sections so far."""
        oudict = {}
        paned = indict.has_key('_inPaned') and indict['_inPaned']
        for key,value in indict.iteritems():
            if isinstance(value, dict):
                oudict[key] = self.cleancfg(value)
            elif key == 'parent':
                oudict[key] = value
            elif key == 'caption' and paned:
                pass
            elif not value or value == 'default':
                pass
            elif key[0] == '_':
                pass
            else:
                oudict[key] = value
        return oudict

    #def layout_item_changed(self, who, key, value):
    def commit_layout_change(self, who, key, value):
        """Update, set dict as dirty"""
        if not self._curlayoutname:
            err('LAYOUT NOT SET')
            return
        dbg('~CHANGE for %s. SET %s to %s [layout:%s]' % (who, key, value, self._curlayoutname))
        self.layouts[self._curlayoutname][who][key] = value
        self._dirty = True

    def get_item(self, key, profile='default', plugin=None, default=None):
        """Look up a configuration item"""
        if not self.profiles.has_key(profile):
            # Hitting this generally implies a bug
            profile = 'default'

        if self.global_config.has_key(key):
            dbg('ConfigBase::get_item: %s found in globals: %s' %
                    (key, self.global_config[key]))
            return(self.global_config[key])
        elif self.profiles[profile].has_key(key):
            dbg('ConfigBase::get_item: %s found in profile %s: %s' % (
                    key, profile, self.profiles[profile][key]))
            return(self.profiles[profile][key])
        elif key == 'keybindings':
            return(self.keybindings)
        elif plugin and plugin in self.plugins and key in self.plugins[plugin]:
            dbg('ConfigBase::get_item: %s found in plugin %s: %s' % (
                    key, plugin, self.plugins[plugin][key]))
            return(self.plugins[plugin][key])
        elif default:
            return default
        else:
            raise KeyError('ConfigBase::get_item: unknown key %s' % key)

    def set_item(self, key, value, profile='default', plugin=None):
        """Set a configuration item"""
        dbg('ConfigBase::set_item: Setting %s=%s (profile=%s, plugin=%s)' %
                (key, value, profile, plugin))

        if self.global_config.has_key(key):
            self.global_config[key] = value
        elif self.profiles[profile].has_key(key):
            self.profiles[profile][key] = value
        elif key == 'keybindings':
            self.keybindings = value
        elif plugin is not None:
            if not self.plugins.has_key(plugin):
                self.plugins[plugin] = {}
            self.plugins[plugin][key] = value
        else:
            raise KeyError('ConfigBase::set_item: unknown key %s' % key)

        self._dirty = True
        return(True)

    def get_plugin(self, plugin):
        """Return a whole tree for a plugin"""
        if self.plugins.has_key(plugin):
            return(self.plugins[plugin])

    def set_plugin(self, plugin, tree):
        """Set a whole tree for a plugin"""
        self.plugins[plugin] = tree
        self._dirty = True

    def del_plugin(self, plugin):
        """Delete a whole tree for a plugin"""
        if plugin in self.plugins:
            del self.plugins[plugin]
            self._dirty = True

    def add_profile(self, profile):
        """Add a new profile"""
        if profile in self.profiles:
            return(False)
        self.profiles[profile] = copy(DEFAULTS['profiles']['default'])
        self._dirty = True
        return(True)

    def add_layout(self, name, layout):
        """Add a new layout"""
        if name in self.layouts:
            return(False)
        self.layouts[name] = layout
        self._dirty = True
        return(True)

    def replace_layout(self, name, layout):
        """Replaces a layout with the given name"""
        if not name in self.layouts:
            return(False)
        self.layouts[name] = layout
        self._dirty = True
        return(True)

    def get_layout(self, layout, key=None):
        """Return a layout"""
        if self.layouts.has_key(layout):
            if key:
                if self.layouts[layout].has_key(key):
                    return self.layouts[layout][key]
                else:
                    err('layout key does not exist: %s[%s]' % (layout, key))
                    return None
            else:
                return(self.layouts[layout])
        else:
            err('layout does not exist: %s' % layout)

    def set_layout(self, layout, tree):
        """Set a layout"""
        self.layouts[layout] = tree
        self._dirty = True

    # XXX better this way. Otherwise we might make a 3
    # or 4 chained calls just to pass cwd to config.
    def set_current_layoutname(self, key):
        """Set a layout"""
        self._curlayoutname = key

    def get_current_layoutname(self):
        """Set a layout"""
        return self._curlayoutname

    def get_defstub(self):
        r = {}
        cfgdef = {}
        defdef = copy(DEFAULTS['layouts']['default']['NewT'])
        if self.layouts[self._curlayoutname].has_key('NewT'):
            cfgdef = self.layouts[self._curlayoutname]['NewT']

        for key, value in defdef.iteritems():
            if cfgdef.has_key(key):
                r[key] = cfgdef[key]
            else:
                r[key] = value
        return r


