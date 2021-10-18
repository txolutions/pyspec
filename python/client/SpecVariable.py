#  @(#)SpecVariable.py	3.6  12/13/20 CSS
#  "pyspec" Release 3
#
#$Id: SpecVariable.py,v 1.4 2005/03/17 12:43:46 guijarro Exp $

"""SpecVariable module

This module defines the class for Spec variable objects
"""
import SpecEventsDispatcher as SpecEventsDispatcher
import SpecWaitObject as SpecWaitObject

from SpecEventsDispatcher import UPDATEVALUE, FIREEVENT

class SpecVariable(object):
    """SpecVariable class

    Thin wrapper around SpecChannel objects, to make
    variables watching, setting and getting values easier.
    """
    def __init__(self, conn, varname, callbacks={}):
        """Constructor

        Keyword arguments:
        varname -- the variable name in Spec
        specapp -- 'host:port' string representing a Spec server to connect to (defaults to None)
        timeout -- optional timeout (defaults to None)
        """

        if None in (varname, conn):
            raise SpecClientError("Bad SpecVariable initialization")

        if "/" in varname: 
            self.chan_name = str(varname)
        else:
            self.chan_name = 'var/' + str(varname)

        self._callbacks = {
          'connected': None,
          'disconnected': None,
          'update': None,
        }

        self._conn = conn

        self._conn.connect_event('connected', self.spec_connected)
        self._conn.connect_event('disconnected', self.spec_disconnected)

        print("callbacks are: %s" % str(callbacks))
        for cb_name in iter(self._callbacks.keys()):
            if callable(callbacks.get(cb_name)):
               print("adding callback for signal %s" % cb_name)
               self._callbacks[cb_name] = SpecEventsDispatcher.callableObjectRef(callbacks[cb_name])

    def spec_connected(self):
        pass
    def spec_disconnected(self):
        pass

    def is_connected(self):
        """Return whether the remote Spec version is connected or not."""
        return self._conn is not None and self._conn.is_connected()

    def get(self):
        """Return the watched variable current value."""
        if self.is_connected():
            return self._conn.read_channel(self.chan_name)
        return None

    getValue = get

    @property
    def value(self):
        return self.get()

    @value.setter
    def value(self, value):
        self.set(value)

    def set(self, value):
        """Set the watched variable value

        Arguments:
        value -- the new variable value
        """
        if self.is_connected():
            return self._conn.write_channel(self.chan_name, value)

    setValue = set

    def waitUpdate(self, waitValue = None, timeout = None):
        """Wait for the watched variable value to change

        Keyword arguments:
        waitValue -- wait for a specific variable value
        timeout -- optional timeout
        """
        if self.is_connected():
            w = SpecWaitObject.SpecWaitObject(self._conn)
            w.waitChannelUpdate(self.chan_name, waitValue = waitValue, timeout = timeout)
            return w.value

class SpecVariableA(SpecVariable):
    """SpecVariableA class - asynchronous version of SpecVariable

    Thin wrapper around SpecChannel objects, to make
    variables watching, setting and getting values easier.
    """
    def __init__(self, conn, varname, dispatchMode = UPDATEVALUE, callbacks={}):
        """Constructor

        Keyword arguments:
        varname -- name of the variable to monitor (defaults to None)
        specapp -- 'host:port' string representing a Spec server to connect to (defaults to None)
        """
        super(SpecVariableA,self).__init__(conn, varname, callbacks)

        self.dispatchMode = dispatchMode

        if self._conn.is_connected():
            self.spec_connected()

    def refresh(self):
        self._conn.update()

    def spec_connected(self):
        #
        # register channel
        #
        self._conn.registerChannel(self.chan_name, self._update, dispatchMode = self.dispatchMode)

        try:
            if self._callbacks.get("connected"):
                cb = self._callbacks["connected"]()
                if cb is not None:
                    cb()
        finally:
            self.connected()

    def connected(self):
        """Callback triggered by a 'connected' event from Spec

        To be extended by derivated classes.
        """
        pass

    def spec_disconnected(self):
        try:
            if self._callbacks.get("disconnected"):
                cb = self._callbacks["disconnected"]()
                if cb is not None:
                    cb()
        finally:
            self.disconnected()

    def disconnected(self):
        """Callback triggered by a 'disconnected' event from Spec

        To be extended by derivated classes.
        """
        pass

    def _update(self, value):
        print("new value is %s" % value)
        print("toto")
        print("see if update in _callbacks: %s " % str(self._callbacks))

        try:
            if self._callbacks.get("update"):
                cb = self._callbacks["update"]()
                if cb is not None:
                    cb(value)
        finally:
            self.update(value)

    def update(self, value):
        """Callback triggered by a variable update

        Extend it to do something useful.
        """
        pass

