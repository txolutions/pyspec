#  %W%  %G% CSS
#  "splot" Release %R%
#

import re
import socket
import asyncore

from pyspec.utils import is_python3
from pyspec.css_logger import log

import SpecConnection as SpecConnection
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
          

class SpecServer(asyncore.dispatcher):
    def __init__(self, host, name, handler = BaseSpecRequestHandler):

        asyncore.dispatcher.__init__(self)

        self.name = name
        self.RequestHandlerClass = handler
        self.clients = []

        self.commands = {}

        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)

        self.set_reuse_addr()

        if type(name) == type(''):
            host = ""
            for p in range(SpecConnection.MIN_PORT, SpecConnection.MAX_PORT):
                self.server_address = ( host, p )

                try:
                    self.bind(self.server_address)
                except:
                    continue
                else:
                    break
        else:
            self.server_address = (host, name)
            self.bind(self.server_address)

        #print self.server_address
        self.listen(5)


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

