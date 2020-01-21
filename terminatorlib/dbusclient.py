#!/usr/bin/python
import dbus
#import gobject
#import sys
import os
import borg
from borg import Borg
from version import APP_NAME
from util import dbg

SMKNOWN = {
    """
    'kde' : {
        'bus'       : 'org.kde.ksmserver',
        'objpath'   : '/KSMServer',
        'interface' : 'org.kde.KSMServerInterface',
        'bus_class' : dbus.SessionBus
    },
    'default' : {
        'bus'       : 'org.freedesktop.Hal',
        'objpath'   : '/org/freedesktop/Hal/devices/computer',
        'interface' : 'org.freedesktop.Hal.Device.SystemPowerManagement',
        'bus_class' : dbus.SystemBus
    }
    """
    'gnome' : {
        'bus'       : 'org.gnome.SessionManager',
        'objpath'   : '/org/gnome/SessionManager',
        'interface' : 'org.gnome.SessionManager',
        'clientif'  : 'org.xfce.SessionManager.ClientPrivate',
    },
    'xfce' : {
        'bus'       : 'org.xfce.SessionManager',
        'objpath'   : '/org/xfce/SessionManager',
        'interface' : 'org.xfce.Session.Manager',
        'clientif'  : 'org.xfce.Session.Client',
    },
    'mock' : {
        'bus'       : 'org.mock.SessionManager',
        'objpath'   : '/org/mock/SessionManager',
        'interface' : 'org.mock.Session.Manager',
        'clientif'  : 'org.mock.Session.Client',
    }
}

#class DbusSM(Borg):
class DbusSM(Borg):
    sessionEnding = None
    sessionBus = None
    smknown = None
    ok = None

    def __init__(self):
        Borg.__init__(self, self.__class__.__name__)
        self.sessionEnding = False
        self.sessionBus = dbus.SessionBus()
        # self.smknown = SMKNOWN.keys()
        #self.smknown = [ 'mock' ]
        self.smknown = [ 'xfce' ]
        # FIXME should we check for exact w/o trying one by one?
        self.ok = self.connect()

    def connect(self):
        """Try to connect us to the session manager. Return True if succeeded"""
        ret = False
        for smcfg in self.smknown:
            try:
                self.register_with_sm(smcfg)
                dbg('~ Registered SM')
                self.init_sm_client(smcfg)
                dbg('~ Client INIT')
                ret = True
            except Exception, ex:
                 dbg('~ DBUS No session manager for %s. >>> %s' % (smcfg, ex))
            if ret:
                dbg('~ DBUS Registered with %s session manager.' % smcfg)
                break
            else:
                dbg('~ DBUS No session manager I can register with.')
        return ret

    def register_with_sm(self, smcfg):
        proxy = self.sessionBus.get_object(SMKNOWN[smcfg]['bus'], SMKNOWN[smcfg]['objpath'])
        if proxy:
            dbg('~ DBUS proxy acquired')
            #pout.v(proxy)
        sm = dbus.Interface(proxy, SMKNOWN[smcfg]['interface'])
        if proxy:
            dbg('~ DBUS sm acquired')
            #pout.v(sm)
        else:
            dbg('~ DBUS NO SM here')
        autostart_id = os.getenv("DESKTOP_AUTOSTART_ID", default="")
        # pout.v(sm)
        self.smClientId = sm.RegisterClient(APP_NAME, autostart_id)
        #self.smClientId = sm.RegisterClient(APP_NAME, "a", 0)

    # Set up to handle signals from the session manager.
    def init_sm_client(self, smcfg):
        proxy = self.sessionBus.get_object(SMKNOWN[smcfg]['bus'], self.smClientId)
        self.smClient = dbus.Interface(proxy, SMKNOWN[smcfg]['clientif'])
        self.smClient.connect_to_signal("QueryEndSession",
                                         self.sm_on_QueryEndSession)
        self.smClient.connect_to_signal("EndSession", self.sm_on_EndSession)
        self.smClient.connect_to_signal("CancelEndSession",
                                         self.sm_on_CancelEndSession)
        self.smClient.connect_to_signal("Stop", self.sm_on_Stop)

     # Here on a QueryEndSession signal from the session manager.
    def sm_on_QueryEndSession(self, flags):
        self.sessionEnding = True
        # Response args: is_ok, reason.
        dbg('DBUS sm_on_QueryEndSession %s' % flags)
        self.smClient.EndSessionResponse(True, "")

    # Here on an EndSession signal from the session manager.
    def sm_on_EndSession(self, flags):
        self.sessionEnding = True
        dbg('DBUS sm_on_EndSession %s' % flags)
        # Response args: is_ok, reason.
        self.smClient.EndSessionResponse(True, "")

    # Here on a CancelEndSession signal from the session manager.
    def sm_on_CancelEndSession(self):
        dbg('DBUS sm_on_CancelEndSession %s' % flags)
        self.sessionEnding = False

    # Here on a Stop signal from the session manager.
    def sm_on_Stop(self):
        dbg('DBUS sm_on_Stop %s' % flags)
        raise SystemExit

