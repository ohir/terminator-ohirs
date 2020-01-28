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
from borg import Borg
from util import dbg, err, DEBUG, get_config_dir, dict_diff
from oconf import fromfile, tofile, DEFAULTS
#import pout
#pout.inject()
from gi.repository import Gio

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
    cfgdict = None
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
        if self.cfgdict is None:
            self.cfgdict = fromfile()
        ## keep this voodoo until bigger refactoring
        if self.global_config is None:
            self.global_config = self.cfgdict['global_config']
        if self.profiles is None:
            self.profiles = self.cfgdict['profiles']
        if self.keybindings is None:
            self.keybindings = self.cfgdict['keybindings']
        if self.plugins is None:
            self.plugins = {}
        if self.layouts is None:
            self.layouts = self.cfgdict['layouts']

    # XXX prefseditor Cancel feature preparation
    def get_undo_tree(self):
        r = {}
        for k in self.sections:
            r[k] = getattr(self, k)
        return r

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

        # we just defaults now in oconf
        self.loaded = True
        return


    def reload(self):
        """Force a reload of the base config"""
        self.loaded = False
        self.load()

    # FIXED we can write all changes for ourselves. No session manager needed.
    # With SM it ultimateliy also ends with almost immediate disk write either
    # to gconf database or straight to the separate file in a SM cache. (ohir)
    def save(self, force=False):
        return(True)
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


