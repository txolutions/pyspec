#  %W%  %G% CSS
#  "pyspec" Release %R%
#
"""SpecWaitObject module

This module defines the classes for helper objects
designed for waiting specific events from Spec

Classes:
   wait_object -- base class for Wait objects

Functions:
   wait_update - wait for a channel update (or wait for a certain value in channel)
   wait_reply - wait for a reply for a command
"""

import weakref
import time

from pyspec.utils import is_python2

import SpecEventsDispatcher as SpecEventsDispatcher
from SpecClientError import SpecClientError, SpecClientTimeoutError

DEFAULT_WAIT_TIMEOUT = 5

class wait_object:
    """Helper class for waiting specific events from Spec"""
    def __init__(self, connection):
        """Constructor

        Arguments:
        connection -- a SpecConnection object
        """
        self.connection = weakref.ref(connection)
        self._unregistered = False
        self._connected = False
        self.value = None

    def wait_reply(self, reply_id, argsTuple, timeout = None):
        """Wait for a reply from Spec

        Arguments:
        command -- method returning a replyID to be executed on the connection object
        argsTuple -- tuple of arguments to be passed to the command
        timeout -- optional timeout (defaults to None)
        """
        connection = self.connection()

        if connection is not None:
            try:
                func = getattr(connection, command)
            except:
                return
            else:
                if callable(func):
                    func(*argsTuple)

                self.wait(timeout = timeout)

    def wait_update(self, chan_name, done_value = None, timeout = None):
        """Wait for a channel update

        Arguments:
        chanName -- channel name
        waitValue -- particular value to wait (defaults to None, meaning any value)
        timeout -- optional timeout (defaults to None)
        """
        connection = self.connection()

        if connection is not None:
            self.channelWasUnregistered = False
            channel = connection.getChannel(chanName)

            if not channel.registered:
                self.channelWasUnregistered = True
                connection.registerChannel(chanName, self.channelUpdated) #channel.register()
            else:
                SpecEventsDispatcher.connect(channel, 'valueChanged', self.channelUpdated)

            self.wait(waitValue = waitValue, timeout = timeout)

            if self.channelWasUnregistered:
                connection.unregisterChannel(chanName) #channel.unregister()

    def wait(self, wait_value = None, timeout = 5):
        """Block until the object's internal value gets updated

        Arguments:
        waitValue -- particular value to wait (defaults to None, meaning any value)
        timeout -- optional timeout (defaults to None)

        Exceptions:
        timeout -- raise a timeout exception on timeout
        """
        start_wait = time.time()

        while self._connected:
            if self.value is not None:
                if waitValue is None:
                    return

                if waitValue == self.value:
                    return
                else:
                    self.value = None

            if self.value is None:
                t = (time.time() - t0)*1000
                if timeout is not None and t >= timeout:
                    raise SpecClientTimeoutError

    def replyArrived(self, reply):
        """Callback triggered by a reply from Spec."""
        self.value = reply.get_data()

        if reply.error:
            raise SpecClientError('Server request did not complete: %s' % self.value, reply.error_code)

    def channelUpdated(self, channelValue):
        """Callback triggered by a channel update

        If channel was unregistered, we skip the first update,
        else we update our internal value
        """
        if self.channelWasUnregistered == True:
            #
            # if we were unregistered, skip first update
            #
            self.channelWasUnregistered = 2
        else:
            self.value = channelValue

def wait_update(chan_name, connection, done_value = None, timeout = DEFAULT_WAIT_TIMEOUT):
    """Wait for a channel to be updated

    Arguments:
    chan_name -- channel name (e.g 'var/foo')
    connection -- a 'host:port' string
    waitValue -- value to wait (defaults to None)
    timeout -- optional timeout (defaults to None)
    """
    w = SpecWaitObject(connection)
    w.wait_update(chan_name, done_value = done_value, timeout = timeout)
    return w.value

def waitReply(connection, command, argsTuple, timeout = None):
    """Wait for a reply from a remote Spec server

    Arguments:
    connection -- a 'host:port' string
    command -- command to execute
    argsTuple -- tuple of arguments for the command
    timeout -- optional timeout (defaults to None)
    """
    if isinstance(connection, str) or (is_python2() and isinstance(connection, unicode)):
      connection = str(connection)
      from pyspec.client.SpecConnectionsManager import SpecConnectionsManager
      connection = SpecConnectionsManager().getConnection(connection)
      waitConnection(connection, timeout = timeout)

    w = SpecWaitObject(connection)
    w.waitReply(command, argsTuple, timeout=timeout)

    return w.value

