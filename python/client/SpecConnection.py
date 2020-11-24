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

from SpecClientError import SpecClientNotConnectedError, \
        SpecClientVersionError, SpecClientProtocolError, \
        SpecClientTimeoutError

import SpecEventsDispatcher 

import SpecChannel 
import SpecMessage
import SpecReply

from SpecCommand import SpecCommand
from pyspec.client.SpecMotor import SpecMotor, SpecMotorA

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

DEFAULT_REPLY_TIMEOUT = 1 # in seconds. 

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

        if _class.class_name == "QSpecConnection":
            thread_update = False
        else:
            thread_update = True

        key = (host, specname, thread_update)
        if key not in _instances:
            _instances[key] = _SpecConnection(host, specname, thread_update)

        return _instances[key]

    return get_only_one

@_spec_connection
class SpecConnection(object):
    """ 
    If using this class events are automatically propagated
    from updating thread. 
    Not thread safe. 
    Alternative: QSpecConnection
    """
    class_name = "SpecConnection"

@_spec_connection
class QSpecConnection(object):
    """ 
    If using this class program must take care of calling conn.update_events() 
    for events to propagate 

    create class with argument:  "host:specname"
    """
    class_name = "QSpecConnection"

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

        self.message = None

        self.received_strings = []
        self.output_strings = []
        self.sendq = []

        self.server_version = None

        self.aliasedChannels = {}
        self.reg_channels = {}
        self.reg_replies = {}

        self.simulation_mode = False

        # some shortcuts
        self.macro = self.send_msg_cmd_with_return
        self.macro_noret = self.send_msg_cmd
        self.abort = self.send_msg_abort

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
        self.registerChannel('error', self.error, dispatchMode = FIREEVENT)
        self.registerChannel('status/simulate', self.simulationStatusChanged)

        self.run()

    def get_host(self):
        return self.host

    def get_specname(self):
        return self.specname

    def is_remote(self):
        return is_remote_host(self.host)

    def __str__(self):
        return '<spec connection: %s (@%s:%s)>' % (self.specname, self.host, self.port)

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

    def __del__(self):
        self.close_connection()

    # END update thread handling

    def wait_connected(self, timeout=2):
        if not self.updater.is_running():
            self.updater.run()

        start_waiting = time.time()

        while self.state in (DISCONNECTED, WAITINGFORHELLO):
            time.sleep(0.02)
            if time.time() - start_waiting > timeout:
                raise SpecClientTimeoutError

    def wait_channel_is(self, channel, done_value, timeout):
        pass

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
                    break
        elif self.state == WAITINGFORHELLO:
            if (time.time() - self.waiting_hello_started) > WAIT_HELLO_TIMEOUT:
                log.log(2, "socket connected but no response to hello message.forget this socket")
                self.handle_close()

    def register(self, chan_name, receiver_slot, registrationFlag = SpecChannel.DOREG, dispatchMode = UPDATEVALUE):
        """Register a channel

        Tell the remote Spec we are interested in receiving channel update events.
        If the channel is not already registered, create a new SpecChannel object,
        and connect the channel 'valueChanged' signal to the receiver slot. If the
        channel is already registered, simply add a connection to the receiver
        slot.

        Arguments:
        chan_name -- a string representing the channel name, i.e. 'var/toto'
        receiver_slot -- any callable object in Python

        Keywords arguments:
        registrationFlag -- internal flag
        dispatchMode -- can be SpecEventsDispatcher.UPDATEVALUE (default) or SpecEventsDispatcher.FIREEVENT,
        depending on how the receiver slot will be called. UPDATEVALUE means we don't mind skipping some
        channel update events as long as we got the last one (for example, a motor position). FIREEVENT means
        we want to call the receiver slot for every event.
        """
        if dispatchMode is None:
            return

        chan_name = str(chan_name)

        try:
            if not chan_name in self.reg_channels:
                channel = SpecChannel.SpecChannel(self, chan_name, registrationFlag)

                self.reg_channels[chan_name] = channel

                if channel.spec_chan_name != chan_name:  # for assoc array elements
                    channel.registered = True
                    def valueChanged(value, chan_name=chan_name):
                        channel = self.reg_channels[chan_name]
                        channel.update(value) 
                    self.aliasedChannels[chan_name]=valueChanged
                    self.registerChannel(channel.spec_chan_name, valueChanged, registrationFlag, dispatchMode)
            else:
                channel = self.reg_channels[chan_name]
  
            SpecEventsDispatcher.connect(channel, 'valueChanged', receiver_slot, dispatchMode)
  
            channelValue = self.reg_channels[channel.spec_chan_name].value
            if channelValue is not None:
                # we received a value, so emit an update signal
                channel.update(channelValue,force=True)
        except Exception:
            traceback.print_exc()

    registerChannel = register

    def unregister(self, chan_name, receiver_slot=None):
        """Unregister a channel

        Arguments:
        chan_name -- a string representing the channel to unregister, i.e. 'var/toto'
        """
        chan_name = str(chan_name)

        if chan_name in self.reg_channels:
            channel = self.reg_channels[chan_name] 
            if receiver_slot: 
                SpecEventsDispatcher.disconnect(channel, 'valueChanged', receiver_slot)
            else:
                self.reg_channels[chan_name].unregister()
                del self.reg_channels[chan_name]

    unregisterChannel = unregister

    def run_cmd(self, cmd, timeout=2):
        cmd = SpecCommand(self, cmd, timeout=timeout)
        return cmd()

    def read_channel(self, chan_name):
        p = chan_name.split("/")
        if len(p) == 1:
            chan_name = "var/%s" % chan_name

        chan = self.get_channel(chan_name)
        return chan.read()

    def write_channel(self, chan_name,value):
        p = chan_name.split("/")
        if len(p) == 1:
            chan_name = "var/%s" % chan_name
        chan = self.get_channel(chan_name)
        return chan.write(value)

    def get_position(self, mnemonic):
        chan_name = "motor/%s/position" % mnemonic
        chan = self.get_channel(chan_name)
        return chan.read()

    def get_version(self):
        return self.get("var/VERSION")

    def get_name(self):
        return self.get("var/SPEC")

    def get_motor(self, mne):
        motor = SpecMotorA(self, mne)
        return motor

    def get_motors(self):
        macro = """local md[]; 
            for (i=0; i<MOTORS; i++) { 
                 md[motor_mne(i)]=motor_name(i) }; 
            return md"""

        return self.run_cmd(macro)

    def get_positions(self):
        macro = """ local mpos[]
           for (i=0;i<MOTORS;i++) {
              mpos[motor_mne(i)]=A[i]
           }
        return mpos"""
        positions = self.run_cmd(macro)
        for ky, val in positions.items():
            positions[ky] = float(val)
        return positions

    @property
    def spec_version(self):
        return self.get_version()

    @property
    def name(self):
        return self.get_name()

    def __getattr__(self, name):
        if name in self.get_motors().keys():
            return self.get_motor(name)
        else:
            raise AttributeError(name)

    def get_channel(self, chan_name):
        """Return a channel object

        If the required channel is already registered, return it.
        Otherwise, return a new 'temporary' unregistered SpecChannel object ;
        reference should be kept in the caller or the object will get dereferenced.

        Arguments:
        chan_name -- a string representing the channel name, i.e. 'var/toto'
        """
        if chan_name not in self.reg_channels:
            # return a newly created temporary SpecChannel object, without registering
            return SpecChannel.SpecChannel(self, chan_name, SpecChannel.DONTREG)

        return self.reg_channels[chan_name]

    getChannel = get_channel


    def error(self, error):
        """Emit the 'error' signal when the remote Spec version signals an error."""
        log.error('Error from Spec: %s', error)
        SpecEventsDispatcher.emit(self, 'error', (error, ))

    def simulationStatusChanged(self, sim_state):
        self.simulation_mode = sim_state
        SpecEventsDispatcher.emit(self, 'simulation', (sim_state,))

    def is_simulation(self):
        return self.simulation_mode

    def is_connected(self):
        """Return True if the remote Spec version is connected."""
        return self.state == CONNECTED

    isSpecConnected = is_connected

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

    update = update_events

    def disconnect(self):
        """Disconnect from the remote Spec version."""
        self.handle_close()

    def handle_close(self):
        """Handle 'close' event on socket."""

        self.socket_connected = False
        self.server_version = None

        if self.socket:
            self.close()

        self.valid_socket = False

        self.reg_channels = {}
        self.aliasedChannels = {}
        self.spec_disconnected()

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

        self.received_strings.append(_received)

        if is_python3():
            s = b''.join(self.received_strings)
            sbuffer = memoryview(s)
        else:
            s = ''.join(self.received_strings)
            sbuffer = buffer(s)

        consumedBytes = 0
        offset = 0

        while offset < len(sbuffer):
            if self.message is None:
                self.message = SpecMessage.message(version = self.server_version)

            consumedBytes = self.message.readFromStream(sbuffer[offset:])

            if consumedBytes == 0:
                break

            offset += consumedBytes

            if self.message.isComplete():
                try:
                    # dispatch incoming message
                    if self.message.cmd == SpecMessage.REPLY:
                        self.dispatch_reply_msg(self.message)
                    elif self.message.cmd == SpecMessage.EVENT:
                        self.dispatch_event_msg(self.message)
                    elif self.message.cmd == SpecMessage.HELLO_REPLY:
                        self.dispatch_hello_reply_msg(self.message)
                except Exception as e:
                    self.message = None
                    self.received_strings = [ s[offset:] ]
                    raise SpecClientProtocolError(str(e))
                else:
                    self.message = None
                                   
        self.received_strings = [ s[offset:] ]

    def dispatch_event_msg(self, msg):

        chan_name = msg.name

        chan = self.reg_channels.get(chan_name, None)

        if chan is None:
            raise SpecClientProtocolError("received event for unregistered channel %s" % chan_name)

        chan.update(msg.data, msg.flags == SpecMessage.DELETED)

    def dispatch_reply_msg(self, msg):
        reply_id = msg.sn

        if reply_id <= 0:
            return 

        reply = self.reg_replies.get(reply_id, None)

        if reply is None:
            raise SpecClientProtocolError("non expected reply received")

        # deliver data to reply
        del self.reg_replies[reply_id]

        is_error = (msg.type == SpecMessage.ERROR)
        errmsg = msg.err
        reply.update(msg.data, is_error, errmsg)

    def dispatch_hello_reply_msg(self, msg):
        if self.check_appname(msg.name):
            self.server_version = msg.vers #header version
            self.spec_connected()
        else:
            self.server_version = None
            self.socket_connected = False
            self.close()
            self.state = DISCONNECTED

    def check_appname(self, name):
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
            self.specname = name
            return True

    def readable(self):
        return self.valid_socket

    def writable(self):
        """Return True if socket should be written."""
        if not self.readable(): 
            return False

        buf_len = sum(map(len, self.output_strings)) 

        if len(self.sendq) > 0 or buf_len > 0:
            return True
        return False

        #ret = self.readable() and (len(self.sendq) > 0 or sum(map(len, self.output_strings)) > 0)
        #return ret

    def handle_connect(self):
        """Handle 'connect' event on socket

        Send a HELLO message.
        """
        self.socket_connected = True
        self.state = WAITINGFORHELLO
        self.waiting_hello_started = time.time()
        self.send_msg_hello()

    def handle_write(self):
        """Handle 'write' events on socket

        Send all the messages from the queue.
        """
        while len(self.sendq) > 0:
            self.output_strings.append(self.sendq.pop().sendingString())

        if is_python3():
            out_buffer = b''.join(self.output_strings)
        else:
            out_buffer = ''.join(self.output_strings)

        sent = self.send(out_buffer)

        self.output_strings = [ out_buffer[sent:] ]


    def send_msg_cmd_with_return(self, cmd):
        """Send a command message to the remote Spec server, and return the reply id.

        Arguments:
        cmd -- command string, i.e. '1+1'
        """
        if not self.is_connected():
            raise SpecClientNotConnectedError

        try:
            caller = sys._getframe(1).f_locals['self']
        except KeyError:
            caller = None

        reply, msg = SpecMessage.msg_cmd_with_return(cmd, version = self.server_version)
        reply_id = self.__send_msg_with_reply(reply, msg, receiver_obj = caller)

        return reply_id

    def wait_reply(self, reply_id, timeout=DEFAULT_REPLY_TIMEOUT):

        start_wait = time.time()

        if reply_id not in self.reg_replies:
            return None

        reply = self.reg_replies[reply_id]

        while reply.is_pending():
            elapsed = time.time() - start_wait
            if elapsed > timeout:
                raise SpecClientTimeoutError('timeout waiting for reply')
            time.sleep(0.02)

        return reply.get_data()

    def send_msg_func_with_return(self, cmd):
        """Send a command message to the remote Spec server using the new 'func' feature, and return the reply id.

        Arguments:
        cmd -- command string
        """
        if self.server_version < 3:
            raise SpecClientVersionError("need spec server minimum version 3")
        
        if not self.is_connected():
            raise SpecClientNotConnectedError

        try:
            caller = sys._getframe(1).f_locals['self']
        except KeyError:
            caller = None

        reply, msg = SpecMessage.msg_func_with_return(cmd, version = self.server_version)
        reply_id = self.__send_msg_with_reply(reply, msg, receiver_obj = caller)
        return reply_id

    def send_msg_cmd(self, cmd):
        """Send a command message to the remote Spec server.

        Arguments:
        cmd -- command string, i.e. 'mv psvo 1.2'
        """
        if not self.is_connected():
            raise SpecClientNotConnectedError

        self.__send_msg_no_reply(SpecMessage.msg_cmd(cmd, version = self.server_version))

    def send_msg_func(self, cmd):
        """Send a command message to the remote Spec server using the new 'func' feature

        Arguments:
        cmd -- command string
        """
        if self.server_version < 3:
            raise SpecClientVersionError("need spec server minimum version 3")

        if not self.is_connected():
            raise SpecClientNotConnectedError

        msg = SpecMessage.msg_func(cmd, version = self.server_version)
        self.__send_msg_no_reply( msg )

    def send_msg_chan_read(self, chan_name):
        """Send a channel read message, and return the reply id.

        Arguments:
        chan_name -- a string representing the channel name, i.e. 'var/toto'
        """
        if not self.is_connected():
            raise SpecClientNotConnectedError

        try:
            caller = sys._getframe(1).f_locals['self']
        except KeyError:
            caller = None

        reply, msg = SpecMessage.msg_chan_read(chan_name, version = self.server_version)
        reply_id = self.__send_msg_with_reply(reply, msg, receiver_obj = caller)
        return reply_id

    def send_msg_chan_send(self, chan_name, value):
        """Send a channel write message.

        Arguments:
        chan_name -- a string representing the channel name, i.e. 'var/toto'
        value -- channel value
        """
        if not self.is_connected():
            raise SpecClientNotConnectedError

        msg = SpecMessage.msg_chan_send(chan_name, value, version = self.server_version)
        self.__send_msg_no_reply( msg )

    def send_msg_register(self, chan_name):
        """Send a channel register message.

        Arguments:
        chan_name -- a string representing the channel name, i.e. 'var/toto'
        """
        if not self.is_connected():
            raise SpecClientNotConnectedError

        msg = SpecMessage.msg_register(chan_name, version = self.server_version)
        self.__send_msg_no_reply( msg )

    def send_msg_unregister(self, chan_name):
        """Send a channel unregister message.

        Arguments:
        chan_name -- a string representing the channel name, i.e. 'var/toto'
        """
        if not self.is_connected():
            raise SpecClientNotConnectedError

        msg = SpecMessage.msg_unregister(chan_name, version = self.server_version)
        self.__send_msg_no_reply( msg )

    def send_msg_close(self):
        """Send a close message."""
        if not self.is_connected():
            raise SpecClientNotConnectedError

        msg = SpecMessage.msg_close(version = self.server_version)
        self.__send_msg_no_reply( msg )

    def send_msg_abort(self):
        """Send an abort message."""
        if not self.is_connected():
            raise SpecClientNotConnectedError

        msg = SpecMessage.msg_abort(version = self.server_version)
        self.__send_msg_no_reply( msg )

    def send_msg_hello(self):
        """Send a hello message."""
        msg = SpecMessage.msg_hello()
        self.__send_msg_no_reply(msg)

    def __send_msg_with_reply(self, reply, msg, receiver_obj = None):
        """Send a message to the remote Spec, and return the reply id.

        The reply object is added to the reg_replies dictionary,
        with its reply id as the key. The reply id permits then to
        register for the reply using the 'registerReply' method.

        Arguments:
        reply -- SpecReply object which will receive the reply
        message -- SpecMessage object defining the message to send
        """
        reply_id = reply.id
        self.reg_replies[reply_id] = reply

        if hasattr(receiver_obj, 'replyArrived'):
            SpecEventsDispatcher.connect(reply, 'replyFromSpec', receiver_obj.replyArrived)

        self.sendq.insert(0, msg)

        return reply_id

    def __send_msg_no_reply(self, msg):
        """Send a message to the remote Spec.

        If a reply is sent depends only on the message, and not on the
        method to send the message. Using this method, any reply is
        lost.
        """
        self.sendq.insert(0, msg)

if __name__ == '__main__':
    import sys
    log.start()

    conn = ThreadedSpecConnection(sys.argv[1])
    conn.wait_connected(timeout=10)
    print("connection is now ready")
