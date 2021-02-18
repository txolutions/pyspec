#  @(#)SpecCommand.py	3.5  12/13/20 CSS
#  "pyspec" Release 3
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

import sys
import time

from pyspec.css_logger import log
from pyspec.utils import is_python2

import SpecEventsDispatcher as SpecEventsDispatcher
from SpecClientError import SpecClientTimeoutError

class SpecCommand(object):
    """Base class for SpecCommand objects"""
    synchronous = True

    def __init__(self, conn, command, callbacks = {}, timeout=5):

        self.command = command
        self._conn = conn
        self.timeout = timeout

        self.reply_pending = False
        self.retvalue = None

        self.specapp = self._conn.get_specname()

        # save callbacks
        self.__callback = None
        self.__error_callback = None

        self.__callbacks = {
            'connected': None,
            'disconnected': None,
            'statusChanged': None,
        }
       
        for cb_name in iter(self.__callbacks.keys()):
            if callable(callbacks.get(cb_name)):
                self.__callbacks[cb_name] = SpecEventsDispatcher.callableObjectRef(callbacks[cb_name])

        if self.synchronous:
            self._conn.wait_connected()
        else:
            SpecEventsDispatcher.connect(self._conn, 'connected', self._connected)
            SpecEventsDispatcher.connect(self._conn, 'disconnected', self._disconnected)

            if self._conn.is_connected():
                self._connected()

    def is_connected(self):
        return self._conn is not None and self._conn.is_connected()

    def __repr__(self):
        return '<SpecCommand object, command=%s>' % self.command or ''

    def __call__(self, *args, **kwargs):
        if self.command is None:
            return

        if not self.is_connected():
            return

        self.__callback = kwargs.get("callback", None)
        self.__error_callback = kwargs.get("error_callback", None)

        if self._conn.server_version < 3:
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

        self.reply_pending = True
        self.retvalue = None

        return self.executeCommand(command)

    def executeCommand(self, command):
        if self._conn.server_version < 3:
            conn_cmd = 'send_msg_cmd_with_return'
        else:
            if isinstance(command,str):
                conn_cmd = self._conn.send_msg_cmd_with_return
            else:
                conn_cmd = self._conn.send_msg_func_with_return

        reply_id = conn_cmd(command)

        if self.synchronous:
            log.log(2, "synchronous command waiting for reply")
            self.wait()
            return self.retvalue
        else:
            return reply_id

    def replyArrived(self, reply):
        log.log(2, "reply arrived for command")
        self.reply_pending = False
        self.retvalue = reply.get_data()

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

    def wait(self):
        start_wait = time.time()
        while self.reply_pending:
            elapsed = time.time() - start_wait
            if elapsed > self.timeout:
                raise SpecClientTimeoutError("timeout waiting for command execution")
            SpecEventsDispatcher.dispatch()
            time.sleep(0.02)

    def abort(self):
        self._conn.abort()

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

class SpecCommandA(SpecCommand):
    """SpecCommandA is the asynchronous version of SpecCommand.
    It allows custom waiting by subclassing."""
    synchronous = False

