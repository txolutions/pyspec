#  @(#)SpecMessage.py	3.6  12/13/20 CSS
#  "pyspec" Release 3
#
"""SpecMessage module

This module defines classes and functions for creating messages
from data received from Spec, and for generating messages to be
sent to Spec.

It handles the different message versions (headers 2, 3 and 4).

For message description check the protocol section of the spec
"help server" page or 
  http://certif.com/spec_help/server.html

Message versions:
   V2 - spec 5.04.03 - released July 20, 2003
   V3 - spec 5.04.04 - released July 18, 2004
   V4 - spec 5.04.05 and later - released Sept 30, 2004
"""

import struct
import time
import types

from pyspec.utils import is_python3, is_python2
from pyspec.css_logger import log

from SpecReply import SpecReply
import SpecArray 

DEBUG=4  # debug level for this module

(DOUBLE, STRING, ERROR, ASSOC) = (1,2,3,4)

MAGIC_NUMBER=4277009102
NATIVE_HEADER_VERSION=4
NULL_B=b'\000'
NULL='\000'

# cmd
(CLOSE, ABORT, CMD, CMD_WITH_RETURN, REGISTER, UNREGISTER, EVENT,  \
 FUNC, FUNC_WITH_RETURN, CHAN_READ, CHAN_SEND, REPLY, HELLO, HELLO_REPLY) = \
                                         (1,2,3,4,6,7,8,9,10,11,12,13,14,15)

# flags
DELETED = 0x0001

def message(*args, **kwargs):
    """Return a new SpecMessage object

    The returned SpecMessage object can be of any of the available message
    class. You can specify the desired message class with the 'version' keyword
    argument. If not specified, defaults to NATIVE_HEADER_VERSION.

    Arguments are passed to the appropriate message constructor.

    Keyword arguments:
    version -- message version, defaults to NATIVE_HEADER_VERSION. When
    reading messages from stream, you can set it to None and it will try
    to guess the suitable message class by reading the header version
    from Spec.
    """
    version = kwargs.get('version', NATIVE_HEADER_VERSION)
    order = kwargs.get('order', '<')

    if len(order) == 0:
      order = "<"

    if version == 4:
        m = message4(*args)
    elif version == 3:
        m = message3(*args)
    elif version == 2:
        m = message2(*args)
    else:
        m = anymessage(*args) # only for reading message from stream

    m.packedHeaderDataFormat=order+m.packedHeaderDataFormat[1:]

    return m


def rawtodictonary(rawstring):
    """Transform a list as coming from a SPEC associative array
    to a dictonary - 2dim arrays are transformed top dict with dict
    entries. In SPEC the key contains \x1c"""

    if is_python3():
        rawstring = bytes(rawstring).decode('utf-8')  
    
    raw = rawstring.split(NULL)[:-2]

    data = {}
    for i in range(0,len(raw) - 1,2):

        key,val = raw[i], raw[i+1]
        keyel = key.split("\x1c")

        if len(keyel) == 1:
            if key in data:
              data[key][None] = val
            else:
              data[key]=val
        else:
            if keyel[0] in data and not isinstance(data[keyel[0]], dict):
              data[keyel[0]]={ None: data[keyel[0]] }

            try:
                data[keyel[0]][keyel[1]] = val
            except TypeError:
                data[keyel[0]] = {keyel[1] : val}
            except KeyError:
                data[keyel[0]] = {keyel[1] : val}

    return data

def dictionarytoraw(dict):
    """Transform a Python dictionary object to the string format
    expected by Spec"""

    data = ""

    for key, val in dict.items():
        if isinstance(val,dict):
            for kkey, vval in iter(val.items()):
                if kkey is None:
                  data += str(key) + NULL + str(vval) + NULL
                else:
                  data += ''.join([str(key), '\x1c', str(kkey), NULL, str(vval), NULL])
        else:
            data += str(key) + NULL + str(val) + NULL

    return (len(data) > 0 and data) or NULL

class SpecMessage:
    """Base class for messages."""
    def __init__(self, packedHeader):
        """Constructor

        Arguments:
        packedHeader -- string representing the packed header format for the message,
        use the same syntax as the 'struct' Python module
        """
        self.packedHeaderDataFormat = packedHeader
        self.headerLength = struct.calcsize(self.packedHeaderDataFormat)
        self.bytesToRead = self.headerLength
        self.readheader = True
        self.data = ''
        self.type = None

        #message properties
        self.magic = None
        self.vers = None
        self.size = None
        self.sn = None
        self.sec = None
        self.usec = None
        self.cmd = None
        self.type = None
        self.rows = 0
        self.cols = 0
        self.name = None
        self.err = 0
        self.flags = 0

    def isComplete(self):
        """Return wether a message read from stream has been fully received or not."""
        return self.bytesToRead == 0

    def readFromStream(self, streamBuf):
        """Read buffer from stream and try to create a message from it

        Arguments:
        streamBuf - string buffer of the last bytes received from Spec

        Return value :
        the number of consumed bytes
        """
        consumedBytes = 0

        try:
            while self.bytesToRead > 0 and len(streamBuf[consumedBytes:]) >= self.bytesToRead:
                if self.readheader:
                    self.readheader = False
                    self.type, self.bytesToRead = self.readHeader(streamBuf[:self.headerLength])
                    consumedBytes = self.headerLength
                else:
                    rawdata = streamBuf[consumedBytes:consumedBytes+self.bytesToRead]
                    consumedBytes += self.bytesToRead
                    self.bytesToRead = 0
    
                    self.data = self.readData(rawdata, self.type)
    
        except BaseException as e:
            import traceback
            log.log(2, "error reading message from stream %s" % str(e))
            log.log(2,  traceback.format_exc())
  
        return consumedBytes

    def readHeader(self, rawstring):
        """Read the header of the message coming from stream

        Arguments:
        rawstring -- raw bytes of the header

        Return value:
        (message data type, message data len) tuple
        """
        return (None, 0)

    def readData(self, rawstring, datatype):
        """Read the data part of the message coming from stream

        Arguments:
        rawstring -- raw data bytes
        datatype -- data type

        Return value:
        the data read
        """
        data = rawstring[:-1] #remove last NULL byte

        if datatype == ERROR:
            if is_python3():
                data2 = data.tobytes()
                data = data2.decode('utf-8')
            return data
        elif datatype == STRING or datatype == DOUBLE:
            # try to convert data to a more appropriate type
            if is_python3():
                data2 = data.tobytes()
                data = data2.decode('utf-8')

            try:
                data = int(data)
            except:
                try:
                    data = float(data)
                except:
                    pass

            return data
        elif datatype == ASSOC:
            return rawtodictonary(rawstring)
        elif SpecArray.isArrayType(datatype):
            #Here we read cols and rows... which are *supposed* to be received in the header!!!
            #better approach: data contains this information (since it is particular to that data type)
            return SpecArray.SpecArray(rawstring, datatype, self.rows, self.cols)
        else:
            raise TypeError


    def dataType(self, data):
        """Try to guess data type

        Works for obvious cases only
          - it is a hard job guessing ARRAY_* types, we ignore this case (user has to provide a suitable datatype)
          - we cannot make a difference between ERROR type and STRING type
        """
        if isinstance(data,str):
            return STRING
        elif isinstance(data,dict):
            return ASSOC
        elif isinstance(data,int) or isinstance(data,float):
            return STRING
        elif is_python2() and isinstance(data,long):
            return STRING
        elif isinstance(data, SpecArray.SpecArrayData):
            self.rows, self.cols = data.shape
            return data.type

    def sendingDataString(self, data, datatype):
        """Return the string representing the data part of the message."""
        rawstring = ''

        if datatype in (ERROR, STRING, DOUBLE):
            rawstring = str(data)
        elif datatype == ASSOC:
            rawstring = dictionarytoraw(data)
        elif SpecArray.isArrayType(datatype):
            rawstring = data.tostring()

        if len(rawstring) > 0:
            rawstring += NULL

        return rawstring

    def sendingString(self):
        """Create a string representing the message which can be send
        over the socket."""
        return ''

class message2(SpecMessage):
    """Version 2 message class"""
    def __init__(self, *args, **kwargs):
        """Constructor

        If called without arguments, message is supposed to be read from stream.
        Otherwise, the 'init' method is called with the specified arguments, for
        creating a message from arguments.
        """
        SpecMessage.__init__(self, '<IiiiIIiiIII80s')

        if len(args) > 0:
            self.init(*args, **kwargs)

    def init(self, ser, cmd, name, data, datatype = None, rows = 0, cols = 0):
        """ Create a message from the arguments"""
        self.vers = 2 #header version
        self.size = self.headerLength
        self.magic = MAGIC_NUMBER
        self.rows = rows
        self.cols = cols
        self.data = data
        self.type = datatype or self.dataType(self.data)
        self.time = time.time()
        self.sec = int(self.time)
        self.usec = int((self.time-self.sec)*1E6)
        self.sn, self.cmd, self.name = ser, cmd, str(name)

    def readHeader(self, rawstring):
        self.magic, self.vers, self.size, self.sn, \
                    self.sec, self.usec, self.cmd, \
                    datatype, self.rows, self.cols, \
                    datalen, name  = struct.unpack(self.packedHeaderDataFormat, rawstring)
        if self.magic != MAGIC_NUMBER:
            self.packedHeaderDataFormat=">"+self.packedHeaderDataFormat[1:]
            self.magic, self.vers, self.size, self.sn, \
                    self.sec, self.usec, self.cmd, \
                    datatype, self.rows, self.cols, \
                    datalen, name  = struct.unpack(self.packedHeaderDataFormat, rawstring)

        self.time = self.sec + float(self.usec) / 1E6

        if is_python3():
            self.name = name.replace(NULL_B, b'') #remove padding null bytes
        else:
            self.name = name.replace(NULL, '') #remove padding null bytes

        return (datatype, datalen)

    def sendingString(self):
        if self.type is None:
            # invalid message
            return ''

        data = self.sendingDataString(self.data, self.type)
        datalen = len(data)

        if is_python3():
            name = self.name.encode('utf-8')
            data = data.encode('utf-8')
        else:
            name = str(self.name)

        header = struct.pack(self.packedHeaderDataFormat, self.magic, self.vers, self.size,
                             self.sn, self.sec, self.usec, self.cmd, self.type,
                             self.rows, self.cols, datalen, name)
        return header + data

class message3(SpecMessage):
    def __init__(self, *args, **kwargs):
        SpecMessage.__init__(self, '<IiiiIIiiIIIi80s')

        if len(args) > 0:
            self.init(*args, **kwargs)

    def init(self, ser, cmd, name, data, datatype = None, rows = 0, cols = 0):
        """ Create a message from the arguments """
        self.vers = 3 #header version
        self.size = self.headerLength
        self.magic = MAGIC_NUMBER
        self.rows = rows
        self.cols = cols
        self.data = data
        self.type = datatype or self.dataType(self.data)
        self.time = time.time()
        self.sec = int(self.time)
        self.usec = int((self.time-self.sec)*1E6)
        self.sn, self.cmd, self.name = ser, cmd, str(name)

    def readHeader(self, rawstring):
        self.magic, self.vers, self.size, self.sn, \
                    self.sec, self.usec, self.cmd, \
                    datatype, self.rows, self.cols, \
                    datalen, self.err, name  = struct.unpack(self.packedHeaderDataFormat, rawstring)

        if self.magic != MAGIC_NUMBER:
            self.packedHeaderDataFormat=">"+self.packedHeaderDataFormat[1:]
            self.magic, self.vers, self.size, self.sn, \
                    self.sec, self.usec, self.cmd, \
                    datatype, self.rows, self.cols, \
                    datalen, self.err, name  = struct.unpack(self.packedHeaderDataFormat, rawstring)

        self.time = self.sec + float(self.usec) / 1E6

        if is_python3():
            self.name = name.replace(NULL_B, b'') # remove padding null bytes
        else:
            self.name = name.replace(NULL, '') # remove padding null bytes

        if self.err > 0:
            datatype = ERROR #change message type to 'ERROR' for further processing

        return (datatype, datalen)

    def sendingString(self):
        if self.type is None:
            return ''

        data = self.sendingDataString(self.data, self.type)
        datalen = len(data)

        if is_python3():
            name = self.name.encode('utf-8')
            data = data.encode('utf-8')
        else:
            name = str(self.name)

        header = struct.pack(self.packedHeaderDataFormat, self.magic, self.vers, self.size,
                             self.sn, self.sec, self.usec, self.cmd, self.type,
                             self.rows, self.cols, datalen, self.err, self.name)

        return header + data

class message4(SpecMessage):
    def __init__(self, *args, **kwargs):
        SpecMessage.__init__(self, '<IiIIIIiiIIIii80s')

        if len(args) > 0:
            self.init(*args, **kwargs)

    def init(self, ser, cmd, name, data, datatype = None, rows = 0, cols = 0):
        """ Create a message from the arguments """
        self.vers = 4 #header version
        self.size = self.headerLength
        self.magic = MAGIC_NUMBER
        self.rows = rows
        self.cols = cols
        self.data = data
        self.type = datatype or self.dataType(self.data)
        self.time = time.time()
        self.sec = int(self.time)
        self.usec = int((self.time-self.sec)*1E6)
        self.sn, self.cmd, self.name = ser, cmd, str(name)


    def readHeader(self, rawstring):
        self.magic, self.vers, self.size, self.sn, \
                    self.sec, self.usec, self.cmd, \
                    datatype, self.rows, self.cols, \
                    datalen, self.err, self.flags, name  = struct.unpack(self.packedHeaderDataFormat, rawstring)
        if self.magic != MAGIC_NUMBER:
            self.packedHeaderDataFormat=">"+self.packedHeaderDataFormat[1:]
            self.magic, self.vers, self.size, self.sn, \
                    self.sec, self.usec, self.cmd, \
                    datatype, self.rows, self.cols, \
                    datalen, self.err, self.flags, name  = struct.unpack(self.packedHeaderDataFormat, rawstring)
        self.time = self.sec + float(self.usec) / 1E6
        
        if is_python3():
            name = name.decode()
        
        name = name.replace(NULL, '') #remove padding null bytes
        self.name = name.strip()

        if self.err > 0:
            datatype = ERROR #change message type to 'ERROR' for further processing

        return (datatype, datalen)

    def sendingString(self):
        if self.type is None:
            # invalid message
            return ''

        try:
            data = self.sendingDataString(self.data, self.type)
            datalen = len(data)

            if is_python3():
                name = self.name.encode('utf-8')
                data = data.encode('utf-8')
            else:
                name = str(self.name)

            header = struct.pack(self.packedHeaderDataFormat, self.magic, self.vers, self.size,
                             self.sn, self.sec, self.usec, self.cmd, self.type,
                             self.rows, self.cols, datalen, self.err, self.flags, name)
        except:
            import traceback
            log.log(2,"specmessage error: %s" % traceback.format_exc())

        return header + data

class anymessage(SpecMessage):
    def __init__(self, *args, **kwargs):
        SpecMessage.__init__(self, '<Ii')

    def readFromStream(self, streamBuf):
        if len(streamBuf) >= self.bytesToRead:
            magic, version = struct.unpack(self.packedHeaderDataFormat, streamBuf[:self.headerLength])

            if magic != MAGIC_NUMBER:
                self.packedHeaderDataFormat=">"+self.packedHeaderDataFormat[1:]
                magic, version = struct.unpack(self.packedHeaderDataFormat, streamBuf[:self.headerLength])

            # try to guess which message class suits best
            if version == 2:
                self.__class__ = message2
                message2.__init__(self)
                return self.readFromStream(streamBuf)
            elif version == 3:
                self.__class__ = message3
                message3.__init__(self)
                return self.readFromStream(streamBuf)
            elif version >= 4:
                self.__class__ = message4
                message4.__init__(self)
                return self.readFromStream(streamBuf)

        return 0

def commandListToCommandString(cmdlist):
    """Convert a command list to a Spec command string."""

    if isinstance(cmdlist, list) and len(cmdlist) > 0:
        cmd = [str(cmdlist[0])]

        for arg in cmdlist[1:]:
            argstr = repr(arg)

            if isinstance(arg,dict):
                argstr = argstr.replace('{', '[')
                argstr = argstr.replace('}', ']')

            cmd.append(argstr)

        return NULL.join(cmd)
    else:
        return ''

def msg_cmd_with_return(cmd, version = NATIVE_HEADER_VERSION, order="<"):
    """Return a command with return message"""
    return message_with_reply(CMD_WITH_RETURN, "", cmd, version, order)

def msg_func_with_return(cmd, version = NATIVE_HEADER_VERSION, order="<"):
    """Return a func with return message"""
    cmd = commandListToCommandString(cmd)
    return message_with_reply(FUNC_WITH_RETURN, "", cmd, version, order)

def msg_cmd(cmd, version = NATIVE_HEADER_VERSION, order="<"):
    """Return a command without reply message"""
    return message_no_reply(CMD, "", cmd, version, order)

def msg_func(cmd, version = NATIVE_HEADER_VERSION, order="<"):
    """Return a func without reply message"""
    cmd = commandListToCommandString(cmd)
    return message_no_reply(FUNC, "", cmd, version, order)

def msg_chan_read(channel, version = NATIVE_HEADER_VERSION, order="<"):
    """Return a property-reading message"""
    return message_with_reply(CHAN_READ, channel, "", version, order)

def msg_chan_send(channel, value, version = NATIVE_HEADER_VERSION, order="<"):
    """Return a property-setting message"""
    return message_no_reply(CHAN_SEND, channel, value, version, order)

def msg_event(channel, value, version = NATIVE_HEADER_VERSION, order="<"):
    """Return an event message"""
    return message_no_reply(EVENT, channel, value, version, order)

def msg_register(channel, version = NATIVE_HEADER_VERSION, order="<"):
    """Return a register message"""
    return message_no_reply(REGISTER, channel, "", version, order)

def msg_unregister(channel, version = NATIVE_HEADER_VERSION, order="<"):
    """Return an unregister message"""
    return message_no_reply(UNREGISTER, channel, "", version, order)

def msg_close(version = NATIVE_HEADER_VERSION, order="<"):
    """Return a close message"""
    return message_no_reply(CLOSE, "", "", version, order)

def msg_abort(version = NATIVE_HEADER_VERSION, order="<"):
    """Return an abort message"""
    return message_no_reply(ABORT, "", "", version, order)

def msg_hello(version = NATIVE_HEADER_VERSION, order="<"):
    """Return a hello message"""
    return message_no_reply(HELLO, "python", "", version, order)

def msg_hello_reply(reply_id, serverName, version = NATIVE_HEADER_VERSION, order="<"):
    return message(reply_id, HELLO_REPLY, serverName, serverName, version = version, order=order)

# Methods to send any Messages
def message_with_reply(cmd, name, data, version = NATIVE_HEADER_VERSION, order="<"):
    """ Lower level call to send a message of a certain type """

    new_reply = SpecReply()
    reply_id = new_reply.id

    msg = message(reply_id, cmd, name, data, version = version, order=order)

    return (new_reply, msg)

def message_no_reply(cmd, name, data, version = NATIVE_HEADER_VERSION, order="<"):
    """ Send a message which will not result in a reply from the server.
    If a reply is sent depends only on the cmd and not on the method
    to send the message """
    return message(0, cmd, name, data, version = version, order=order)

def reply_message(reply_id, name, data, version = NATIVE_HEADER_VERSION, order="<"):
    return message(reply_id, REPLY, name, data, version = version, order=order)

def error_message(reply_id, name, data, version = NATIVE_HEADER_VERSION, order="<"):
    return message(reply_id, REPLY, name, data, ERROR, version = version, order=order)
