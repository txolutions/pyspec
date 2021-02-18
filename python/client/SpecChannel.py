#  @(#)SpecChannel.py	3.5  12/13/20 CSS
#  "pyspec" Release 3
#
#$Id: SpecChannel.py,v 1.6 2006/12/14 10:03:13 guijarro Exp $
"""SpecChannel module

This module defines the SpecChannel class
"""

__author__ = 'Matias Guijarro'
__version__ = '1.0'

import SpecEventsDispatcher  as SpecEventsDispatcher
from SpecWaitObject import SpecWaitObject
from SpecClientError import SpecClientError
import weakref

from pyspec.css_logger import log

(DOREG, DONTREG, WAITREG) = (0, 1, 2)

class SpecChannel(object):
    """SpecChannel class

    Represent a channel in Spec

    Signals:
    valueChanged(value, chan_name) -- emitted when the channel gets updated
    """

    def __init__(self, conn, chan_name, registrationFlag = DOREG):
        """Constructor

        Arguments:
        * conn -- a SpecConnection object
        * chan_name -- string representing a channel name, i.e. 'var/toto'

        Keyword arguments:
        * registrationFlag -- defines how the channel is registered, possible
             values are : SpecChannel.DOREG (default), SpecChannel.DONTREG
             (do not register), SpecChannel.WAITREG (delayed registration until Spec is
             reconnected)
        """
        self.conn = weakref.ref(conn)
        self.name = chan_name

        if chan_name.startswith("var/") and '/' in chan_name[4:]:
            l = chan_name.split('/')
            self.spec_chan_name = "/".join((l[0], l[1]))

            if len(l)==3:
                self.access1=l[2]
                self.access2=None
            else:
                self.access1=l[2]
                self.access2=l[3]
        else:
            self.spec_chan_name = self.name
            self.access1=None
            self.access2=None

        self.registrationFlag = registrationFlag

        self._connected = False
        self.registered = False
        self.value = None

        SpecEventsDispatcher.connect(conn, 'connected', self.connected)
        SpecEventsDispatcher.connect(conn, 'disconnected', self.disconnected)

        if conn.is_connected():
            self.connected()

    def connected(self):
        """Do registration when Spec gets connected

        If registration flag is WAITREG put the flag to DOREG if not yet connected,
        and register if DOREG
        """
        if self.registrationFlag == WAITREG:
            if not self._connected:
                self.registrationFlag = DOREG

        self._connected = True

        if self.registrationFlag == DOREG:
            self.register()

    def disconnected(self):
        """Reset channel object when Spec gets disconnected."""
        self.value = None
        self._connected = False

    def read(self):
        """Read the channel value

        If channel is registered, just return the internal value,
        else obtain the channel value and return it.
        """
        if self.registered and self.value is not None:
            return self.value
        
        conn = self.conn()

        if conn is not None:
            #w = SpecWaitObject(conn)
            # make sure spec is connected, we give a short timeout
            # because it is supposed to be the case already
            #w.waitConnection(timeout=500)                                 
            #w.waitReply('send_msg_chan_read', (self.spec_chan_name, ))
            #self.update(w.value)

            conn.wait_connected()

            reply_id = conn.send_msg_chan_read(self.spec_chan_name)

            try:
                self.value = conn.wait_reply(reply_id)
            except SpecClientError as e:
                raise(e)

        return self.value

    def write(self, value):
        """Write a channel value."""
        conn = self.conn()

        if conn is not None:
            if self.access1 is not None:
                if self.access2 is None:
                    value = { self.access1: value }
                else:
                    value = { self.access1: { self.access2: value } }

            conn.send_msg_chan_send(self.spec_chan_name, value)

    def register(self):
        """Register channel

        Registering a channel means telling the server we want to receive
        update events when a channel value changes on the server side.
        """
        if self.spec_chan_name != self.name:
            return

        conn = self.conn()

        if conn is not None:
            conn.send_msg_register(self.spec_chan_name)
            self.registered = True

    def update(self, value, deleted = False,force=False):
        """Update channel's value and emit the 'valueChanged' signal."""

        # receive dictionary - access1 is set (init with var/arr/idx1 or var/arr/idx1/idx2 )
        if isinstance(value, dict) and self.access1 is not None:
            if self.access1 in value:
                if deleted:
                    SpecEventsDispatcher.emit(self, 'valueChanged', (None, self.name, ))
                else:
                    if self.access2 is None:
                        if force or self.value is None or self.value != value[self.access1]: 
                            self.value = value[self.access1]
                            SpecEventsDispatcher.emit(self, 'valueChanged', (self.value, self.name, ))
                    else:
                        if self.access2 in value[self.access1]:
                            if deleted:
                                SpecEventsDispatcher.emit(self, 'valueChanged', (None, self.name, ))
                            else:
                                if force or self.value is None or self.value != value[self.access1][self.access2]:
                                    self.value = value[self.access1][self.access2]
                                    SpecEventsDispatcher.emit(self, 'valueChanged', (self.value, self.name, ))
            return

        # receive dictionary - access1 is not set (init with var/arr)
        if isinstance(self.value, dict) and isinstance(value, dict):
            # update dictionary
            if deleted:
                for key,val in iter(value.items()):
                    if isinstance(val,dict):
                        for k in val:
                            try:
                                del self.value[key][k]
                            except KeyError:
                                pass
                        if len(self.value[key])==1 and None in self.value[key]:
                            self.value[key]=self.value[key][None]
                    else:
                        try:
                            del self.value[key]
                        except KeyError:
                            pass
            else:
                for k1,v1 in iter(value.items()):
                    if isinstance(v1,dict):
                        try:
                            self.value[k1].update(v1)
                        except KeyError:
                            self.value[k1]=v1
                        except AttributeError:
                            self.value[k1]={None: self.value[k1]}
                            self.value[k1].update(v1)
                    else:
                        if k1 in self.value.keys() and isinstance(self.value[k1], dict):
                            self.value[k1][None] = v1
                        else:
                            self.value[k1] = v1
            value2emit=self.value.copy()
            SpecEventsDispatcher.emit(self, 'valueChanged', (value2emit, self.name, ))
            return

        # no assoc array - (init with var/var_name)
        if deleted:
            self.value = None
        else:
            self.value = value
            SpecEventsDispatcher.emit(self, 'valueChanged', (self.value, self.name, ))

    def unregister(self):
        """Unregister channel."""
        conn = self.conn()

        if conn is not None:
            conn.send_msg_unregister(self.spec_chan_name)
            self.registered = False
            self.value = None
