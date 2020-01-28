#!/usr/bin/env python2
# -*- coding: utf8 -*-
# Terminator by Chris Jones <cmsj@tenshu.net>
# GPL v2 only
"""titlebar.py - classes necessary to provide a terminal title bar"""

from gi.repository import Gtk, Gdk
from gi.repository import GObject
from gi.repository import Pango
import random
import itertools

from version import APP_NAME
from util import dbg, uhoextract, get_home_dir
from terminator import Terminator
from editablelabel import EditableLabel
from translation import _

# pylint: disable-msg=R0904
# pylint: disable-msg=W0613
class Titlebar(Gtk.EventBox):
    """Class implementing the Titlebar widget"""

    terminator = None
    terminal = None
    config = None
    oldtitle = None
    termtext = None
    label = None
    ebox = None
    groupicon = None
    grouplabel = None
    groupentry = None
    bellicon = None
    _autotext = u''
    _tsize = u''
    _tabcapt = u''
    sizetext = u''
    titlefixed = False # True # False
    custom_title = u'' # raw
    _ctitle = u'' # output
    _ostitle = u''
    custom_caption = u''
    _tabcapt = u''
    custom_env = u''
    _custenv = u''
    hidesize = None

    __gsignals__ = {
            'clicked': (GObject.SignalFlags.RUN_LAST, None, ()),
            'edit-done': (GObject.SignalFlags.RUN_LAST, None, ()),
            'create-group': (GObject.SignalFlags.RUN_LAST, None,
                (GObject.TYPE_STRING,)),
    }

    def __init__(self, terminal):
        """Class initialiser"""
        GObject.GObject.__init__(self)

        self.terminator = Terminator()
        self.terminal = terminal
        self.config = self.terminal.config

        self.label = EditableLabel()
        self.label.connect('edit-done', self.on_edit_done)
        self.ebox = Gtk.EventBox()
        grouphbox = Gtk.HBox()
        self.grouplabel = Gtk.Label(ellipsize='end')
        self.groupicon = Gtk.Image()
        self.bellicon = Gtk.Image()
        self.bellicon.set_no_show_all(True)
        self.titlefixed = False
        self.groupentry = Gtk.Entry()
        self.groupentry.set_no_show_all(True)
        self.groupentry.connect('focus-out-event', self.groupentry_cancel)
        self.groupentry.connect('activate', self.groupentry_activate)
        self.groupentry.connect('key-press-event', self.groupentry_keypress)

        groupsend_type = self.terminator.groupsend_type
        if self.terminator.groupsend == groupsend_type['all']:
            icon_name = 'all'
        elif self.terminator.groupsend == groupsend_type['group']:
            icon_name = 'group'
        elif self.terminator.groupsend == groupsend_type['off']:
            icon_name = 'off'
        self.set_from_icon_name('_active_broadcast_%s' % icon_name,
                Gtk.IconSize.MENU)

        grouphbox.pack_start(self.groupicon, False, True, 2)
        grouphbox.pack_start(self.grouplabel, False, True, 2)
        grouphbox.pack_start(self.groupentry, False, True, 2)

        self.ebox.add(grouphbox)
        self.ebox.show_all()

        self.bellicon.set_from_icon_name('terminal-bell', Gtk.IconSize.MENU)

        viewport = Gtk.Viewport(hscroll_policy='natural')
        viewport.add(self.label)

        hbox = Gtk.HBox()
        hbox.pack_start(self.ebox, False, True, 0)
        hbox.pack_start(Gtk.VSeparator(), False, True, 0)
        hbox.pack_start(viewport, True, True, 0)
        hbox.pack_end(self.bellicon, False, False, 2)

        self.add(hbox)
        hbox.show_all()
        self.set_no_show_all(True)
        self.show()

        self.connect('button-press-event', self.on_clicked)

    def connect_icon(self, func):
        """Connect the supplied function to clicking on the group icon"""
        self.ebox.connect('button-press-event', func)

    def update_visibility(self):
        """Make the titlebar be visible or not"""
        if not self.get_desired_visibility():
            dbg('hiding titlebar')
            self.hide()
            self.label.hide()
        else:
            dbg('showing titlebar')
            self.show()
            self.label.show()

    def get_desired_visibility(self):
        """Returns True if the titlebar is supposed to be visible. False if
        not"""
        if self.editing() == True or self.terminal.group:
            dbg('implicit desired visibility')
            return(True)
        else:
            dbg('configured visibility: %s' % self.config['show_titlebar'])
            return(self.config['show_titlebar'])

    def set_from_icon_name(self, name, size = Gtk.IconSize.MENU):
        """Set an icon for the group label"""
        if not name:
            self.groupicon.hide()
            return

        self.groupicon.set_from_icon_name(APP_NAME + name, size)
        self.groupicon.show()

    def update_terminal_size(self, width, height):
        """Update the displayed terminal size"""
        self.sizetext = " %sx%s" % (width, height)
        self.update()

    def update_terminal_title(self, widget, title):
        """Update the terminal title from signal"""
        # self._tabcapt self._ctitle self._autotext self._tsize
        self._ostitle = title
        self.update()
        # Return False so we don't interrupt any chains of signal handling
        return False

    def get_custom_title(self):
        """Return custom title if it is set, otherwise return empty """
        return self.custom_title

    def set_custom_title(self, ctitle):
        """Set a custom title"""
        if ctitle:
            self.custom_title = ctitle
            self._ctitle = "%s| " % ctitle
            self.label.set_edit_base("%s" % ctitle)
        else:
            self.custom_title = ''
            self._ctitle = ''
            self.label.set_edit_base('NewTitle')
        self.update()

    def set_custom_caption(self, capt):
        """Set tabcaption"""
        if capt:
            self.custom_caption = capt
            self._tabcapt = "[%s] " % capt
        else:
            self.custom_caption = ''
            self._tabcapt = ''
        self.update()

    def set_custom_env(self, cenv):
        """Set custom environment name"""
        if cenv:
            self._custenv = "env:%s " % cenv
        else:
            self._custenv = ''
        self.update()

    def make_labeltext(self):
        title = self._ostitle
        # FIXME title fiddling assumes standard linux PS1
        # pobably we oughta get cwd ourselves
        if not title:
            title = 'user@host:/some/path'
        pathpart = self.terminal.get_cwd()
        homepart = get_home_dir()
        if pathpart.startswith(homepart):
            # Tilde is barely noticeable with system font on high dpi displays.
            #pathpart = pathpart.replace(homepart,'<HOME>',1)
            pathpart = pathpart.replace(homepart,'⁓',1)
        if self.titlefixed:
            if self._ctitle:
                self._autotext = ''
            elif self.config['title_hide_userhost']:
                    self._autotext = '@'
            else:
                # user OR remote OR R@REMOTE
                self._autotext = "%s" % uhoextract(title, smart=True)
        elif self.config['title_hide_path'] \
            and self.config['title_hide_userhost']:
            self._autotext = r'.'
        elif self.config['title_hide_path']:
            self._autotext = "%s" % uhoextract(title)
        elif self.config['title_hide_userhost']:
            self._autotext = "%s" % pathpart
        else:
            self._autotext = "%s" % title
        # forcibly show at bar even if tabs are hidden
        if self.config['title_hide_tabcaption'] \
                and not self.config['tabs_hidden']:
            self._tabcapt = ''
        elif self.custom_caption:
            self._tabcapt = "[%s] " % self.custom_caption
        else:
            self._tabcapt = ''
        if self.config['title_hide_sizetext']:
            self._tsize = ''
        else:
            self._tsize = self.sizetext

    def update(self, other=None):
        """Update our contents"""
        default_bg = False

        self.make_labeltext()
        #self.label.set_text("%s%s%s%s%s" % (self._custenv, self._tabcapt, self._ctitle, self._autotext, self._tsize), force=True)
        self.label.set_text("%s%s%s%s%s" % (self._custenv.decode('utf-8'), \
                                            self._tabcapt.decode('utf-8'), \
                                            self._ctitle.decode('utf-8'), \
                                            self._autotext.decode('utf-8'), \
                                            self._tsize), force=True)

        if (not self.config['title_use_system_font']) and self.config['title_font']:
            title_font = Pango.FontDescription(self.config['title_font'])
        else:
            title_font = Pango.FontDescription(self.config.get_system_prop_font())
        self.label.modify_font(title_font)
        self.grouplabel.modify_font(title_font)

        if other:
            term = self.terminal
            terminator = self.terminator
            if other == 'window-focus-out':
                title_fg = self.config['title_inactive_fg_color']
                title_bg = self.config['title_inactive_bg_color']
                icon = '_receive_off'
                default_bg = True
                group_fg = self.config['title_inactive_fg_color']
                group_bg = self.config['title_inactive_bg_color']
            elif term != other and term.group and term.group == other.group:
                if terminator.groupsend == terminator.groupsend_type['off']:
                    title_fg = self.config['title_inactive_fg_color']
                    title_bg = self.config['title_inactive_bg_color']
                    icon = '_receive_off'
                    default_bg = True
                else:
                    title_fg = self.config['title_receive_fg_color']
                    title_bg = self.config['title_receive_bg_color']
                    icon = '_receive_on'
                group_fg = self.config['title_receive_fg_color']
                group_bg = self.config['title_receive_bg_color']
            elif term != other and not term.group or term.group != other.group:
                if terminator.groupsend == terminator.groupsend_type['all']:
                    title_fg = self.config['title_receive_fg_color']
                    title_bg = self.config['title_receive_bg_color']
                    icon = '_receive_on'
                else:
                    title_fg = self.config['title_inactive_fg_color']
                    title_bg = self.config['title_inactive_bg_color']
                    icon = '_receive_off'
                    default_bg = True
                group_fg = self.config['title_inactive_fg_color']
                group_bg = self.config['title_inactive_bg_color']
            else:
                # We're the active terminal
                title_fg = self.config['title_transmit_fg_color']
                title_bg = self.config['title_transmit_bg_color']
                if terminator.groupsend == terminator.groupsend_type['all']:
                    icon = '_active_broadcast_all'
                elif terminator.groupsend == terminator.groupsend_type['group']:
                    icon = '_active_broadcast_group'
                else:
                    icon = '_active_broadcast_off'
                group_fg = self.config['title_transmit_fg_color']
                group_bg = self.config['title_transmit_bg_color']

            self.label.modify_fg(Gtk.StateType.NORMAL,
                    Gdk.color_parse(title_fg))
            self.grouplabel.modify_fg(Gtk.StateType.NORMAL,
                    Gdk.color_parse(group_fg))
            self.modify_bg(Gtk.StateType.NORMAL,
                    Gdk.color_parse(title_bg))
            if not self.get_desired_visibility():
                if default_bg == True:
                    color = term.get_style_context().get_background_color(Gtk.StateType.NORMAL)  # VERIFY FOR GTK3
                else:
                    color = Gdk.color_parse(title_bg)
            self.update_visibility()
            self.ebox.modify_bg(Gtk.StateType.NORMAL,
                    Gdk.color_parse(group_bg))
            self.set_from_icon_name(icon, Gtk.IconSize.MENU)

    def set_group_label(self, name):
        """Set the name of the group"""
        if name:
            self.grouplabel.set_text(name)
            self.grouplabel.show()
        else:
            self.grouplabel.set_text('')
            self.grouplabel.hide()
        self.update_visibility()

    def on_clicked(self, widget, event):
        """Handle a click on the label"""
        self.show()
        self.label.show()
        self.emit('clicked')

    def on_edit_done(self, widget):
        """Re-emit an edit-done signal from an EditableLabel"""
        if widget == self.label:
            if widget.is_custom():
                self.set_custom_title(widget.get_text())
            else:
                self.set_custom_title('')
            self.make_labeltext()
        self.emit('edit-done')

    def editing(self):
        """Determine if we're currently editing a group name or title"""
        return(self.groupentry.get_property('visible') or self.label.editing())

    def create_group(self):
        """Create a new group"""
        if self.terminal.group:
            self.groupentry.set_text(self.terminal.group)
        else:
            defaultmembers=[_('Alpha'),_('Beta'),_('Gamma'),_('Delta'),_('Epsilon'),_('Zeta'),_('Eta'),
                            _('Theta'),_('Iota'),_('Kappa'),_('Lambda'),_('Mu'),_('Nu'),_('Xi'),
                            _('Omicron'),_('Pi'),_('Rho'),_('Sigma'),_('Tau'),_('Upsilon'),_('Phi'),
                            _('Chi'),_('Psi'),_('Omega')]
            currentgroups=set(self.terminator.groups)
            for i in range(1,4):
                defaultgroups=set(map(''.join, list(itertools.product(defaultmembers,repeat=i))))
                freegroups = list(defaultgroups-currentgroups)
                if freegroups:
                    self.groupentry.set_text(random.choice(freegroups))
                    break
            else:
                self.groupentry.set_text('')
        self.groupentry.show()
        self.grouplabel.hide()
        self.groupentry.grab_focus()
        self.update_visibility()

    def groupentry_cancel(self, widget, event):
        """Hide the group name entry"""
        self.groupentry.set_text('')
        self.groupentry.hide()
        self.grouplabel.show()
        self.get_parent().grab_focus()

    def groupentry_activate(self, widget):
        """Actually cause a group to be created"""
        groupname = self.groupentry.get_text() or None
        dbg('Titlebar::groupentry_activate: creating group: %s' % groupname)
        self.groupentry_cancel(None, None)
        last_focused_term=self.terminator.last_focused_term
        if self.terminal.targets_for_new_group:
            [term.titlebar.emit('create-group', groupname) for term in self.terminal.targets_for_new_group]
            self.terminal.targets_for_new_group = None
        else:
            self.emit('create-group', groupname)
        last_focused_term.grab_focus()
        self.terminator.focus_changed(last_focused_term)

    def groupentry_keypress(self, widget, event):
        """Handle keypresses on the entry widget"""
        key = Gdk.keyval_name(event.keyval)
        if key == 'Escape':
            self.groupentry_cancel(None, None)

    def icon_bell(self):
        """A bell signal requires we display our bell icon"""
        self.bellicon.show()
        GObject.timeout_add(1000, self.icon_bell_hide)

    def icon_bell_hide(self):
        """Handle a timeout which means we now hide the bell icon"""
        self.bellicon.hide()
        return(False)

GObject.type_register(Titlebar)
