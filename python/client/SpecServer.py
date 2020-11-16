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
from SpecConnection import _SpecUpdateThread

import SpecMessage as SpecMessage

class BaseSpecRequestHandler(asyncore.dispatcher):
    def __init__(self, request, client_address, server):
        asyncore.dispatcher.__init__(self, request)

        self.client_address = client_address
        self.server = server
        self.sendq = []
        self.receivedStrings = []
        self.outputStrings = []
        self.message = None
        self.clientVersion = None
        self.clientOrder = ""

    def handle_read(self):
        try:
            received = self.recv(32768)

            self.receivedStrings.append(received)

            if is_python3():
                s = b''.join(self.receivedStrings)
                sbuffer = memoryview(s)
            else:
                s = ''.join(self.receivedStrings)
                sbuffer = buffer(s)

            consumedBytes = 0
            offset = 0
            received_messages = []

            while offset < len(sbuffer):
                if self.message is None:
                    self.message = SpecMessage.message(version = self.clientVersion, order=self.clientOrder)

                consumedBytes = self.message.readFromStream(sbuffer[offset:])
    
                if consumedBytes == 0:
                    break

                offset += consumedBytes

                if self.message.isComplete():
                    # dispatch incoming message
                    if self.message.cmd == SpecMessage.HELLO:
                        self.clientOrder = self.message.packedHeaderDataFormat[0]
                        self.clientVersion = self.message.vers
                        self.clientName = self.message.name
                        self.send_hello_reply(self.message.sn, str(self.server.name))
                    else:
                        received_messages.append(self.message)

                    self.message = None

            self.receivedStrings = [ s[offset:] ]

            for message in received_messages:
              if not self.dispatchIncomingMessage(message):
                self.send_error(message.sn, '', 'unsupported command type : %d' % message.cmd)
        except:
            import traceback
            log.log(3,"SpecServer read error. %s" % traceback.format_exc())
            return


    def writable(self):
        return len(self.sendq) > 0 or sum(map(len, self.outputStrings)) > 0


    def handle_write(self):
        #
        # send all the messages from the queue
        #
        while len(self.sendq) > 0:
            self.outputStrings.append(self.sendq.pop().sendingString())

        try:
            outputBuffer = b''.join(self.outputStrings)

            sent = self.send(outputBuffer)
            self.outputStrings = [ outputBuffer[sent:] ]
        except:
            import traceback
            log.log(3,"error writing message: %s", traceback.format_exc())


    def handle_close(self):
        self.close()
        self.server.clients.remove(self)

    def dispatchIncomingMessage(self, message):
        pass

    def parseCommandString(self, cmdstr):

        if SpecMessage.NULL in cmdstr:
            cmdparts = cmdstr.split(SpecMessage.NULL)
            command = cmdparts[0]
            args = tuple([ eval(cmdpart) for cmdpart in cmdparts[1:] ])
            return command, args

        cmdpartLength = cmdstr.find('(')

        # no parenthesis
        if cmdpartLength < 0:
            parts = re.split("\s+", cmdstr.strip())
            if len(parts) > 1:
               command = parts[0]
               args    = parts[1:]
               return command, args
            else:
               return cmdstr, ()

        # command with parenthesis
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

    def executeCommandAndReply(self, replyID = None, cmd = '', *args):
        if len(cmd) == 0 or replyID is None:
            return

        if len(args) == 0:
            cmdstr = str(cmd)
            command, args = self.parseCommandString(cmdstr)
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
            self.send_error(replyID, '', '"' + command + '" command does not exist.')
            return

        if callable(func):
            try:
                ret = func(*args)
            except:
                import traceback
                traceback.print_exc()

                self.send_error(replyID, '', 'Failed to execute command "' + command + '"')
            else:
                if ret is None:
                    self.send_error(replyID, '', command + ' returned None.')
                else:
                    self.send_reply(replyID, '', ret)
        else:
            self.send_error(replyID, '',  command + ' is not callable on server.')

    def send_hello_reply(self, replyID, serverName):
        self.sendq.append(SpecMessage.msg_hello_reply(replyID, serverName, version = self.clientVersion, order=self.clientOrder))

    def send_reply(self, replyID, name, data):
        self.sendq.append(SpecMessage.reply_message(replyID, name, data, version = self.clientVersion, order=self.clientOrder))

    def send_error(self, replyID, name, data):
        self.sendq.append(SpecMessage.error_message(replyID, name, data, version = self.clientVersion, order=self.clientOrder))

    def send_msg_event(self, chanName, value, broadcast=True):
        self.sendq.append(SpecMessage.msg_event(chanName, value, version = self.clientVersion, order=self.clientOrder))
        if broadcast:
          for client in self.server.clients:
            client.send_msg_event(chanName, value, broadcast=False)
          
class SpecServerInfo(object):
    def __init__(self):
        self.name = ""
        self.running = False

class SpecServer(asyncore.dispatcher):

    def __init__(self, host=None, name=None, handler=BaseSpecRequestHandler):

        asyncore.dispatcher.__init__(self)

        self.RequestHandlerClass = handler
        self._update_thread = None

        if host is None:
            self.host = "localhost"
        else:
            self.host = host  # only needed to select a particular ip in the computer

        self.address = self.host
        self.name = None

        self.clients = []
        self.commands = {}
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

    def get_command_list(self):
        return ",".join(self.commands.keys())

    def set_name(self,name):
        if self.name is not None:
            self.name = name
            return

        # start only when a name is provided
        self.name = name
        self.address = "{}:{}".format(self.host, self.name)

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
            self.listen(5)

    def get_info(self):
        info = SpecServerInfo()
        info.running = self.is_running()
        info.name = self.name
        return info

    def run(self, name=None):
        if name is not None:
            self.set_name(name)
        elif self.name is None:
            log.log(2, "cannot start SpecServer without a name.") 
            return

        if self._update_thread is not None and self._update_thread.is_running():
           return

        self._update_thread = _SpecUpdateThread()
        self._update_thread._start() 

    def is_running(self):
        if self._update_thread is None:
            return False
        return self._update_thread.is_running()

    def stop(self):
        self._update_thread._stop() 

    def handle_accept(self):
        try:
            conn, addr = self.accept()
        except:
            return
        else:
            conn.setblocking(0)
            self.clients.append(self.RequestHandlerClass(conn, addr, self))

    def serve_update(self):
        asyncore.loop(timeout=1, count=1)

    def serve_forever(self):
        asyncore.loop()

class SpecCommandServerHandler(BaseSpecRequestHandler):

    def __init__(self, *args):
        BaseSpecRequestHandler.__init__(self, *args)

    def dispatchIncomingMessage(self, message):
        log.log(2, "dispatching message. message.cmd is %s" % message.cmd)
        try:
            if message.cmd == SpecMessage.CHAN_READ:
                # temporary code (workaround for a Spec client bug)
                self.getValueAndReply(replyID=message.sn, varname=message.name)
            elif message.cmd == SpecMessage.CHAN_SEND:
                self.setValueAndReply(replyID=message.sn,
                                      varname=message.name, value=message.data)
            elif message.cmd == SpecMessage.CMD_WITH_RETURN:
                self.executeCommandAndReply(replyID=message.sn, cmd=message.data)
            elif message.cmd == SpecMessage.FUNC_WITH_RETURN:
                self.executeCommandAndReply(replyID=message.sn, cmd=message.data)
            elif message.cmd == SpecMessage.CMD:
                # in this case we allow for multiple commands separated by colon
                cmdstr = message.data
                cmds = cmdstr.split(";")
                for cmd in cmds:
                    #log.log(3,"executing command %s"%cmd)
                    self.executeCommandAndReply(replyID=message.sn, cmd=cmd)
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

    def getValueAndReply(self, replyID, varname):
        ret = self.server.get_value(varname)
        if ret is None:
            self.send_error(replyID, '', 'cannot get variable ' + varname)
        else:
            self.send_reply(replyID, '', ret)

    def setValueAndReply(self, replyID, varname, value):
        ret = self.server.set_value(varname, value)
        if ret is None:
            self.send_error(replyID, '', 'cannot set variable ' + varname)
        else:
            self.send_reply(replyID, '', ret)


class SpecCommandServer(SpecServer):

    def __init__(self, host=None, name=None):
        super(SpecCommandServer,self).__init__(
            host, name, handler=SpecCommandServerHandler)

        # channels must be a dictionary indexed by channame
        # each channame must have as value a list with pointers
        #      to set and get functions for that channel
        self.channels = {}
        self.allow_change_name = True
        log.log(2,"SpecCommandServer address is: %s " %
               str(self.address))

    def get_info(self):
        info = super(SpecCommandServer,self).get_info()
        info.allow_change_name = self.allow_change_name
        return info
        
    def run(self, name=None, allow_change_name=True):
        if not self.allow_change_name:
            if self.name is not None and name != self.name:
                log.log(1, "cannot start command server with different name")
                return

        self.allow_change_name = allow_change_name
        super(SpecCommandServer,self).run(name)


if __name__ == "__main__":
    import sys

    def say_hello(name):
        print("hello "+name)
        return "done"

    def set_var(value):
        log.log(2, "setting variable to %s" % value)
        return 1

    def get_var():
        return 5

    def sum_data(data):
        print("received data %s" % str(data))

    log.start()
    name  = sys.argv[1]
    server = SpecCommandServer()
    server.set_command("hello", say_hello)
    server.set_channel("myvar", [set_var, get_var])
    server.run(name=name)

    #server.serve_forever()

