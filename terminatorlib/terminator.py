#!/usr/bin/env python2
# Terminator by Chris Jones <cmsj@tenshu.net>
# GPL v2 only
"""terminator.py - class for the master Terminator singleton"""
"""Refactored for Terminator2 by Ohir Ripe <ohir@fairbe.org>"""

import copy
import os
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import Gtk, Gdk, Vte, GdkX11
from gi.repository.GLib import GError

import borg
from borg import Borg
from config import Config
from keybindings import Keybindings
from util import dbg, err, enumerate_descendants
from factory import Factory
from cwd import get_pid_cwd
from version import APP_NAME, APP_VERSION
#import pout
#pout.inject()

def eventkey2gdkevent(eventkey):  # FIXME FOR GTK3: is there a simpler way of casting from specific EventKey to generic (union) GdkEvent?
    gdkevent = Gdk.Event.new(eventkey.type)
    gdkevent.key.window = eventkey.window
    gdkevent.key.send_event = eventkey.send_event
    gdkevent.key.time = eventkey.time
    gdkevent.key.state = eventkey.state
    gdkevent.key.keyval = eventkey.keyval
    gdkevent.key.length = eventkey.length
    gdkevent.key.string = eventkey.string
    gdkevent.key.hardware_keycode = eventkey.hardware_keycode
    gdkevent.key.group = eventkey.group
    gdkevent.key.is_modifier = eventkey.is_modifier
    return gdkevent

class Terminator(Borg):
    """master object for the application"""

    windows = None
    launcher_windows = None
    windowtitle = None
    terminals = None
    groups = None
    config = None
    keybindings = None
    style_providers = None
    last_focused_term = None

    origcwd = None
    dbus_path = None
    dbus_name = None
    pid_cwd = None
    gnome_client = None
    debug_address = None
    ibus_running = None

    _layout_changed = None
    doing_quit = None
    doing_layout = None
    doing_prefs = False
    layoutname = None
    last_active_window = None
    prelayout_windows = None

    groupsend = None
    groupsend_type = {'all':0, 'group':1, 'off':2}

    cur_gtk_theme_name = None
    gtk_settings = None

    def __init__(self):
        """Class initialiser"""

        Borg.__init__(self, self.__class__.__name__)
        self.prepare_attributes()

    def prepare_attributes(self):
        """Initialise anything that isn't already"""

        if not self.windows:
            self.windows = []
        if not self.launcher_windows:
            self.launcher_windows = []
        if not self.terminals:
            self.terminals = []
        if not self.groups:
            self.groups = []
        if not self.config:
            self.config = Config()
        if self.groupsend == None:
            self.groupsend = self.groupsend_type[self.config['broadcast_default']]
        if not self.keybindings:
            self.keybindings = Keybindings()
            self.keybindings.configure(self.config['keybindings'])
        if not self.style_providers:
            self.style_providers = []
        if not self.doing_layout:
            self.doing_layout = False
        if not self.pid_cwd:
            self.pid_cwd = get_pid_cwd()
        if self.gnome_client is None:
            self.attempt_gnome_client()
        self.connect_signals()

    def connect_signals(self):
        """Connect all the gtk signals"""
        self.gtk_settings=Gtk.Settings().get_default()
        self.gtk_settings.connect('notify::gtk-theme-name', self.on_gtk_theme_name_notify)
        self.cur_gtk_theme_name = self.gtk_settings.get_property('gtk-theme-name')

    def set_origcwd(self, cwd):
        """Store the original cwd our process inherits"""
        if cwd == '/':
            cwd = os.path.expanduser('~')
            os.chdir(cwd)
        self.origcwd = cwd

    def set_dbus_data(self, dbus_service):
        """Store the DBus bus details, if they are available"""
        if dbus_service:
            self.dbus_name = dbus_service.bus_name.get_name()
            self.dbus_path = dbus_service.bus_path

    # FIXME Gnome only. Others use XSMP.
    def attempt_gnome_client(self):
        """Attempt to find a GNOME Session to register with"""
        try:
            from gi.repository import Gnome
            self.gnome_program = Gnome.init(APP_NAME, APP_VERSION)  # VERIFY FOR GTK3
            self.gnome_client = Gnome.Ui.master_client()  # VERIFY FOR GTK3
            self.gnome_client.connect_to_session_manager()
            self.gnome_client.connect('save-yourself', self.save_yourself)
            self.gnome_client.connect('die', self.die)
            dbg('GNOME session support enabled and registered')
        except (ImportError, AttributeError):
            self.gnome_client = False
            dbg('GNOME session support not available')

    def die(self, *args):
        """Die at the hands of the session manager"""
        dbg('session manager asked us to die')
        # FIXME: Test this
        self.config.save()
        self.config.set_nosave(True)
        for w in self.windows:
            w.close()
            # last w will call Gtk.main_quit()
        return True

    def get_windows(self):
        """Return a list of windows"""
        return self.windows

    def register_window(self, window):
        """Register a new window widget"""
        if window not in self.windows:
            dbg('Terminator::register_window: registering %s:%s' % (id(window),
                type(window)))
            self.windows.append(window)

    def deregister_window(self, window):
        """de-register a window widget"""
        dbg('Terminator::deregister_window: de-registering %s:%s' %
                (id(window), type(window)))
        if window in self.windows:
            self.windows.remove(window)
        else:
            err('%s is not in registered window list' % window)

        if len(self.windows) == 0:
            # We have no windows left, we should exit
            dbg('~No windows remain, quitting')
            Gtk.main_quit()
        else:
            self._layout_changed = True

    def register_launcher_window(self, window):
        """Register a new launcher window widget"""
        if window not in self.launcher_windows:
            dbg('Terminator::register_launcher_window: registering %s:%s' % (id(window),
                type(window)))
            self.launcher_windows.append(window)

    def deregister_launcher_window(self, window):
        """de-register a launcher window widget"""
        dbg('Terminator::deregister_launcher_window: de-registering %s:%s' %
                (id(window), type(window)))
        if window in self.launcher_windows:
            self.launcher_windows.remove(window)
        else:
            err('%s is not in registered window list' % window)

        if len(self.launcher_windows) == 0 and len(self.windows) == 0:
            # We have no windows left, we should exit
            dbg('no windows remain, quitting')
            Gtk.main_quit()

    def register_terminal(self, terminal):
        """Register a new terminal widget"""
        if terminal not in self.terminals:
            dbg('Terminator::register_terminal: registering %s:%s' %
                    (id(terminal), type(terminal)))
            self.terminals.append(terminal)

    def deregister_terminal(self, terminal):
        """De-register a terminal widget"""
        dbg('Terminator::deregister_terminal: de-registering %s:%s' %
                (id(terminal), type(terminal)))
        self.terminals.remove(terminal)

        if len(self.terminals) == 0:
            dbg('no terminals remain, destroying all windows')
            for window in self.windows:
                window.destroy()
        else:
            self._layout_changed = True
            dbg('Terminator::deregister_terminal: %d terminals remain' % len(self.terminals))

    def find_terminal_by_uuid(self, uuid):
        """Search our terminals for one matching the supplied UUID"""
        dbg('searching self.terminals for: %s' % uuid)
        for terminal in self.terminals:
            dbg('checking: %s (%s)' % (terminal.uuid.urn, terminal))
            if terminal.uuid.urn == uuid:
                return terminal
        return None

    def find_window_by_uuid(self, uuid):
        """Search our terminals for one matching the supplied UUID"""
        dbg('searching self.terminals for: %s' % uuid)
        for window in self.windows:
            dbg('checking: %s (%s)' % (window.uuid.urn, window))
            if window.uuid.urn == uuid:
                return window
        return None

    def new_window(self, cwd=None, profile=None):
        """Create a window with a Terminal in it"""
        maker = Factory()
        window = maker.make('Window')
        terminal = maker.make('Terminal')
        if cwd:
            terminal.set_cwd(cwd)
        # new window gets terminal with defaults
        terminal.apply_new(self.config.get_defstub())
        window.add(terminal)
        window.show(True)
        terminal.spawn_child()
        if len(self.windows) > 1:
            dbg('~MORE WINDOWS')
        else:
            dbg('~FIX NOCONFIg HEISENBUG')
            terminal.describe_layout('n',{'_': 1})
        return(window, terminal)

    # FIXME redo all this in paralel with new config. Layout can be created
    # from the flat structure.
    def create_layout(self, layoutname):
        """Create all the parts necessary to satisfy the specified layout"""
        layout = None
        objects = {}

        self.doing_layout = True
        self.last_active_window = None
        self.prelayout_windows = self.windows[:]

        #layout = copy.deepcopy(self.config.layout_get_config(layoutname))
        layout = copy.deepcopy(self.config.layout_get_config('default'))
        #layout = self.config.layout_get_config('default')
        if not layout:
            # User specified a non-existent layout. default to one Terminal
            err('layout %s not defined' % layout)
            self.new_window()
            return

        # Wind the flat objects into a hierarchy
        hierarchy = {}
        count = 0
        # Loop over the layout until we have consumed it, or hit 1000 loops.
        # This is a stupid artificial limit, but it's safe.
        while len(layout) > 0 and count < 1000:
            count = count + 1
            if count == 1000:
                err('hit maximum loop boundary. THIS IS VERY LIKELY A BUG')
                #pout.v(layout)

            for obj in layout.keys():
                # all other top-level keys need to be deleted
                if layout[obj]['type'] == 'Defstub':
                    del(layout[obj])
                elif layout[obj]['type'].lower() == 'window':
                    hierarchy[obj] = {}
                    hierarchy[obj]['type'] = 'Window'
                    hierarchy[obj]['children'] = {}

                    # Copy any additional keys
                    for objkey in layout[obj].keys():
                        if layout[obj][objkey] != '' and not hierarchy[obj].has_key(objkey):
                            hierarchy[obj][objkey] = layout[obj][objkey]

                    objects[obj] = hierarchy[obj]
                    del(layout[obj])
                else:
                    # Now examine children to see if their parents exist yet
                    if not layout[obj].has_key('parent'):
                        err('Invalid object: %s' % obj)
                        del(layout[obj])
                        continue
                    if objects.has_key(layout[obj]['parent']):
                        # Our parent has been created, add ourselves
                        childobj = {}
                        childobj['type'] = layout[obj]['type']
                        childobj['children'] = {}

                        # Copy over any additional object keys
                        for objkey in layout[obj].keys():
                            if not childobj.has_key(objkey):
                                childobj[objkey] = layout[obj][objkey]

                        objects[layout[obj]['parent']]['children'][obj] = childobj
                        objects[obj] = childobj
                        del(layout[obj])
        layout = hierarchy

        for windef in layout:
            if layout[windef]['type'] != 'Window':
                err('invalid layout format. %s' % layout)
                raise(ValueError)
            dbg('Creating a window')
            window, terminal = self.new_window()
            if layout[windef].has_key('position'):
                parts = layout[windef]['position']
                if len(parts) == 2:
                    window.move(int(parts[0]), int(parts[1]))
            if layout[windef].has_key('size'):
                parts = layout[windef]['size']
                winx = int(parts[0])
                winy = int(parts[1])
                if winx > 1 and winy > 1:
                    window.resize(winx, winy)
            if layout[windef].has_key('title'):
                window.title.force_title(layout[windef]['title'])
            if layout[windef].has_key('maximised'):
                if layout[windef]['maximised'] == 'True':
                    window.ismaximised = True
                else:
                    window.ismaximised = False
                window.set_maximised(window.ismaximised)
            if layout[windef].has_key('fullscreen'):
                if layout[windef]['fullscreen'] == 'True':
                    window.isfullscreen = True
                else:
                    window.isfullscreen = False
                window.set_fullscreen(window.isfullscreen)
            window.config_section = windef
            window.create_layout(layout[windef])

        self.layoutname = layoutname
        self.config.base.set_current_layoutname(layoutname)

    def layout_done(self):
        """Layout operations have finished, record that fact"""
        self.doing_layout = False
        maker = Factory()

        window_last_active_term_mapping = {}
        for window in self.windows:
            if window.is_child_notebook():
                source = window.get_toplevel().get_children()[0]
            else:
                source = window
            window_last_active_term_mapping[window] = copy.copy(source.last_active_term)

        for terminal in self.terminals:
            if not terminal.pid:
                terminal.spawn_child()

        for window in self.windows:
            if window.is_child_notebook():
                # For windows with a notebook
                notebook = window.get_toplevel().get_children()[0]
                # Cycle through pages by number
                for page in xrange(0, notebook.get_n_pages()):
                    # Try and get the entry in the previously saved mapping
                    mapping = window_last_active_term_mapping[window]
                    page_last_active_term = mapping.get(notebook.get_nth_page(page),  None)
                    if page_last_active_term is None:
                        # Couldn't find entry, so we find the first child of type Terminal
                        children = notebook.get_nth_page(page).get_children()
                        for page_last_active_term in children:
                            if maker.isinstance(page_last_active_term, 'Terminal'):
                                page_last_active_term = page_last_active_term.uuid
                                break
                        else:
                            err('Should never reach here!')
                            page_last_active_term = None
                    if page_last_active_term is None:
                        # Bail on this tab as we're having no luck here, continue with the next
                        continue
                    # Set the notebook entry, then ensure Terminal is visible and focussed
                    urn = page_last_active_term.urn
                    notebook.last_active_term[notebook.get_nth_page(page)] = page_last_active_term
                    if urn:
                        term = self.find_terminal_by_uuid(urn)
                        if term:
                            term.ensure_visible_and_focussed()
            else:
                # For windows without a notebook ensure Terminal is visible and focussed
                if window_last_active_term_mapping[window]:
                    term = self.find_terminal_by_uuid(window_last_active_term_mapping[window].urn)
                    term.ensure_visible_and_focussed()

        # Build list of new windows using prelayout list
        new_win_list = []
        for window in self.windows:
            if window not in self.prelayout_windows:
                new_win_list.append(window)

        # Make sure all new windows get bumped to the top
        for window in new_win_list:
            window.show()
            window.grab_focus()
            try:
                t = GdkX11.x11_get_server_time(window.get_window())
            except (TypeError, AttributeError):
                t = 0
            window.get_window().focus(t)

        # Awful workaround to be sure that the last focused window is actually the one focused.
        # Don't ask, don't tell policy on this. Even this is not 100%
        if self.last_active_window:
            window = self.find_window_by_uuid(self.last_active_window.urn)
            count = 0
            while count < 1000 and Gtk.events_pending():
                count += 1
                Gtk.main_iteration_do(False)
                window.show()
                window.grab_focus()
                try:
                    t = GdkX11.x11_get_server_time(window.get_window())
                except (TypeError, AttributeError):
                    t = 0
                window.get_window().focus(t)

        self.prelayout_windows = None
        dbg('~on_layout_done: ENABLE SAVES')
        self.config.set_dirty(False)
        self.config.set_nosave(False)

    def on_gtk_theme_name_notify(self, settings, prop):
        """Reconfigure if the gtk theme name changes"""
        new_gtk_theme_name = settings.get_property(prop.name)
        if new_gtk_theme_name != self.cur_gtk_theme_name:
            self.cur_gtk_theme_name = new_gtk_theme_name
            self.reconfigure()

    def reconfigure(self):
        """Update configuration for the whole application"""

        if self.style_providers != []:
            for style_provider in self.style_providers:
                Gtk.StyleContext.remove_provider_for_screen(
                    Gdk.Screen.get_default(),
                    style_provider)
        self.style_providers = []

        # Force the window background to be transparent for newer versions of
        # GTK3. We then have to fix all the widget backgrounds because the
        # widgets theming may not render it's own background.
        css = """
            .terminator-terminal-window {
                background-color: alpha(@theme_bg_color,0); }

            .terminator-terminal-window .notebook.header,
            .terminator-terminal-window notebook header {
                background-color: @theme_bg_color; }

            .terminator-terminal-window .pane-separator {
                background-color: @theme_bg_color; }

            .terminator-terminal-window .terminator-terminal-searchbar {
                background-color: @theme_bg_color; }
            """

        # Fix several themes that put a borders, corners, or backgrounds around
        # viewports, making the titlebar look bad.
        css += """
            .terminator-terminal-window GtkViewport,
            .terminator-terminal-window viewport {
                border-width: 0px;
                border-radius: 0px;
                background-color: transparent; }
            """

        # Add per profile snippets for setting the background of the HBox
        template = """
            .terminator-profile-%s {
                background-color: alpha(%s, %s); }
            """
        profiles = self.config.base.profiles
        for profile in profiles.keys():
            if profiles[profile]['use_theme_colors']:
                # Create a dummy window/vte and realise it so it has correct
                # values to read from
                tmp_win = Gtk.Window()
                tmp_vte = Vte.Terminal()
                tmp_win.add(tmp_vte)
                tmp_win.realize()
                bgcolor = tmp_vte.get_style_context().get_background_color(Gtk.StateType.NORMAL)
                bgcolor = "#{0:02x}{1:02x}{2:02x}".format(int(bgcolor.red  * 255),
                                                          int(bgcolor.green * 255),
                                                          int(bgcolor.blue * 255))
                tmp_win.remove(tmp_vte)
                del(tmp_vte)
                del(tmp_win)
            else:
                bgcolor = Gdk.RGBA()
                bgcolor = profiles[profile]['background_color']
            if profiles[profile]['background_type'] == 'transparent':
                bgalpha = profiles[profile]['background_darkness']
            else:
                bgalpha = "1"

            munged_profile = "".join([c if c.isalnum() else "-" for c in profile])
            css += template % (munged_profile, bgcolor, bgalpha)

        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css)
        self.style_providers.append(style_provider)

        # Attempt to load some theme specific stylistic tweaks for appearances
        usr_theme_dir = os.path.expanduser('~/.local/share/themes')
        (head, _tail) = os.path.split(borg.__file__)
        app_theme_dir = os.path.join(head, 'themes')

        theme_name = self.gtk_settings.get_property('gtk-theme-name')

        theme_part_list = ['terminator.css']
        if self.config['extra_styling']:    # checkbox_style - needs adding to prefs
            theme_part_list.append('terminator_styling.css')
        for theme_part_file in theme_part_list:
            for theme_dir in [usr_theme_dir, app_theme_dir]:
                path_to_theme_specific_css = os.path.join(theme_dir,
                                                          theme_name,
                                                          'gtk-3.0/apps',
                                                          theme_part_file)
                if os.path.isfile(path_to_theme_specific_css):
                    style_provider = Gtk.CssProvider()
                    style_provider.connect('parsing-error', self.on_css_parsing_error)
                    try:
                        style_provider.load_from_path(path_to_theme_specific_css)
                    except GError:
                        # Hmmm. Should we try to provide GTK version specific files here on failure?
                        gtk_version_string = '.'.join([str(Gtk.get_major_version()),
                                                       str(Gtk.get_minor_version()),
                                                       str(Gtk.get_micro_version())])
                        err('Error(s) loading css from %s into Gtk %s' % (path_to_theme_specific_css,
                                                                          gtk_version_string))
                    self.style_providers.append(style_provider)
                    break

        # Size the GtkPaned splitter handle size.
        css = ""
        if self.config['handle_size'] in xrange(0, 21):
            css += """
                .terminator-terminal-window GtkPaned,
                .terminator-terminal-window paned {
                    -GtkPaned-handle-size: %s; }
                """ % self.config['handle_size']
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css)
        self.style_providers.append(style_provider)

        # Apply the providers, incrementing priority so they don't cancel out
        # each other
        for idx in xrange(0, len(self.style_providers)):
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(),
                self.style_providers[idx],
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION+idx)

        # Cause all the terminals to reconfigure
        for terminal in self.terminals:
            terminal.reconfigure()

        # Reparse our keybindings
        self.keybindings.configure(self.config['keybindings'])

        # Update tab position if appropriate
        maker = Factory()
        for window in self.windows:
            child = window.get_child()
            if maker.isinstance(child, 'Notebook'):
                child.configure()
        # FIXME TODO describe_layout where?

    def on_css_parsing_error(self, provider, section, error, user_data=None):
        """Report CSS parsing issues"""
        file_path = section.get_file().get_path()
        line_no = section.get_end_line() +1
        col_no = section.get_end_position() + 1
        err('%s, at line %d, column %d, of file %s' % (error.message,
                                                       line_no, col_no,
                                                       file_path))

    def create_group(self, name):
        """Create a new group"""
        if name not in self.groups:
            dbg('Terminator::create_group: registering group %s' % name)
            self.groups.append(name)

    def closegroupedterms(self, group):
        """Close all terminals in a group"""
        for terminal in self.terminals[:]:
            if terminal.group == group:
                terminal.close()

    def group_hoover(self):
        """Clean out unused groups"""

        if self.config['autoclean_groups']:
            inuse = []
            todestroy = []

            for terminal in self.terminals:
                if terminal.group:
                    if not terminal.group in inuse:
                        inuse.append(terminal.group)

            for group in self.groups:
                if not group in inuse:
                    todestroy.append(group)

            dbg('Terminator::group_hoover: %d groups, hoovering %d' %
                    (len(self.groups), len(todestroy)))
            for group in todestroy:
                self.groups.remove(group)

    def group_emit(self, terminal, group, type, event):
        """Emit to each terminal in a group"""
        dbg('Terminator::group_emit: emitting a keystroke for group %s' %
                group)
        for term in self.terminals:
            if term != terminal and term.group == group:
                term.vte.emit(type, eventkey2gdkevent(event))

    def all_emit(self, terminal, type, event):
        """Emit to all terminals"""
        for term in self.terminals:
            if term != terminal:
                term.vte.emit(type, eventkey2gdkevent(event))

    def do_enumerate(self, widget, pad):
        """Insert the number of each terminal in a group, into that terminal"""
        if pad:
            numstr = '%0'+str(len(str(len(self.terminals))))+'d'
        else:
            numstr = '%d'

        terminals = []
        for window in self.windows:
            containers, win_terminals = enumerate_descendants(window)
            terminals.extend(win_terminals)

        for term in self.get_target_terms(widget):
            idx = terminals.index(term)
            term.feed(numstr % (idx + 1))

    def get_sibling_terms(self, widget):
        termset = []
        for term in self.terminals:
            if term.group == widget.group:
                termset.append(term)
        return(termset)

    def get_target_terms(self, widget):
        """Get the terminals we should currently be broadcasting to"""
        if self.groupsend == self.groupsend_type['all']:
            return(self.terminals)
        elif self.groupsend == self.groupsend_type['group']:
            if widget.group != None:
                return(self.get_sibling_terms(widget))
        return([widget])

    # FIXME no call site spotted for this
    def get_focussed_terminal(self):
        """iterate over all the terminals to find which, if any, has focus"""
        for terminal in self.terminals:
            if terminal.has_focus():
                return(terminal)
        return(None)

    def focus_changed(self, widget):
        """We just moved focus to a new terminal"""
        for terminal in self.terminals:
            terminal.titlebar.update(widget)
        return

    # SMFIX: simple hack around session managers mess.
    # Be KISS: notify early, commit on focus_left, possibly save on focus_out.
    # Apart from power failure, session exit inevitably will fire focus-out.
    def layout_changed(self, who=None):
        if self.doing_layout or self.doing_quit:
            return
        #dbg('LAYOUT CHANGED called from %s' % who)
        self._layout_changed = True

    def notify_config(self):
        dbg('~---------------------------')
        dbg('~DESCRIBE FOR CONFIG')
        if self.doing_layout:
            dbg('~DISCARD CNF_COMMIT: doing_layout')
            return
        if self.doing_quit:
            dbg('~DISCARD CNF_COMMIT: doing_quit')
            return
        self.layout_readcurrent()
        self.config.set_dirty()
        self._layout_changed = False

    def focus_left(self, widget):
        if not widget.config_section:
            self.notify_config()
        elif self._layout_changed:
            self.notify_config()
        self.last_focused_term=widget

    def describe_layout(self):
        """Describe our current layout"""
        layout = {}
        layout['NewT'] = self.config.get_defstub()
        self.config.name_next(reset=True)
        for window in self.windows:
            parent = ''
            window.describe_layout(parent, layout)
        return(layout)

    def relayout(self, tree=None):
        """Recursively call relayout on children capable of this"""
        if tree:
            layout = tree
        else:
            layout = self.config.layout_get_config(self.layoutname)

        #with pout.tofile('./relayout.pout.txt'):
        #    pout.v(layout)

        for child in self.windows:
            if hasattr(child, 'relayout'):
                dbg('NoErr top.relayout for %s' % child)
                child.relayout(layout)
            else:
                dbg('NoErr SKIP top.relayout for %s' % child)

    def layout_readcurrent(self):
        """Describe current layout"""
        self.curr_layout = self.describe_layout()
        self.config.layout_set_config(self.layoutname, self.curr_layout)
        self._layout_changed = False
        return

    def save_state(self):
        if self.doing_layout or self.doing_quit:
            dbg('~DISCARD SAVE_STATE at layout or quit phase.')
            return
        if self._layout_changed:
            self.save_yourself() # reread our state then force save
        else:
            self.config.save()   # let config decide

    def save_yourself(self, *args):
        """Refresh layout then save current state"""
        dbg("~SAVING SELF")
        self.layout_readcurrent()
        self.config.set_dirty()
        self.config.save()
        return

# vim: set expandtab ts=4 sw=4:
