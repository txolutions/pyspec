#  %W%  %G% CSS
#  "pyspec" Release %R%
#
"""SpecCommand module
.
This module defines the classes Spec command
objects

Classes:
BaseSpecCommand
SpecCommand
SpecCommandA
"""

__author__ = 'Matias Guijarro'
__version__ = '1.0'

import sys

from pyspec.css_logger import log
from pyspec.utils import is_python2

from SpecConnection import SpecClientNotConnectedError
from SpecConnection import SpecConnection
from SpecReply import SpecReply
from SpecWaitObject import waitReply, waitConnection
import SpecEventsDispatcher as SpecEventsDispatcher

from SpecClientError import SpecClientTimeoutError

class BaseSpecCommand:
    """Base class for SpecCommand objects"""
    def __init__(self, command = None, connection = None, callbacks = None):
        self.command = None
        self._conn = None
        self.specapp = None
        self.isConnected = self.isSpecConnected #alias

        if isinstance(connection, str) or (is_python2() and isinstance(connection, unicode)):
            #
            # connection is given in the 'host:port' form
            #
            self.connectToSpec(str(connection))
        else:
            self._conn = connection

        if command is not None:
            self.setCommand(command)

    def connectToSpec(self, specapp):
        self._conn = SpecConnection(specapp)
        self.specapp = specapp
        waitConnection(self._conn, self.__timeout)

    def isSpecConnected(self):
        return self._conn is not None and self._conn.isSpecConnected()

    def isSpecReady(self):
        if self.isSpecConnected():
            try:
                status_channel = self._conn.getChannel("status/ready")
                status = status_channel.read()
            except:
                pass
            else:
                return status

        return False

    def setCommand(self, command):
        self.command = command

    def __repr__(self):
        return '<SpecCommand object, command=%s>' % self.command or ''

    def __call__(self, *args, **kwargs):
        if self.command is None:
            return

        if self._conn is None or not self._conn.isSpecConnected():
            return

        if self._conn.serverVersion < 3:
            func = False

            if 'function' in kwargs:
                func = kwargs['function']

            #convert args list to string args list
            #it is much more convenient using .call('psvo', 12) than .call('psvo', '12')
            #a possible problem will be seen in Spec
            args = map(repr, args)

            if func:
                # macro function
                command = self.command + '(' + ','.join(args) + ')'
            else:
                # macro
                command = self.command + ' ' + ' '.join(args)
        else:
            # Spec knows
            command = [self.command] + list(args)

        return self.executeCommand(command)

    def executeCommand(self, command):
        pass


class SpecCommand(BaseSpecCommand):
    """SpecCommand objects execute macros and wait for results to get back"""
    def __init__(self, command, connection=None, timeout = None):
        self.__timeout = timeout
        BaseSpecCommand.__init__(self, command, connection)

    def executeCommand(self, command):
        if self._conn.serverVersion < 3:
            connectionCommand = 'send_msg_cmd_with_return'
        else:
            if isinstance(command,str):
                connectionCommand = 'send_msg_cmd_with_return'
            else:
                connectionCommand = 'send_msg_func_with_return'

        return waitReply(self._conn, connectionCommand, (command, ), self.__timeout)

class SpecCommandA(BaseSpecCommand):
    """SpecCommandA is the asynchronous version of SpecCommand.
    It allows custom waiting by subclassing."""
    def __init__(self, *args, **kwargs):
        self.__callback = None
        self.__error_callback = None
        self.__callbacks = {
          'connected': None,
          'disconnected': None,
          'statusChanged': None,
        }
        callbacks = kwargs.get("callbacks", {})
        for cb_name in iter(self.__callbacks.keys()):
          if callable(callbacks.get(cb_name)):
            self.__callbacks[cb_name] = SpecEventsDispatcher.callableObjectRef(callbacks[cb_name])

        BaseSpecCommand.__init__(self, *args, **kwargs)

    def connectToSpec(self, specapp, timeout=200):
        if self._conn is not None:
            SpecEventsDispatcher.disconnect(self._conn, 'connected', self._connected)
            SpecEventsDispatcher.disconnect(self._conn, 'disconnected', self._disconnected)

        super(SpecCommandA, self).connectToSpec(specapp)

        SpecEventsDispatcher.connect(self._conn, 'connected', self._connected)
        SpecEventsDispatcher.connect(self._conn, 'disconnected', self._disconnected)

        if self._conn.isSpecConnected():
            self._connected()
        else:
            try:
              waitConnection(self._conn, timeout)
            except SpecClientTimeoutError:
              pass
            SpecEventsDispatcher.dispatch()

    def connected(self):
        pass

    def _connected(self):
        self._conn.registerChannel("status/ready", self._statusChanged)
 
        self._conn.send_msg_hello()        

        try:
            cb_ref = self.__callbacks.get("connected")
            if cb_ref is not None:
                cb = cb_ref()
                if cb is not None:
                    cb()
        finally:
            self.connected()

    def _disconnected(self):
        try:
            cb_ref = self.__callbacks.get("disconnected")
            if cb_ref is not None:
                cb = cb_ref()
                if cb is not None:
                    cb()
        finally:
           self.disconnected()


    def disconnected(self):
        pass

    def _statusChanged(self, ready):
        try:
            cb_ref = self.__callbacks.get("statusChanged")
            if cb_ref is not None:
                cb = cb_ref()
                if cb is not None:
                   cb(ready)
        finally:
            self.statusChanged(ready)
    
    def statusChanged(self, ready):
        pass

    def executeCommand(self, command):
        self.beginWait()

        if self._conn.serverVersion < 3:
            id = self._conn.send_msg_cmd_with_return(command)
        else:
            if isinstance(command,str):
                id = self._conn.send_msg_cmd_with_return(command)
            else:
                id = self._conn.send_msg_func_with_return(command)

    def wait_reply(self):
        pass

    def __call__(self, *args, **kwargs):
        log.log(2,"executing spec command")
        self.__callback = kwargs.get("callback", None)
        self.__error_callback = kwargs.get("error_callback", None)

        return BaseSpecCommand.__call__(self, *args, **kwargs)

    def replyArrived(self, reply):
        if reply.error:
            if callable(self.__error_callback):
                try:
                    self.__error_callback(reply.error)
                except:
                    log.exception("Error while calling error callback (command=%s,spec version=%s)", self.command, self.specapp)
                self.__error_callback = None
        else:
            if callable(self.__callback):
                try:
                    self.__callback(reply.data)
                except:
                    log.exception("Error while calling reply callback (command=%s,spec version=%s)", self.command, self.specapp)
                self.__callback = None

    def beginWait(self):
        pass

    def abort(self):
        if self._conn is None or not self._conn.isSpecConnected():
            return

        self._conn.abort()

