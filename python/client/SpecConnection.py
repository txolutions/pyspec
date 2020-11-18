#  %W%  %G% CSS
#  "pyspec" Release %R%
#
#$id: SpecConnection.py,v 1.11 2005/12/09 10:32:24 guijarro Exp $
"""SpecConnection module

Low-level module for communicating with a
remove Spec server

Classes :
SpecClientNotConnectedError -- exception class
SpecConnection
SpecConnectionDispatcher
"""

__author__ = 'Matias Guijarro'
__version__ = '1.0'

import asyncore
import socket
import string
import traceback
import sys
import time

from pyspec.css_logger import log
from pyspec.utils import is_python3, is_remote_host

from SpecEventsDispatcher import UPDATEVALUE, FIREEVENT
from SpecClientError import SpecClientNotConnectedError

import SpecEventsDispatcher 

import SpecChannel 
import SpecMessage
import SpecReply

import spec_updater

try:
    import spec_shm
    shm_available = True
except Exception as e:
    shm_available = False

asyncore.dispatcher.ac_in_buffer_size = 32768 #32 ko input buffer

(DISCONNECTED, PORTSCANNING, WAITINGFORHELLO, CONNECTED) = (1,2,3,4)
(MIN_PORT, MAX_PORT) = (6510, 6530)

# timing
WAIT_HELLO_TIMEOUT = 5  # in seconds. timeout for hello reply
UPDATER_TIME = 10 # in millisecs.  update time for spec_updater

def _spec_connection(_class):
    """ decorator to provide connection parameter singletons """
    _instances = {}

    def get_only_one(spec_app):
        """ creating or just return the one and only class instance.
            The singleton depends on the parameters used in __init__ """

        t = spec_app.split(":")
        if len(t) == 2:
            host, specname = t
        else:
            host = "localhost"
            specname = spec_app

        if _class.class_name == "ThreadedSpecConnection":
            thread_update = True
        else:
            thread_update = False

        key = (host, specname, thread_update)
        if key not in _instances:
            _instances[key] = _SpecConnection(host, specname, thread_update)

        return _instances[key]

    return get_only_one

@_spec_connection
class ThreadedSpecConnection(object):
    """ 
    If using this class events are automatically propagated
    from updating thread. 
    Not thread safe. 
    Alternative: QSpecConnection
    """
    class_name = "ThreadedSpecConnection"

@_spec_connection
class SpecConnection(object):
    """ 
    If using this class program must take care of calling conn.update_events() 
    for events to propagate 

    create class with argument:  "host:specname"
    """
    class_name = "SpecConnection"

class _SpecConnection(asyncore.dispatcher):
    """SpecConnection class

    Signals:
    connected() -- emitted when the required Spec version gets connected
    disconnected() -- emitted when the required Spec version gets disconnected
    replyFromSpec(reply id, SpecReply object) -- emitted when a reply comes from the remote Spec
    error(error code) -- emitted when an error event is received from the remote Spec
    """
    def __init__(self, host, specname, thread_update):
        """Constructor

        Arguments:
        spec_app -- a 'host:port' string
        """
        asyncore.dispatcher.__init__(self)

        self.updater = None
        log.log(2, "creating _SpecConnection. thread_update=%s" % thread_update)
        self.thread_update = thread_update

        self.socket_connected = False  # a socket is opened

        # state 
        self.state = DISCONNECTED 
        self.valid_socket = False

        self.scanports = False
        self.specname = ''

        self.receivedStrings = []
        self.message = None
        self.serverVersion = None
        self.aliasedChannels = {}
        self.registeredChannels = {}
        self.registeredReplies = {}
        self.sendq = []
        self.outputStrings = []
        self.simulationMode = False

        # some shortcuts
        self.macro       = self.send_msg_cmd_with_return
        self.macro_noret = self.send_msg_cmd
        self.abort         = self.send_msg_abort

        self.host = host
        self.specname = specname

        try:
            self.port = int(self.specname)
            self.specname = None
        except:
            self.port = None
            self.scanports = True

        #
        # register 'service' channels
        #
        self.registerChannel('error', self.error, dispatchMode = SpecEventsDispatcher.FIREEVENT)
        self.registerChannel('status/simulate', self.simulationStatusChanged)

    def get_host(self):
        return self.host

    def get_specname(self):
        return self.specname

    def is_remote(self):
        return is_remote_host(self.host)

    def __str__(self):
        return '<connection to Spec, host=%s, port=%s>' % (self.host, self.port or self.specname)

    def set_socket(self, s):
        self.valid_socket = True
        asyncore.dispatcher.set_socket(self, s)

    # update thread handling
    def is_running(self):
        if self.updater is None:
            return False
        return self.updater.is_running()

    def run(self):
        if self.is_running():
           return

        # start a thread for automatic update
        self.updater = spec_updater.spec_updater(method=spec_updater.THREAD,
                update_time=UPDATER_TIME,
                update_func=self._update)

        self.updater.start()

    def _update(self,timeout=0.01):
        try:
            self.check_connection()
            if asyncore.socket_map:
                asyncore.loop(timeout=0.01, count=1)

            if self.thread_update:
                self.update_events()

        except Exception as e:
            import traceback
            log.log(2, traceback.format_exc())

    def close_connection(self):
        if self.updater is not None:
            self.updater.stop()
        self.close()

    # END update thread handling

    def check_connection(self):
        """Establish a connection to Spec

        If the connection is already established, do nothing.
        Otherwise, create a socket object and try to connect.
        If we are in port scanning mode, try to connect using
        a port defined in the range from MIN_PORT to MAX_PORT
        """
        if not self.socket_connected:
            if self.scanports:
                if self.port is None or self.port > MAX_PORT:
                    self.port = MIN_PORT
                else:
                    self.port += 1

            while not self.scanports or self.port < MAX_PORT:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.2)
                try:
                    if s.connect_ex( (self.host, self.port) ) == 0:
                        self.set_socket(s)
                        self.handle_connect()
                        break
                except socket.error:
                    pass # exception could be 'host not found' for example, we ignore it

                if self.scanports:
                    self.port += 1 
                else:
                    log.log(2, "connected by port number %s succeeded. " % self.port)
                    break
        elif self.state == WAITINGFORHELLO:
            if (time.time() - self.waiting_hello_started) > WAIT_HELLO_TIMEOUT:
                log.log(2, "socket connected but no response to hello message.forget this socket")
                self.handle_close()

    def checkServer(self):
        if self.scanports:
            if self.port is None or self.port > MAX_PORT:
                self.port = MIN_PORT
            else:
                self.port += 1

        while not self.scanports or self.port < MAX_PORT:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.2)
            try:
                if s.connect_ex( (self.host, self.port) ) == 0:
                    return True 
            except socket.error:
                pass #exception could be 'host not found' for example, we ignore it

            if self.scanports:
                self.port += 1 
            else:
                break

        return False

    def registerChannel(self, chanName, receiverSlot, registrationFlag = SpecChannel.DOREG, dispatchMode = SpecEventsDispatcher.UPDATEVALUE):
        """Register a channel

        Tell the remote Spec we are interested in receiving channel update events.
        If the channel is not already registered, create a new SpecChannel object,
        and connect the channel 'valueChanged' signal to the receiver slot. If the
        channel is already registered, simply add a connection to the receiver
        slot.

        Arguments:
        chanName -- a string representing the channel name, i.e. 'var/toto'
        receiverSlot -- any callable object in Python

        Keywords arguments:
        registrationFlag -- internal flag
        dispatchMode -- can be SpecEventsDispatcher.UPDATEVALUE (default) or SpecEventsDispatcher.FIREEVENT,
        depending on how the receiver slot will be called. UPDATEVALUE means we don't mind skipping some
        channel update events as long as we got the last one (for example, a motor position). FIREEVENT means
        we want to call the receiver slot for every event.
        """
        if dispatchMode is None:
            return

        chanName = str(chanName)

        try:
          if not chanName in self.registeredChannels:
            channel = SpecChannel.SpecChannel(self, chanName, registrationFlag)
            self.registeredChannels[chanName] = channel
            if channel.spec_chan_name != chanName:
                channel.registered = True
                def valueChanged(value, chanName=chanName):
                    channel = self.registeredChannels[chanName]
                    channel.update(value) #,force=True)
                self.aliasedChannels[chanName]=valueChanged
                self.registerChannel(channel.spec_chan_name, valueChanged, registrationFlag, dispatchMode)
          else:
            channel = self.registeredChannels[chanName]

          SpecEventsDispatcher.connect(channel, 'valueChanged', receiverSlot, dispatchMode)

          channelValue = self.registeredChannels[channel.spec_chan_name].value
          if channelValue is not None:
            # we received a value, so emit an update signal
            channel.update(channelValue,force=True)
        except Exception:
          traceback.print_exc()

        listreg = [ky for ky in self.registeredChannels.keys() if not ky.startswith('motor') ]

    def unregisterChannel(self, chanName, receiverSlot=None):
        """Unregister a channel

        Arguments:
        chanName -- a string representing the channel to unregister, i.e. 'var/toto'
        """
        chanName = str(chanName)

        if chanName in self.registeredChannels:
            channel = self.registeredChannels[chanName] 
            if receiverSlot: 
                SpecEventsDispatcher.disconnect(channel, 'valueChanged', receiverSlot)
            else:
                self.registeredChannels[chanName].unregister()
                del self.registeredChannels[chanName]

        listreg = [ky for ky in self.registeredChannels.keys() if not ky.startswith('motor') ]

    def getChannel(self, chanName):
        """Return a channel object

        If the required channel is already registered, return it.
        Otherwise, return a new 'temporary' unregistered SpecChannel object ;
        reference should be kept in the caller or the object will get dereferenced.

        Arguments:
        chanName -- a string representing the channel name, i.e. 'var/toto'
        """
        if not chanName in self.registeredChannels:
            # return a newly created temporary SpecChannel object, without registering
            return SpecChannel.SpecChannel(self, chanName, SpecChannel.DONTREG)

        return self.registeredChannels[chanName]

    def error(self, error):
        """Emit the 'error' signal when the remote Spec version signals an error."""
        log.error('Error from Spec: %s', error)
        SpecEventsDispatcher.emit(self, 'error', (error, ))

    def simulationStatusChanged(self, simulationMode):
        self.simulationMode = simulationMode

    def isSpecConnected(self):
        """Return True if the remote Spec version is connected."""
        return self.state == CONNECTED

    def spec_connected(self):
        """Emit the 'connected' signal when the remote Spec version is connected."""
        old_state = self.state
        self.state = CONNECTED
        if old_state != CONNECTED:
            log.log(1,'Connected to %s:%s' % (self.host, self.specname or self.port))
            SpecEventsDispatcher.emit(self, 'connected', ())

    def spec_disconnected(self):
        """Emit the 'disconnected' signal when the remote Spec version is disconnected."""
        # SpecEventsDispatcher.dispatch()
        old_state = self.state
        self.state = DISCONNECTED
        if old_state == CONNECTED:
            log.log(1,'disconnected from %s:%s' % (self.host, self.specname or self.port))
            SpecEventsDispatcher.emit(self, 'disconnected', ())

    def connect_event(self, signal, cb):
        SpecEventsDispatcher.connect(self, signal, cb)

    def update_events(self):
        SpecEventsDispatcher.dispatch()

    def handle_close(self):
        """Handle 'close' event on socket."""

        log.log(2, "connection to spec:%s closed")

        self.socket_connected = False
        self.serverVersion = None

        if self.socket:
            self.close()

        self.valid_socket = False

        self.registeredChannels = {}
        self.aliasedChannels = {}
        self.spec_disconnected()

    def disconnect(self):
        """Disconnect from the remote Spec version."""
        self.handle_close()

    def handle_error(self):
        """Handle an uncaught error."""
        exception, error_string, tb = sys.exc_info()
        # let Python display exception like it wants!
        sys.excepthook(exception, error_string, tb)


    def handle_read(self):
        """Handle 'read' events on socket

        Messages are built from the read calls on the socket.
        """
        _received = self.recv(32768) 

        #if is_python3():
           #_received = _received.decode('utf-8')

        self.receivedStrings.append(_received)

        if is_python3():
            s = b''.join(self.receivedStrings)
            sbuffer = memoryview(s)
            #sbuffer = bytes(sbuffer).decode('utf-8')
        else:
            s = ''.join(self.receivedStrings)
            sbuffer = buffer(s)

        consumedBytes = 0
        offset = 0

        while offset < len(sbuffer):
            if self.message is None:
                self.message = SpecMessage.message(version = self.serverVersion)

            consumedBytes = self.message.readFromStream(sbuffer[offset:])

            if consumedBytes == 0:
                break

            offset += consumedBytes

            if self.message.isComplete():
                try:
                    # dispatch incoming message
                    if self.message.cmd == SpecMessage.REPLY:
                        replyID = self.message.sn

                        if replyID > 0:
                            try:
                                reply = self.registeredReplies[replyID]
                            except:
                                log.exception("Unexpected error while receiving a message from server")
                            else:
                                del self.registeredReplies[replyID]

                                reply.update(self.message.data, self.message.type == SpecMessage.ERROR, self.message.err)
                                #SpecEventsDispatcher.emit(self, 'replyFromSpec', (replyID, reply, ))
                    elif self.message.cmd == SpecMessage.EVENT:
                        try:
                            self.registeredChannels[self.message.name].update(self.message.data, self.message.flags == SpecMessage.DELETED)
                        except KeyError:
                            import traceback
                            log.log(2, traceback.format_exc())
                        except:
                            import traceback
                            log.log(2, traceback.format_exc())
                    elif self.message.cmd == SpecMessage.HELLO_REPLY:
                        if self.checkourversion(self.message.name):
                            self.serverVersion = self.message.vers #header version
                            self.spec_connected()
                        else:
                            self.serverVersion = None
                            self.socket_connected = False
                            self.close()
                            self.state = DISCONNECTED
                except:
                    self.message = None
                    self.receivedStrings = [ s[offset:] ]
                    raise
                else:
                    self.message = None
                                   
        self.receivedStrings = [ s[offset:] ]


    def checkourversion(self, name):
        """Check remote Spec version

        If we are in port scanning mode, check if the name from
        Spec corresponds to our required Spec version.
        """
        if self.scanports:
            if name == self.specname:
                return True
            else:
                return False
        else:
            # if connected by port just be happy
            log.log(2, "connected by port. name received from app is: %s" % name)
            self.specname = name
            return True


    def readable(self):
        return self.valid_socket


    def writable(self):
        """Return True if socket should be written."""
        ret = self.readable() and (len(self.sendq) > 0 or sum(map(len, self.outputStrings)) > 0)
        return ret

    def handle_connect(self):
        """Handle 'connect' event on socket

        Send a HELLO message.
        """
        self.socket_connected = True
        self.state = WAITINGFORHELLO
        self.waiting_hello_time = time.time()
        log.log(2, "sending hello message")
        self.send_msg_hello()

    def handle_write(self):
        """Handle 'write' events on socket

        Send all the messages from the queue.
        """
        while len(self.sendq) > 0:
            self.outputStrings.append(self.sendq.pop().sendingString())

        if is_python3():
            outputBuffer = b''.join(self.outputStrings)
        else:
            outputBuffer = ''.join(self.outputStrings)

        sent = self.send(outputBuffer)

        self.outputStrings = [ outputBuffer[sent:] ]


    def send_msg_cmd_with_return(self, cmd):
        """Send a command message to the remote Spec server, and return the reply id.

        Arguments:
        cmd -- command string, i.e. '1+1'
        """
        if self.isSpecConnected():
            try:
                caller = sys._getframe(1).f_locals['self']
            except KeyError:
                caller = None

            return self.__send_msg_with_reply(replyReceiverObject = caller, *SpecMessage.msg_cmd_with_return(cmd, version = self.serverVersion))
        else:
            raise SpecClientNotConnectedError


    def send_msg_func_with_return(self, cmd):
        """Send a command message to the remote Spec server using the new 'func' feature, and return the reply id.

        Arguments:
        cmd -- command string
        """
        if self.serverVersion < 3:
            log.error('Cannot execute command in Spec : feature is available since Spec server v3 only')
        else:
            if self.isSpecConnected():
                try:
                    caller = sys._getframe(1).f_locals['self']
                except KeyError:
                    caller = None

                message = SpecMessage.msg_func_with_return(cmd, version = self.serverVersion)
                return self.__send_msg_with_reply(replyReceiverObject = caller, *message)
            else:
                raise SpecClientNotConnectedError


    def send_msg_cmd(self, cmd):
        """Send a command message to the remote Spec server.

        Arguments:
        cmd -- command string, i.e. 'mv psvo 1.2'
        """
        if self.isSpecConnected():
            self.__send_msg_no_reply(SpecMessage.msg_cmd(cmd, version = self.serverVersion))
        else:
            raise SpecClientNotConnectedError


    def send_msg_func(self, cmd):
        """Send a command message to the remote Spec server using the new 'func' feature

        Arguments:
        cmd -- command string
        """
        if self.serverVersion < 3:
            log.error('Cannot execute command in Spec : feature is available since Spec server v3 only')
        else:
            if self.isSpecConnected():
                self.__send_msg_no_reply(SpecMessage.msg_func(cmd, version = self.serverVersion))
            else:
                raise SpecClientNotConnectedError


    def send_msg_chan_read(self, chanName):
        """Send a channel read message, and return the reply id.

        Arguments:
        chanName -- a string representing the channel name, i.e. 'var/toto'
        """
        if self.isSpecConnected():
            try:
                caller = sys._getframe(1).f_locals['self']
            except KeyError:
                caller = None

            return self.__send_msg_with_reply(replyReceiverObject = caller, *SpecMessage.msg_chan_read(chanName, version = self.serverVersion))
        else:
            raise SpecClientNotConnectedError


    def send_msg_chan_send(self, chanName, value):
        """Send a channel write message.

        Arguments:
        chanName -- a string representing the channel name, i.e. 'var/toto'
        value -- channel value
        """
        if self.isSpecConnected():
            try:
                self.__send_msg_no_reply(SpecMessage.msg_chan_send(chanName, value, version = self.serverVersion))
            except:
                import traceback
                log.log(1, traceback.format_exc())
        else:
            raise SpecClientNotConnectedError


    def send_msg_register(self, chanName):
        """Send a channel register message.

        Arguments:
        chanName -- a string representing the channel name, i.e. 'var/toto'
        """
        if self.isSpecConnected():
            self.__send_msg_no_reply(SpecMessage.msg_register(chanName, version = self.serverVersion))
        else:
            raise SpecClientNotConnectedError


    def send_msg_unregister(self, chanName):
        """Send a channel unregister message.

        Arguments:
        chanName -- a string representing the channel name, i.e. 'var/toto'
        """
        if self.isSpecConnected():
            self.__send_msg_no_reply(SpecMessage.msg_unregister(chanName, version = self.serverVersion))
        else:
            raise SpecClientNotConnectedError


    def send_msg_close(self):
        """Send a close message."""
        if self.isSpecConnected():
            self.__send_msg_no_reply(SpecMessage.msg_close(version = self.serverVersion))
        else:
            raise SpecClientNotConnectedError


    def send_msg_abort(self):
        """Send an abort message."""
        if self.isSpecConnected():
            self.__send_msg_no_reply(SpecMessage.msg_abort(version = self.serverVersion))
        else:
            raise SpecClientNotConnectedError

    def send_msg_hello(self):
        """Send a hello message."""
        #log.log(2, "sending hello message")
        self.__send_msg_no_reply(SpecMessage.msg_hello())

    def __send_msg_with_reply(self, reply, message, replyReceiverObject = None):
        """Send a message to the remote Spec, and return the reply id.

        The reply object is added to the registeredReplies dictionary,
        with its reply id as the key. The reply id permits then to
        register for the reply using the 'registerReply' method.

        Arguments:
        reply -- SpecReply object which will receive the reply
        message -- SpecMessage object defining the message to send
        """
        replyID = reply.id
        self.registeredReplies[replyID] = reply

        if hasattr(replyReceiverObject, 'replyArrived'):
            SpecEventsDispatcher.connect(reply, 'replyFromSpec', replyReceiverObject.replyArrived)

        self.sendq.insert(0, message)

        return replyID


    def __send_msg_no_reply(self, message):
        """Send a message to the remote Spec.

        If a reply is sent depends only on the message, and not on the
        method to send the message. Using this method, any reply is
        lost.
        """
        self.sendq.insert(0, message)


if __name__ == '__main__':
    import sys
    log.start()
    conn = SpecConnection(sys.argv[1])
    conn.run()
