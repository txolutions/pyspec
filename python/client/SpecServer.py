#  %W%  %G% CSS
#  "pyspec" Release %R%
#

import re
import time
import socket
import asyncore

from pyspec.utils import is_python3
from pyspec.css_logger import log

from SpecConnection import MIN_PORT, MAX_PORT
import SpecMessage as SpecMessage

import spec_updater 

class SpecHandler(asyncore.dispatcher):

    def __init__(self, request, client_address, server):
        asyncore.dispatcher.__init__(self, request)

        # not used
        self.client_address = client_address

        self.server = server
        self.sendq = []

        self.received_strings = []
        self.output_strings = []
        self.client_version = None
        self.client_order = ""

        self.message = None

    # asyncore interface
    def writable(self):
        return len(self.sendq) > 0 or sum(map(len, self.output_strings)) > 0

    def handle_read(self):
        try:
            received = self.recv(32768)

            self.received_strings.append(received)

            if is_python3():
                s = b''.join(self.received_strings)
                sbuffer = memoryview(s)
            else:
                s = ''.join(self.received_strings)
                sbuffer = buffer(s)

            consumedBytes = 0
            offset = 0
            received_messages = []

            while offset < len(sbuffer):

                if self.message is None:
                    try:
                        self.message = SpecMessage.message(version = self.client_version, order=self.client_order)
                    except:
                        import traceback
                        log.log(2, traceback.format_exc())

                consumedBytes = self.message.readFromStream(sbuffer[offset:])
    
                if consumedBytes == 0:
                    break

                offset += consumedBytes

                if self.message.isComplete():
                    # dispatch incoming message
                    if self.message.cmd == SpecMessage.HELLO:
                        self.client_order = self.message.packedHeaderDataFormat[0]
                        self.client_version = self.message.vers
                        self.clientName = self.message.name
                        self.send_hello_reply(self.message.sn, str(self.server.name))
                    else:
                        received_messages.append(self.message)

                    self.message = None

            self.received_strings = [ s[offset:] ]

            for message in received_messages:
                if not self.dispatch_message(message):
                   self.send_error(message.sn, '', 'unsupported command type : %d' % message.cmd)
        except:
            import traceback
            log.log(3,"SpecServer read error. %s" % traceback.format_exc())
            return

    def handle_write(self):
        #
        # send all the messages from the queue
        #
        while len(self.sendq) > 0:
            self.output_strings.append(self.sendq.pop().sendingString())

        try:
            outbuf = b''.join(self.output_strings)

            sent = self.send(outbuf)
            self.output_strings = [ outbuf[sent:] ]
        except:
            import traceback
            log.log(3,"error writing message: %s", traceback.format_exc())

    def handle_close(self):
        self.close()
        try:
            self.server.clients.remove(self)
        except:
            log.log(2,"removing client from spec server. but it is gone already")
            pass

    # END asyncore interface 

    def dispatch_message(self, message):
        try:
            if message.cmd == SpecMessage.CHAN_READ:
                # temporary code (workaround for a Spec client bug)
                self.get_and_reply(reply_id=message.sn, channame=message.name)
            elif message.cmd == SpecMessage.CHAN_SEND:
                self.set_and_reply(reply_id=message.sn, channame=message.name, 
                        value=message.data)
            elif message.cmd in (SpecMessage.CMD_WITH_RETURN, SpecMessage.FUNC_WITH_RETURN):
                self.run_and_reply(reply_id=message.sn, cmd=message.data)
            elif message.cmd == SpecMessage.FUNC_WITH_RETURN:
                self.run_and_reply(reply_id=message.sn, cmd=message.data)
            elif message.cmd == SpecMessage.CMD:
                # in this case we allow for multiple commands separated by colon
                cmdstr = message.data
                cmds = cmdstr.split(";")
                for cmd in cmds:
                    self.run_and_reply(reply_id=message.sn, cmd=cmd)
            elif message.cmd == SpecMessage.REGISTER:
                if message.name == 'update':
                    log.log(3,"update channel registered !")
                    self.updateRegistered = True
            else:
                return False
            return True
        except:
            import traceback
            log.log(2,traceback.format_exc())
            return False
    
    def get_and_reply(self, reply_id, channame):

        ret = self.server.get_value(channame)

        if ret is None:
            self.send_error(reply_id, '', 'cannot get channel ' + channame)
        else:
            self.send_reply(reply_id, '', ret)

    def set_and_reply(self, reply_id, channame, value):

        try:
            ret = self.server.set_value(channame, value)
        except Exception:
            import traceback
            log.log(2, traceback.format_exc())

        if ret is None:
            self.send_error(reply_id, '', 'cannot set channel ' + channame)
        else:
            self.send_reply(reply_id, '', ret)

    def run_and_reply(self, reply_id = None, cmd = '', *args):

        if len(cmd) == 0 or reply_id is None:
            return

        if len(args) == 0:
            cmdstr = str(cmd)
            command, args = self.parse_command(cmdstr)
        else:
            command = cmd

        func = None

        if command in self.server.commands:
            func = self.server.commands[ command ][0]
        elif hasattr(self, command):
            func = getattr(self, command)
        elif hasattr(self.server, command):
            func = getattr(self.server, command)
        else:
            self.send_error(reply_id, '', '"' + command + '" command does not exist.')
            return

        if callable(func):
            try:
                ret = func(*args)
            except:
                import traceback
                traceback.print_exc()

                self.send_error(reply_id, '', 'Failed to execute command "' + command + '"')
            else:
                if ret is None:
                    self.send_error(reply_id, '', command + ' returned None.')
                else:
                    self.send_reply(reply_id, '', str(ret))
        else:
            self.send_error(reply_id, '',  command + ' is not callable on server.')

    def send_hello_reply(self, reply_id, serverName):
        self.sendq.append(SpecMessage.msg_hello_reply(reply_id, serverName, \
                version = self.client_version, order=self.client_order))

    def send_reply(self, reply_id, name, data):
        self.sendq.append(SpecMessage.reply_message(reply_id, name, data, \
                version = self.client_version, order=self.client_order))

    def send_error(self, reply_id, name, data):
        self.sendq.append(SpecMessage.error_message(reply_id, name, data, \
                version = self.client_version, order=self.client_order))

    def send_msg_event(self, chanName, value, broadcast=True):
        self.sendq.append(SpecMessage.msg_event(chanName, value, \
                version = self.client_version, order=self.client_order))
        if broadcast:
            for client in self.server.clients:
                client.send_msg_event(chanName, value, broadcast=False)

    def parse_command(self, cmdstr):

        if SpecMessage.NULL in cmdstr:
            cmdparts = cmdstr.split(SpecMessage.NULL)
            command = cmdparts[0]
            args = tuple([ eval(cmdpart) for cmdpart in cmdparts[1:] ])
            return command, args

        cmd_with_parenthesis = (cmdstr.find('(') >= 0) and True or False

        if cmd_with_parenthesis:
            parent_starts = cmdstr.find('(')
            try:
                command = cmdstr[:cmdpartLength]
                args = eval(cmdstr[cmdpartLength:])
            except:
                print( 'error parsing command string %s' % cmdstr )
                return '', ()
            else:
                if not isinstance(args,tuple):
                    args = (args, )
                return command, args

        # no parenthesis (no else necessary)
        if not cmd_with_parenthesis:
            parts = re.split("\s+", cmdstr.strip())
            if len(parts) > 1:
               command = parts[0]
               args    = parts[1:]
               return command, args
            else:
               return cmdstr, ()

class SpecServer(asyncore.dispatcher):

    def __init__(self, host=None, name=None, allow_name_change=True, 
            handler=SpecHandler):

        asyncore.dispatcher.__init__(self)

        self.handler_class = handler
        self.updater = None
        self.last_print = time.time()

        if host is None:
            self.host = "localhost"
        else:
            self.host = host  # only needed to select a particular ip in the computer

        #
        self.last_log_print = time.time()
        self.log_period = 10

        self.name = None
        self.allow_name_change = allow_name_change

        self.clients = []

        self.commands = {
                "?":  [self.get_help,],
                "command_list":  [self.get_command_list,],
                "channel_list":  [self.get_channel_list,],
                }

        self.channels = {}

        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()

        if name is not None:
            self.set_name(name)
        else:
            # delay socket creation
            log.log(2, "SpecServer created without a name. set a name to start it")

    def set_commands(self, cmds):
        self.commands.update(cmds)

    def set_command(self, cmdname, cmdinfo):
        if isinstance(cmdinfo , list):
            self.commands[cmdname] = cmdinfo
        else:
            self.commands[cmdname] = (cmdinfo,)

    def set_channels(self, channels):
        self.channels.update(channels)

    def set_channel(self, channel_name, channel_info):
        self.channels[channel_name] = channel_info

    def get_value(self, name):
        if name in self.channels:
            getcmd = self.channels[name][1]
            if getcmd:
                return getcmd()
            else:
                return None
        return None

    def set_value(self, name, value):
        if name in self.channels:
            setcmd = self.channels[name][0]
            if setcmd:
                return setcmd(value)
            else:
                return none
        return None

    def get_help(self):
        help_str = """This is a demo spec server
Public channels are:
%s
Public commands are:
%s
        """ %  (self.get_channel_list(), self.get_command_list())
        return help_str

    def get_command_list(self):
        return ",".join(self.commands.keys())

    def get_channel_list(self):
        return ",".join(self.channels.keys())

    # sets a name and start server (open socket) if not started yet
    def set_name(self, name):

        if self.name is not None and name != self.name:
            new_name = True
        else:
            new_name = False

        if not self.allow_name_change and new_name:
            if self.name is not None and name != self.name:
                return

        if name is None:
            log.log(2, "cannot start SpecServer without a name.") 
            return

        self.name = name

        if new_name:
            log.log(2, "server name has been changed.")
            return 

        # start only once and when a name is provided
        # a name change does not change the port

        if isinstance(self.name, str): 
            # choose a port number from PORT range
            host = ""
            for p in range(MIN_PORT, MAX_PORT):
                self.server_address = (host,p)

                try:
                    self.bind(self.server_address)
                    self.bind_ok = True
                    break
                except:
                    # already used. continue
                    continue
            else:
                log.log(2, "ALL server addresses are taken. Cannot start")
        else:
            # it is a port number. use that one
            self.server_address = (self.host, self.name)
            try:
                self.bind(self.server_address)
                self.bind_ok = True
            except:
                log.log(2, "Cannot start server on port %s. Already used?" % self.name)

        if self.bind_ok:
            log.log(2,"spec server listening on %s" % str(self.server_address))
            self.listen(5)

    def handle_accept(self):
        try:
            conn, addr = self.accept()
        except:
            return
        else:
            conn.setblocking(0)
            self.clients.append(self.handler_class(conn, addr, self))

    def get_info(self):
        return {'running': self.is_running(), 
                'allow_name_change': self.allow_name_change,
                'name': self.name}

    # auto 
    def run(self):

        if self.is_running():
           return

        # start a thread for automatic update
        self.updater = spec_updater.spec_updater(method=spec_updater.THREAD, 
                update_func=self._update)

        log.log(2, "starting spec server with name: %s" % self.name)
        self.updater.start() 

    def _update(self):

        asyncore.loop(timeout=1,count=1)

        if time.time() - self.last_log_print > self.log_period:
            log.log(4, "command server is running")
            self.last_log_print = time.time()

    def is_running(self):
        if self.updater is None:
            return False
        return self.updater.is_running()

    def stop(self):
        self.updater.stop() 

    def serve_forever(self):
        asyncore.loop()

if __name__ == "__main__":
    import sys

    global myvar
    myvar = 5

    def say_hello(name):
        print("hello "+name)
        return "done"

    def set_var(value):
        global myvar
        log.log(2, "setting variable to %s" % value)
        myvar = value
        return myvar

    def get_var():
        return myvar
        return 5

    def sum_data(data):
        print("received data %s" % str(data))

    log.start()
    name  = sys.argv[1]
    server = SpecServer(name=name)
    server.set_commands({"hello": [say_hello,]})
    server.set_channel("myvar", [set_var, get_var])
    server.run()

    while True:
        try:
            time.sleep(0.2)
        except KeyboardInterrupt:
            server.stop()
            break

