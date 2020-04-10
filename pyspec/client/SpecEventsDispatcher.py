#  %W%  %G% CSS
#  "splot" Release %R%
#
import weakref

import time
import inspect
import platform

try:
   import queue
except ImportError:
   import Queue as queue

import saferef 
from pyspec.css_logger import log

DEBUG=4  # debug level for this module

(UPDATEVALUE, FIREEVENT) = (1, 2)

class SpecClientDispatcherError(Exception):
    def __init__(self, args=None):
        self.args = args

def is_python3():
    return platform.python_version_tuple()[0] == '3'
def is_python2():
    return platform.python_version_tuple()[0] == '2'

def min_args(slot):
    if is_python3():
        sig = inspect.signature(slot)
        params = sig.parameters.values()
        npars = 0
        for param in params:
            if param.kind == param.POSITIONAL_OR_KEYWORD:
                if param.default == param.empty:
                   npars += 1
        return npars
    elif is_python2():
        argspec = inspect.getargspec(slot)
        nargs = len(argspec.args)
        if argspec.defaults:
            nargs -= len(argspec.defaults)
        return nargs
    else:  # python2
        print("Unknown python version")

def robustApply2(slot, arguments = ()):
    """Call slot with appropriate number of arguments"""
    if inspect.isclass(slot):
        slot = slot.__call__

    if hasattr(slot, 'im_func'):
        # an instance method
        if is_python3():
            margs = min_args(slot.__func__) - 1
        else:
            margs = min_args(slot.im_func) - 1
    else:
        margs = min_args(slot) 

    if len(arguments) < margs:
        msg = 'Not enough arguments for calling slot %s ' \
              '(need: %d, given: %d)' % (repr(slot), margs, len(arguments))
        raise SpecClientDispatcherError(msg)
    else:
        return slot(*arguments[0:margs])


def robustApply(slot, arguments = ()):
    """Call slot with appropriate number of arguments"""
    if hasattr(slot, '__call__'):
        # Slot is a class instance ?
        if hasattr( slot.__call__, 'im_func'): # or hasattr( slot.__call__, 'im_code'): WARNING:im_code does not seem to exist?
            # Reassign slot to the actual method that will be called
            slot = slot.__call__

    if hasattr(slot, 'im_func'):
        # an instance method
        n_default_args = slot.im_func.func_defaults and len(slot.im_func.func_defaults) or 0
        n_args = slot.im_func.func_code.co_argcount - n_default_args - 1
    else:
        try:
            n_default_args = slot.func_defaults and len(slot.func_defaults) or 0
            n_args = slot.func_code.co_argcount - n_default_args
        except:
            raise SpecClientDispatcherError ('Unknown slot type %s %s' % (repr(slot), type(slot)))

    if len(arguments) < n_args:
        raise SpecClientDispatcherError( 'Not enough arguments for calling slot %s (need: %d, given: %d)' % (repr(slot), n_args, len(arguments)) )
    else:
        return slot(*arguments[0:n_args])

class Receiver:
    def __init__(self, weakReceiver, dispatchMode):
        self.weakReceiver = weakReceiver
        self.dispatchMode = dispatchMode


    def __call__(self, arguments):
        #slot = self.weakReceiver #get the strong reference
        slot = self.weakReceiver() #get the strong reference

        if slot is not None:
            log.log(DEBUG, "calling receiver slot %s" % slot)
            return robustApply2(slot, arguments)
            #return robustApply(slot, arguments)


class Event:
    def __init__(self, sender, signal, arguments):
        self.receivers = []
        senderId = id(sender)
        signal = str(signal)
        self.args = arguments

        log.log(DEBUG, " creating event for signal %s - senderId is %s" % (signal, senderId))
        try:
            self.receivers = connections[senderId][signal]
        except:
            pass


class EventsQueue(queue.Queue):
    def __init__(self):
        queue.Queue.__init__(self, 0)


    def get(self):
        """Remove and return an item from the queue."""
        #try:
        return queue.Queue.get(self, False)
        #except queue.Empty:
            #raise IndexError


    def put(self, event):
        """Put an event into the queue."""
        receiversList = event.receivers

        self.mutex.acquire()

        try:
            log.log(DEBUG,"adding event. receiversList is %s" % event.receivers)
            showstatus()
            was_empty = not self._qsize()

            for r in receiversList:
                if not was_empty:
                    if r.dispatchMode == UPDATEVALUE:
                        for i in range(len(self.queue)):
                            _r, args = self.queue[i]
                            if r == _r:
                                del self.queue[i]
                                break

                self._put( (r, event.args) )
        except:
            import traceback
            log.log(DEBUG,"could not add event to queue %s" % traceback.format_exc())
        finally:
            self.mutex.release()
        log.log(DEBUG,"adding event done")


eventsToDispatch = EventsQueue()
connections = {} # { senderId0: { signal0: [receiver0, ..., receiverN], signal1: [...], ... }, senderId1: ... }
senders = {} # { senderId: sender, ... }

def callableObjectRef(object):
    """Return a safe weak reference to a callable object"""
    return saferef.safe_ref(object, _removeReceiver)

def connect(sender, signal, slot, dispatchMode = UPDATEVALUE):
    if sender is None or signal is None:
        return

    if not callable(slot):
        return

    senderId = id(sender)
    signal = str(signal)
    signals = {}

    log.log(DEBUG,"connecting (%s) %s to %s - %s" % (str(sender), senderId, signal, signals))

    if senderId in connections:
        signals = connections[senderId]
    else:
        connections[senderId] = signals

    def remove(object, senderId=senderId):
        _removeSender(senderId)

    try:
        weakSender = weakref.ref(sender, remove)
        senders[senderId] = weakSender
    except:
        pass

    receivers = []

    if signal in signals:
        receivers = signals[signal]
    else:
        signals[signal] = receivers

    log.log(DEBUG, "connections are %s" % str(connections))
    weakReceiver = callableObjectRef(slot)
    #weakReceiver = slot

    for r in receivers:
        if r.weakReceiver == weakReceiver:
            r.dispatchMode = dispatchMode
            return

    receivers.append(Receiver(weakReceiver, dispatchMode))

def disconnect(sender, signal, slot):
    if sender is None or signal is None:
        return

    if not callable(slot):
        return

    senderId = id(sender)
    signal = str(signal)

    try:
        signals = connections[senderId]
    except KeyError:
        return
    else:
        try:
            receivers = signals[signal]
        except KeyError:
            return
        else:
            weakReceiver = callableObjectRef(slot)

            toDel = None
            for r in receivers:
                if r.weakReceiver == weakReceiver:
                    toDel = r
                    break

            if toDel is not None:
                receivers.remove(toDel)

                log.log(DEBUG, "cleaning up connections, because sender is removed %s" % senderId)
                _cleanupConnections(senderId, signal)
    
def showstatus():

    log.log(DEBUG,"status of connections is:")

    for i in connections.keys():
        try:
           name = senders[i]().name
           if name.startswith('motor'):
               continue
           log.log(DEBUG,"(1)  - %s " % senders[i]().name)
        except:
           log.log(DEBUG,"(2)  - %s " % str(senders[i]()))

def emit(sender, signal, arguments = ()):
    try:
        ev = Event(sender, signal, arguments)
        log.log(DEBUG, "adding event with signal \"%s\" to the queue %s" % (signal,ev))
        eventsToDispatch.put(ev)
        log.log(DEBUG,"is queue empty %s" % eventsToDispatch.empty())
    except:
        log.log(DEBUG,"failed adding event")
        import traceback
        log.log(DEBUG, traceback.format_exc())
    #if threading.current_thread() == MAIN_THREAD:
    #    dispatch(-1)


def dispatch(max_time_in_s=1):
    t0 = time.time()
    while True:
        try:
            if eventsToDispatch.empty():
                break
            log.log(DEBUG,"is queue empty %s" % eventsToDispatch.empty())
            receiver, args = eventsToDispatch.get()
        except queue.Empty:
            break
        except:
            log.log(1, "other exception while dispatching events")
            import traceback
            log.log(1, traceback.format_exc())
        else:
            log.log(DEBUG,"got a new event to dispatch with args %s" % str(args))
            receiver(args)
            if max_time_in_s < 0:
              continue
            elif (time.time()-t0) >= max_time_in_s:
              break


def _removeSender(senderId):
    try:
        del connections[senderId]
        del senders[senderId]
    except KeyError:
         pass


def _removeReceiver(weakReceiver):
    """Remove receiver from connections"""
    for senderId in list(connections.keys()):
        for signal in list(connections[senderId].keys()):
            receivers = connections[senderId][signal]

            for r in receivers:
                if r.weakReceiver == weakReceiver:
                    receivers.remove(r)
                    break

            log.log(DEBUG, "cleaning up connections, because receiver is removed")
            _cleanupConnections(senderId, signal)


def _cleanupConnections(senderId, signal):
    """Delete any empty signals for sender. Delete sender if empty."""

    receivers = connections[senderId][signal]

    log.log(DEBUG, "   number of receivers is %d" % len(receivers))

    if len(receivers) == 0:
        # no more receivers
        log.log(DEBUG, "   - deleting connection for %s" % senderId)
        signals = connections[senderId]
        del signals[signal]

        if len(signals) == 0:
            # no more signals
            _removeSender(senderId)


