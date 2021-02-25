#!/usr/bin/env python

#   @(#)server.py	6.5  12/13/20 CSS
#
#   "spec" Release 6
#
#   Copyright (c) 2018,2019,2020
#   by Certified Scientific Software.
#   All rights reserved.
#   Copyrighted as an unpublished work.

import asyncore
import socket
import time
import sys
import os
import optparse
import re
import struct
import signal
import logging

from logging.handlers import RotatingFileHandler

progname = os.path.basename(sys.argv[0])

class HardwareLogger(logging.Logger):
    def isEnabledFor(self, level):
        return level <= self.getEffectiveLevel()

log = HardwareLogger(__name__)
log.setLevel(2) # by default log messages with level <= 2

__version__ = "1.0"
protocol_version = "V2"
LOCK_DIR = '/tmp'
LOCK_FILE = ''

re_cmd = re.compile("=: (?P<cmdno>\d+) (?P<cmd>.+?)$")

STATUS_BUSY, STATUS_IDLE = (1,0)

struct_types = {
    "ubyte": {'type': "B", 'size': 2},
    "ushort": {'type': "H", 'size': 2},
    "ulong": {'type': "L", 'size': 4},
    "ulong64": {'type': "Q", 'size': 8},
    "byte": {'type': "b", 'size': 2},
    "short": {'type': "h", 'size': 2},
    "long": {'type': "l", 'size': 4},
    "long64": {'type': "q", 'size': 8},
    "float": {'type': "f", 'size': 4},
    "double": {'type': "d", 'size': 8},
}

def wrap_up(*args):
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)
    sys.exit(0)

class Command(object):
    def __init__(self, cmdno, cmd):
        self.cmdno = cmdno
        self.cmd = cmd
        self.response = None
        self.address = 0
        self.error = ''

        parts = cmd.split()

        self.cmdname = parts[0]
        if len(parts) > 1:
            self.args = parts[1:]
        else:
            self.args = []

        argno = 0
        address = None
        for arg in self.args:
            if arg.startswith("a="):
                address = arg[2:]
                break
            argno += 1

        if address:
            self.args.pop(argno)
            self.address = address

    def get_error(self):
        return self.error

    def set_error(self, error):
        self.error = error

    def get_command_name(self):
        return self.cmdname

    def get_address(self):
        return self.address

    def get_args(self):
        return self.args

    def set_response(self, response):
        self.response = str(response)

    def get_command_no(self):
        return self.cmdno

    def get_response(self):
        return self.response

    def get_response_length(self):
        if self.response:
            return len(self.response)
        else:
            return 0

class CommandHandler(asyncore.dispatcher):

    def __init__(self, *args):
        asyncore.dispatcher.__init__(self,*args)
        self.pending_commands = []
        self.writebuf = ''
        self.databuf = ''
        self.readbuf = ''
        self.last_cmdno = -1
        self.data_expected = 0
        self.received_data = ''
        self.sending_data = False
    
    def command_waiting(self):
        return True if self.pending_commands else False

    def get_command(self):
        if self.pending_commands:
            cmd = self.pending_commands.pop(0)
            return cmd

        return None

    def send_response(self,cmd):
        error = cmd.get_error()
        cmdno = cmd.get_command_no()
        resp = cmd.get_response()
        rlen = cmd.get_response_length()

        if error:
            first_char = "!"
        else:
            first_char = "@"

        if rlen: 
            outstr = "%s: %d %d#%s\n" % (first_char, cmdno, rlen, resp)
        else:
            outstr = "%s: %d %d#\n" % (first_char, cmdno, rlen)
        self.writebuf += outstr

    def send_data(self,strdata):
        log.log(4,"sending data") 
        log.log(4," strdata is %s" % type(strdata))
        self.sending_data = True
        self.databuf = strdata

    def readable(self):
        return True

    def writable(self):
        if self.writebuf or self.sending_data:
            return True
        else:
            return False

    def handle_read(self):
        newdata = self.recv(32768)

        # check first if it should be data
        if self.data_expected:
            lendata = len(newdata)
            if lendata <= self.data_expected:
                buf = newdata
                cmd_buf = ''
            else:
                buf = newdata[:self.data_expected]
                cmd_buf = newdata[self.data_expected:]

            self.data_expected -= len(buf)
            self.received_data = ''.join([self.received_data, buf])

            got = len(self.received_data)
            log.log(3, "receiving data.  Got %d so far. %d still missing", got, self.data_expected)

            if self.data_expected != 0:
                log.log(3, "keep waiting for data")
                return
        else:
            cmd_buf = newdata

        if sys.version_info[0] >= 3:
            self.readbuf += cmd_buf.decode('utf-8')
        else:
            self.readbuf += cmd_buf

        # separator is newline. several commands or only part of it can arrive in one read
        while True: 
            eoc = self.readbuf.find('\n')    

            if eoc == -1:
                break
            
            command = self.readbuf[:eoc]
            self.readbuf = self.readbuf[eoc+1:]
            # log.log(1, "new command received: %s", command[0:10])

            # is it a valid command?
            valid = self.check_cmd_syntax(command)
            if not valid and not self.data_expected: 
                log.log(1, "Not a valid command: %s", command)
                continue
            else:
                cmdno, cmd = valid
                if cmdno == self.last_cmdno:
                    log.log(3, "cmdno: %s - already handled. Ignored", cmdno)
                    continue
                else:
                    log.log(4, "cmdno: %s - new command:  [\"%s\"]", cmdno, cmd)
                    self.pending_commands.append( Command(cmdno, cmd) )
                    self.last_cmdno = cmdno

    def handle_write(self):

        if self.writebuf:
            if sys.version_info[0] >= 3:
                sent = self.send( self.writebuf.encode() )
            else:
                sent = self.send( self.writebuf )

            self.writebuf = self.writebuf[sent:]
            log.log(4, "%s values sent. %s remain.", sent,len(self.writebuf))

        if self.sending_data:  # data is always sent raw / as bytes
            log.log(4, "sending data")
            sent = self.send( self.databuf )
            self.databuf = self.databuf[sent:]
            if self.databuf:
                log.log(4, "%s values sent. %s remain.", sent,len(self.databuf))
            else:
                log.log(4,"all data sent")
                self.sending_data = False

    def handle_close(self):
        log.log(2, "Connection closed")
        self.close()

    def check_cmd_syntax(self,cmdbuf):
        mat = re_cmd.match(cmdbuf)
        if mat:
            cmdno = int(mat.group('cmdno'))
            cmd = mat.group('cmd')
            return cmdno, cmd

        return None

    def get_incoming_data(self):
        return self.received_data

    def expect_data(self, data_size):
        self.received_data = ''
        self.data_expected = data_size
        log.log(1, "expecting data  size: %d", self.data_expected)

class HardwareServer(asyncore.dispatcher):

    doc = """
Base class for hardware servers.

Check documentation for writing your own server
"""

    default_port = 5000
    description = "generic"
    dtype = None

    def __init__(self):
        global LOCK_FILE

        self.opt_parser = None
        self.hdw_pars = {}
        self.i_am_running = True
        self.say_bye = False
        self.data_pending = False  # whether there is data to be sent to client
        self.data_acquired = False # whether any data has been acquired
        self.data_read = False # whether data has been read from hardware
        self.data_buffer = None
        self.pending_incoming_data = False # whether expecting data from a write command

        self.incoming_roi = False
        self.roi_table = {}
        self.dims = 1

        self.server_commands = {
            'hello':  self.say_hello,
            'config':  self.config_hdw,
            'exit':  self._server_exit,
            'clear':  self.server_clear,
            'run':  self.acq_run,
            'halt':  self.acq_halt,
            'get_status':  self.get_status,
            'set':  self.set_par,
            'get':  self.get_par,
            'read':  self.read_data,
            'write':  self.write_data,
            'goodbye':  self.goodbye,
            'xfer_done':  self.xfer_done,
            'set_roi': self.set_roi,
            'get_roi': self.get_roi,
        }

        self.configure_server()
        self.parse_args()
        self.handle_args()

        self.selected_address = None

        self.port = self.settings.port
        self.logfile = self.settings.logfile
        LOCK_FILE = self.settings.lockfile

        if self.settings.do_daemon:
            if not self.logfile:
                self.logfile = "/tmp/%s-%s.log" % (progname,self.port)

        # setup logging 
        formatter = logging.Formatter('%(asctime)s.%(msecs)03d - %(levelno)s - %(message)s', \
                         datefmt='%H:%M:%S')

        if self.settings.verbose_level:
            log.setLevel(self.settings.verbose_level)

        if self.logfile:
            #logh = logging.FileHandler(self.logfile)
            logh = RotatingFileHandler(self.logfile,maxBytes=20000000,backupCount=5)
            log.addHandler(logh)
            logh.setFormatter(formatter)
            log.log(3, "Logging begun on logfile %s", self.logfile)
        elif not self.settings.do_kill:
            logh = logging.StreamHandler()
            log.addHandler(logh)
            logh.setFormatter(formatter)
            log.log(3, "Logging begun on stdout")
        # setup logging end

        if not LOCK_FILE:
            LOCK_FILE = "%s/%s-%s.lock" % (LOCK_DIR, progname,  self.port)

        ret = self.check_lock()
        if ret:
            if ret == 1:
                log.log(1, "%s is already running", progname)
                wrap_up()

        if self.settings.do_kill:
            wrap_up()

        if self.settings.do_daemon:
            self.daemonize()

        signal.signal(signal.SIGTERM, self._server_exit)

        try:
            if os.getpgrp() == os.tcgetpgrp(sys.stdout.fileno()):
                #  Running in foreground
                signal.signal(signal.SIGINT, wrap_up)
            #  dont catch control-C if in background
        except BaseException:
            pass

        self.make_lock()

        self.init_server()

        self.handler_class = CommandHandler
        self.handler = None

        self.cmd = None
        self.status = STATUS_IDLE
        self.executing = False

        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind(('', self.port))
        self.listen(5)

    def configure_server(self):
        # stub. to be defined by implementing classes
        pass

    def init_server(self):
        # stub. to be defined by implementing classes
        pass

    def is_1D(self):
        return self.dims != 2

    def is_2D(self):
        return self.dims == 2

    def set_data_dims(self, dims):
        # function to be called by implementation server
        self.dims = dims

    #  arguments handling
    def parse_args(self):
        parser = self.get_option_parser() 
        self.settings, args = parser.parse_args()

    def handle_args(self):
        # allow implementing classes to act on args 
        pass

    def get_option_parser(self):
        if not self.opt_parser:
            self.set_default_args()
        return self.opt_parser

    def add_option(self, sopt, lopt, **kwargs):
        parser = self.get_option_parser()
        opt = parser.add_option
        opt(sopt,lopt,**kwargs)

    def set_default_args(self):
    
        self.opt_parser = optparse.OptionParser(
            usage="usage: %prog [options]",
            description=self.description,
            version="%%prog %s" % __version__)

        opt = self.opt_parser.add_option
        opt('-p', '--port', dest='port', type='int', default=self.default_port,
	    help = "port number")
        opt('-l', '--logfile', dest='logfile', type='str',
	    help = "if specified, log messages will be saved to logfile")
        opt('-L', '--lockfile', dest='lockfile', type='str', 
	    help = "specifies an alternate lockfile.  If unspecified, lockfile will be placed in /tmp")
        opt('-v', '--verbosity', dest='verbose_level', type='int', default=1,
	    help = "")
        opt('-d', '--demonize', dest='do_daemon', action='store_true', default=False,
	    help = "")
        opt('-k', '--kill', dest='do_kill', action='store_true', default=False,
	    help = "")
    
    def make_lock(self):

        try:
            open(LOCK_FILE, "w").write("%d\n" % self.get_pid())
            return 0
        except BaseException:
            import traceback
            log.log(1, "Cannot create lock file %s", LOCK_FILE)
            log.log(1, traceback.format_exc())
            return -1

    def check_lock(self):
        kill_it = self.settings.do_kill

        if not os.path.exists(LOCK_FILE):
            return 0

        try:
            buf = open(LOCK_FILE, 'r').read().strip()
        except IOError:
            log.log(1, "Cannot read existing lock file %s",  LOCK_FILE)
            return -1

        # read pid from lockfile
        try: 
            pid = int(buf)
        except BaseException:
            log.log(1, "File %s is not a server lock file.\n", LOCK_FILE)
            return -1

        # see if process running
        if not self.check_pid(pid):
            os.remove(LOCK_FILE)
            if kill_it:
                log.log(1, "No existing processs found .\n")
                return 0

        if kill_it:
            os.kill(pid,signal.SIGTERM)
            for _i in range(20):
                if not self.check_pid(pid):
                    break
                time.sleep(0.1)
            else:
                os.kill(pid,signal.SIGKILL)

            try:
                os.remove(LOCK_FILE)
            except BaseException:
                # ignore. probably the killed process has removed it
                pass

            if not self.check_pid(pid): 
                print("Process %d terminated" % pid)
                return 0

            print("Unable to terminate process %d" % pid)
            return -1

        return 1
   
    def check_pid(self,pid):        
        """ Check For the existence of a unix pid. """
        try:
            os.kill(pid, 0)
            time.sleep(0.3)
        except OSError:
            return False
        else:
            return True
           
    def daemonize(self):
        # first fork
        self.fork()

        # detach environment
        os.chdir("/")
        os.setsid()
        os.umask(0)

        # second fork
        self.fork()

        sys.stdout.flush()
        sys.stderr.flush()

        # redirect stdin, stdout, stderr
        stream = open('/dev/null', 'r')
        os.dup2(stream.fileno(), sys.stdin.fileno())
        stream = open('/dev/null', 'a+')
        os.dup2(stream.fileno(), sys.stdout.fileno())
        stream = open('/dev/null', 'a+')
        os.dup2(stream.fileno(), sys.stderr.fileno())


    def fork(self):
        """
        Spawn the child process
        """
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as exc:
            sys.stderr.write("Fork failed: %d (%s)\n" % (exc.errno, exc.strerror))
            sys.exit(1)

    def get_pid(self):
        return os.getpid()

    def get_hostname(self):
        return socket.gethostname()

    def should_quit(self):
        return not self.i_am_running

    # protocol support
    def handle_cmd(self, cmd):
        cmdname = cmd.get_command_name()
        args = cmd.get_args()
        addr = cmd.get_address()

        log.log(4, "Executing command %s with args %s", cmdname, str(args))

        if cmdname not in self.server_commands:
            log.log(1, "Unsupported command %s", cmdname )
            return("unknown")
        
        if self.executing:
            log.log(1, "Execution in progress.  Command ignored %s", cmdname)
            return("busy")
        
        cmdfunc = self.server_commands[cmdname]

        self.executing = True

        try:
            self.cmd = cmd
            self.select_address(addr)
            retval = cmdfunc(*args) 
            if retval is True:
                retval = 1
            elif retval is False:
                retval = 0
            elif retval is None:
                retval = ""
            return retval
        except BaseException as e:
            errstr = str(e)
            import traceback
            log.log(1, "Error while executing %s. %s", cmdname, errstr)
            log.log(1, traceback.format_exc())
            return "%s. error: %s" % (cmdname, errstr), True

    def handle_accept(self):
        # when we get a client connection start a dispatcher for that
        # client
        sock, addr = self.accept()
        log.log(2, "Connection by %s on port %s", addr, self.port)
        self.handler = self.handler_class(sock)

    def handle_close(self):
        log.log(2, "Connection closed")
        self.close()

    def command_waiting(self):
        if self.handler:
            return True if self.handler.command_waiting() else False

        return False

    def check_command(self):
        if self.command_waiting():
            if self.handler:
                cmd = self.handler.get_command()
                if cmd:
                    return cmd
        return None
      
    def send_response(self, cmd):
        self.handler.send_response(cmd)

    def _watch_cmds(self):
        self.executing = False
        self.set_status(STATUS_IDLE)

    def update(self):
        try:
            if self.executing:
                self._watch_cmds()

            cmd = self.check_command()

            if cmd is not None:
                response = self.handle_cmd(cmd) 
                log.log(4, "cmdno: %s - response is:  %s", cmd.cmdno, str(response))
                if type(response) in (list,tuple):
                    response, err = response
                else:
                    err = False
                cmd.set_response(response)  
                cmd.set_error(err)
                self.send_response(cmd)
                if self.data_pending:
                    self.handler.send_data(self.data_buffer)
                    self.data_pending = False

        except BaseException:
            import traceback
            log.log(1, traceback.format_exc() )

    def run(self):
        self.i_am_running = True 
        self.say_bye = False
    
        while asyncore.socket_map:
            # sync asyncore
            asyncore.loop(timeout=0.1, count=1)
            self.update()
            time.sleep(0.001) # to avoid grabbing 100 cpu

            if self.say_bye:
                log.log(1,"Bye")
                break

            if self.should_quit():
                # let a chance to get the response out
                self.say_bye = True
                continue

        wrap_up()

    # END protocol support
    
    # COMMANDS
    # server public interface
    def set_commands(self, cmds):
        self.server_commands.update(cmds)

    def add_command(self, cmd, fnct):
        self.server_commands[cmd] = fnct

    def set_status(self,status):
        self.status = status

    def set_idle(self):
        self.status = STATUS_IDLE
    def set_busy(self):
        self.status = STATUS_BUSY

    def get_status(self):
        return self.status, False

    def is_idle(self):
        return (self.status == STATUS_IDLE)

    def is_busy(self):
        return (self.status == STATUS_BUSY)

    def get_description(self):
        return self.description, False

    def select_address(self, address):
        self.selected_address = address

    def say_hello(self, name=None):
        fields = {
           'pid': self.get_pid(),
           'host': self.get_hostname(),
           'desc': self.description,
           'pvers': protocol_version,
        }
        
        if name is not None and name != self.my_name:
            if name != self.my_name:
                hello_str = "This isn't the server you are looking for"
                err = True
        else:
            hello_str = "hello back %(pvers)s %(host)s %(pid)s %(desc)s" % fields
            err = False

        return hello_str, err

    def config_hdw(self, address):
        # returns data_type and size
        msg = "Server needs to implement config_hdw. addr: %s"  % address
        log.log(1, msg)
        return msg, True

    def server_exit(self):
        """ to be overriden by implementing classes """
        pass

    def _server_exit(self, *args):
        # quit
        self.server_exit()
        log.log(3, "server_exit called (args=%s)", str(args))
        self.i_am_running = False
        return "ok", False

    def server_clear(self):
        # clear memory
        log.log(3, "server_clear called")
        return "ok", False

    def acq_run(self, preset, mode):
        log.log(3, "acq_run called with preset and mode: %s - %s", str(preset), str(mode))

    def acq_halt(self, mode):
        log.log(3, "acq_halt called with mode: %s", str(mode))

    def set_par(self, *args):
        if args[0].startswith("a="):
            parname, parvalue = args[1:]
        else:
            parname, parvalue = args[0:2]

        self.hdw_pars[parname] = parvalue
        log.log(3, "set_par parname %s saved in memory with value: %s", parname, parvalue)

        return parvalue

    def get_par(self, *args):
        if args[0].startswith("a="):
            parname = args[1]
        else:
            parname = args[0]

        parvalue = self.hdw_pars.get(parname,None)
        log.log(3, "get_par parname %s has value in memory: %s", parname, parvalue)
        return parvalue

    def read_data(self, *args):
        nb_args = len(args)
        log.log(3, "server_read called with args: %s", str(args))

        if nb_args == 2:
            # 1D
            dims = 1
            # first, last = map(int,args)
        elif nb_args == 4:
            # 2D
            dims = 2
            # row_beg, row_end, col_beg, col_end = map(int,args)
        else:
            dims = 0
            log.log(1, "Cannot decode arguments for read_data")
            return "cannot decode args", True

        # get a 1d or 2d numpy array from server

        log.log(3, "Calling get_data")
        data, dtype = self.get_data(*args)

        if dtype is True:  # it is an error. data is not ready
            return "not ready", True

        if dims == 2:
            roi_data = data
            data = roi_data.flatten()
            data = data.tolist()
            log.log(2, "roi data integration in HardwareServer.py is %s", sum(data))
        else: # dims = 1
            pass
            #rows = len(data)
            #roi_data = data[first:last+1]
            #data = roi_data

        self.dtype = dtype
        self.data_buffer = self.pack_data(data)
        self.data_pending = True

        if dims == 2:
            return "%s %s" % ( len(data), self.dtype )
        else: # dims = 1
            nb_points = len(data)
            # nb_points = last - first + 1
            return "%s" % nb_points

    def write_data(self, *args):
        log.log(3,"write_data called with args: %s", str(args))

        dims = map(int, args)
        if self.is_1D():
            nb_data = dims[1] - dims[0] + 1
        else:
            log.log(2,"it is 2D - dims are: %s", str(dims))
            nb_rows = dims[1] - dims[0] + 1
            nb_cols = dims[3] - dims[2] + 1
            nb_data = nb_rows * nb_cols

        self.pending_incoming_data = True
        self.incoming_roi = dims
        len_data_expected = nb_data * 4  # 4 bytes for a long 2 bytes for a chr in a string
        self.handler.expect_data(len_data_expected)
        return "ok"

    def goodbye(self, *args):
        log.log(3, "Client (%s) disconnected", str(args))
        return "ok", False

    def xfer_done(self, *args):
        if self.pending_incoming_data:
            databuf = self.handler.get_incoming_data()
            data_received = self.unpack_data(databuf)
            log.log(3,"data received: %s", str(args))
            self.set_data(data_received,self.incoming_roi)
            self.pending_incoming_data = False

        self.handler.expect_data(0)
        return "ok", False

    # END COMMANDS

    def get_data(self, *args):
        log.log(1, "get_data should be provided by implementation")

    def set_data(self, data, roi_info):
        log.log(1,"set_data should be provided by implementation")

    def set_roi(self, *args):
        log.log(2, "Running set_roi command with args %s", str(args))
        if self.is_2D():
            if len(args) == 5:
                roiname, row_beg, row_end, col_beg, col_end = args
                self.roi_table[roiname] = map(int, [row_beg, row_end, col_beg, col_end])
            else:
                return "Wrong number of values for ROI set", True
        else:
            if len(args) == 3:
                roiname, beg, end = args
                self.roi_table[roiname] = map(int, [beg, end])
            else:
                return "Wrong number of values for ROI set", True

        return ""

    def get_roi(self, *args):
        log.log(2, "Running get_roi command with args %s",str(args))

        if self.data is None:
            return "No acquisition done", True

        if not self.data_read:
            self.get_data()

        if len(args) == 1:
            roiname = args[0]
 
            if roiname not in self.roi_table:
                return "Unknown ROI", True

            if self.is_2D():
                row_beg, row_end, col_beg, col_end = self.roi_table[roiname]
            else:
                roi_beg, roi_end = self.roi_table[roiname]

        elif len(args) == 4 and self.is_2D():
            row_beg, row_end, col_beg, col_end = map(int,args)
        elif len(args) == 2 and self.is_1D():
            roi_beg, roi_end = map(int, args)
        else:
            return "Bad ROI parameters", True

        if self.is_2D():
            return self.data[row_beg:row_end+1,col_beg:col_end+1].sum()

        # 1D
        return self.data[roi_beg:roi_end+1].sum()

    def pack_data(self, data_list):
        dtype = self.type_to_struct(self.dtype)
        fmt = "<%d%s" % (len(data_list), dtype)
        log.log(3,"packing data. %s values. type is %s. fmt: %s", len(data_list), self.dtype, fmt)
        data_str = struct.pack(fmt, *data_list) 

        log.log(4, "length of string is %s", len(data_str))
        return data_str

    def unpack_data(self, data_str):

        dtype = self.type_to_struct(self.dtype)
        dsize = self.type_to_size(self.dtype)
        tsize = len(data_str)/dsize
        log.log(3,"number of things to unpack %s", tsize)

        fmt = "<%d%s" % (tsize, dtype)

        log.log(3,"unpacking data from str length %s. type is %s. fmt: %s", len(data_str), self.dtype, fmt)
        data = struct.unpack(fmt, data_str)
        log.log(3,"unpacked data. got %s values", len(data))

        return data

    def type_to_struct(self,dtype):
        if dtype in struct_types:  
            return struct_types[dtype]['type']
        return None

    def type_to_size(self,dtype):
        if dtype in struct_types:  
            return struct_types[dtype]['size']
        return None

if __name__ == '__main__':
    #
    #  Give port number or other through command line arguments
    #         
    hdw_server = HardwareServer()
    hdw_server.run()
