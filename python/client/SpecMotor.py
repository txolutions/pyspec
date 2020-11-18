#  %W%  %G% CSS
#  "pyspec" Release %R%
#
#$Id: SpecMotor.py,v 1.6 2005/02/08 13:17:21 guijarro Exp $
"""SpecMotor module

This module defines the classes for motor objects

Classes:
SpecMotor -- class representing a motor in Spec
SpecMotorA -- class representing a motor in Spec, to be used with a GUI
"""

__author__ = 'Matias Guijarro'
__version__ = '1.0'

import math

from pyspec.css_logger import log

from SpecConnection import SpecConnection
from SpecCommand import SpecCommandA
from SpecWaitObject import SpecWaitObject
from SpecEventsDispatcher import UPDATEVALUE, FIREEVENT, callableObjectRef

(NOTINITIALIZED, UNUSABLE, READY, MOVESTARTED, MOVING, ONLIMIT) = (0,1,2,3,4,5)
(NOLIMIT, LOWLIMIT, HIGHLIMIT) = (0,2,4)

class SpecMotor(object):
    def __init__(self, motormne, specapp): 

        log.log(2, "init SpecMotor mne=%s specapp=%s" % (motormne, specapp))

        if None in (motormne, specapp):
            self._conn_ok = False
            return

        if specapp and isinstance(specapp, str): 
            self._conn = SpecConnection(specapp)
        else:
            self._conn = specapp

        # check that is a valid connection
        try:
            self.specname = self._conn.get_specname()
            self._conn_ok = True
        except Exception as e:
            import traceback
            log.log(2, "SpecMotor (%s) cannot get a valid spec connection" % motormne)
            log.log(2, traceback.format_exc())
            self._conn_ok = False
            return

        self.motormne = motormne
        self.chan_prefix = "motor/%s/%%s" % motormne

        self._conn.connect_event('connected', self.spec_connected)
        self._conn.connect_event('disconnected', self.spec_disconnected)

        if self._conn.isSpecConnected():
            self.spec_connected()

    def update(self):
        self._conn.update()

    def spec_connected(self):
        pass

    def spec_disconnected(self):
        pass

    def read(self, chan_name):
        if not self._conn_ok:
            return

        c = self._conn.getChannel(self.chan_prefix % chan_name)
        return c.read()

    def write(self, chan_name, value):
        if not self._conn_ok:
            return

        c = self._conn.getChannel(self.chan_prefix % chan_name)
        c.write(value)
 
    def wait(self, chan_name, done_value):
        ch = self.chan_prefix % 'move_done'
        w = SpecWaitObject(self._conn)
        w.waitChannelUpdate(ch, waitValue = done_value) 

    def move(self, target_position):
        """Move the motor

        Block until the move is finished

        Arguments:
        absolutePosition -- position where to move the motor to
        """
        try:
            target = float(target_position)
        except ValueError:
            log.log(1, "Cannot move %s: position '%s' is not a number" % \
                    self.motormne, target_position)
            return

        self.start_move(target)
        self.wait_move_done()

    def move_relative(self, inc_position):
        try:
            target = float(inc_position)
            target = self.get_position() + inc_position
        except ValueError:
            log.log(1, "Cannot move relative %s: position '%s' is not a number" % \
                    self.motormne, inc_position)
            return

        self.start_move(target)
        self.wait_move_done()

    def start_move(self, target_position):
        self.write('start_one', target_position)

    def wait_move_done(self):
        self.wait('move_done', 0)

    def stop(self):
        """Stop the current motor

        Send an 'abort' message to the remote Spec
        """
        self._conn.abort()

    def get_position(self):
        """Return the current absolute position for the motor."""
        return self.read('position')

    def set_offset(self, offset):
        """Set the motor offset value"""
        self.write('offset', offset)

    def get_offset(self):
        return self.read('offset')

    def get_sign(self):
        return self.read('sign')

    def get_dial_position(self):
        return self.read('dial_position')

    def get_limits(self):
        """Return a (low limit, high limit) tuple in user units."""
        low_lim = self.read('low_limit')
        high_lim = self.read('high_limit')
        lims = [lim * self.get_sign() + self.get_offset() for lim in (low_lim, high_lim)]
        return (min(lims), max(lims))

    def unusable(self):
        return self.read('unusable')

    def low_limit_hit(self):
        return self.read('low_lim_hit')

    def high_limit_hit(self):
        return self.read('high_lim_hit')

    # backwards compatibility
    moveRelative = move_relative
    getPosition = get_position
    getDialPosition = get_dial_position
    getLimits = get_limits
    getSign = get_limits
    getOffset = get_offset
    setOffset = set_offset
    lowLimitHit = low_limit_hit
    highLimitHit = high_limit_hit
    getParameter = read
    setParameter = write

class SpecMotorA(SpecMotor):
    """SpecMotorA (asynchronous) class"""

    def __init__(self, motormne=None, specapp=None, callbacks={}):
        """Constructor

        Keyword arguments:
        motormne -- mnemonic of the motor 
        specapp -- '[host:]specapp' or existing SpecConnection object
        """
        self.state = NOTINITIALIZED

        self.limit = NOLIMIT
        self.limits = (None, None)

        self.__old_position = None

        # the callbacks listed below can be set directly using the 'callbacks' keyword argument ;
        # when the event occurs, the corresponding callback will be called automatically
        self.__callbacks = {
            'connected': None,
            'disconnected': None,
            'motorLimitsChanged': None,
            'motorPositionChanged': None,
            'motorStateChanged': None
        }

        SpecMotor.__init__(self,motormne,specapp)

        for cb_name in iter(self.__callbacks.keys()):
            if callable(callbacks.get(cb_name)):
                self.__callbacks[cb_name] = callableObjectRef(callbacks[cb_name])

    def spec_connected(self):
        """Private callback triggered by a 'connected' event from Spec."""
        #
        # register channels
        #
        self.register('low_limit', self._motorLimitsChanged)
        self.register('high_limit', self._motorLimitsChanged)
        self.register('position', self.__motorPositionChanged, mode = FIREEVENT)
        self.register( 'move_done', self.motorMoveDone, mode = FIREEVENT)
        self.register('high_lim_hit', self.__motorLimitHit)
        self.register('low_lim_hit', self.__motorLimitHit)
        self.register('sync_check', self.__syncQuestion)
        self.register('unusable', self.__motorUnusable)
        self.register('offset', self.motorOffsetChanged)
        self.register('sign', self.signChanged)

        self.update()
 
        try: 
            if self.__callbacks.get("connected"):
                cb = self.__callbacks["connected"]()
                if cb is not None:
                    cb()
        finally:
            self.connected()

    def register(self, channame, cb, mode=UPDATEVALUE):
        self._conn.registerChannel(self.chan_prefix % channame,  cb, dispatchMode=mode)

    def connected(self):
        """Callback triggered by a 'connected' event from Spec

        To be extended by derivated classes.
        """
        pass

    def spec_disconnected(self):
        """Private callback triggered by a 'disconnected' event from Spec

        Put the motor in NOTINITIALIZED state.
        """
        self.__changeMotorState(NOTINITIALIZED)

        try:
          if self.__callbacks.get("disconnected"):
            cb = self.__callbacks["disconnected"]()
            if cb is not None:
              cb()
        finally:
            self.disconnected()


    def disconnected(self):
        """Callback triggered by a 'disconnected' event from Spec

        To be extended by derivated classes.
        """
        pass

    def signChanged(self, sign):
        self._motorLimitsChanged()

    def motorOffsetChanged(self, offset):
        self._motorLimitsChanged()

    def _motorLimitsChanged(self):
        try:
          if self.__callbacks.get("motorLimitsChanged"):
            cb = self.__callbacks["motorLimitsChanged"]()
            if cb is not None:
              cb()
        finally:
           self.motorLimitsChanged()

    def motorLimitsChanged(self):
        """Callback triggered by a 'low_limit' or a 'high_limit' channel update,
        or when the sign or offset for motor changes

        To be extended by derivated classes.
        """
        pass

    def motorMoveDone(self, channelValue):
        """Callback triggered when motor starts or stops moving

        Change the motor state accordingly.

        Arguments:
        channelValue -- value of the channel
        """

        if channelValue:
            self.__changeMotorState(MOVING)
        elif self.state in (MOVING, MOVESTARTED,NOTINITIALIZED):
            self.__changeMotorState(READY)

    def __motorLimitHit(self, channelValue, channelName):
        """Private callback triggered by a 'low_lim_hit' or a 'high_lim_hit' channel update

        Update the motor state accordingly.

        Arguments:
        channelValue -- value of the channel
        channelName -- name of the channel (either 'low_lim_hit' or 'high_lim_hit')
        """
        if channelValue:
            if channelName.endswith('low_lim_hit'):
                self.limit = self.limit | LOWLIMIT
                self.__changeMotorState(ONLIMIT)
            else:
                self.limit = self.limit | HIGHLIMIT
                self.__changeMotorState(ONLIMIT)

    def __motorPositionChanged(self, absolutePosition):
        if self.__old_position is None:
           self.__old_position = absolutePosition
        else:
           if math.fabs(absolutePosition - self.__old_position) > 1E-6:
              self.__old_position = absolutePosition
           else:
              return
        try:
          if self.__callbacks.get("motorPositionChanged"):
            cb = self.__callbacks["motorPositionChanged"]()
            if cb is not None:
              cb(absolutePosition)
        finally:
          self.motorPositionChanged(absolutePosition)

    def motorPositionChanged(self, absolutePosition):
        """Callback triggered by a position channel update

        To be extended by derivated classes.

        Arguments:
        absolutePosition -- motor absolute position
        """
        pass

    def __syncQuestion(self, channelValue):
        """Callback triggered by a 'sync_check' channel update

        Call the self.syncQuestionAnswer method and reply to the sync question.

        Arguments:
        channelValue -- value of the channel
        """
        if type(channelValue) == type(''):
            steps = channelValue.split()
            specSteps = steps[0]
            controllerSteps = steps[1]

            a = self.syncQuestionAnswer(specSteps, controllerSteps)

            if a is not None:
                c = self._conn.getChannel(self.chan_prefix % 'sync_check')
                c.write(a)

    def syncQuestionAnswer(self, specSteps, controllerSteps):
        """Answer to the sync. question

        Return either '1' (YES) or '0' (NO)

        Arguments:
        specSteps -- steps measured by Spec
        controllerSteps -- steps indicated by the controller
        """
        pass

    def __motorUnusable(self, unusable):
        """Private callback triggered by a 'unusable' channel update

        Update the motor state accordingly

        Arguments:
        unusable -- value of the channel
        """
        if unusable:
            self.__changeMotorState(UNUSABLE)
        else:
            self.__changeMotorState(READY)


    def __changeMotorState(self, state):
        """Private method for changing the SpecMotor object's internal state

        Arguments:
        state -- the motor state
        """
        self.state = state

        try:
            if self.__callbacks.get("motorStateChanged"):
                cb = self.__callbacks["motorStateChanged"]()
                if cb is not None:
                    cb(state)
        finally:
            self.motorStateChanged(state)

    def motorStateChanged(self, state):
        """Callback to take into account a motor state update

        To be extended by derivated classes

        Arguments:
        state -- the motor state
        """
        pass

    def move(self, target_position):
        self.__changeMotorState(MOVESTARTED)
        super(SpecMotorA, self).move(target_position)

    def move_relative(self, inc_position):
        self.__changeMotorState(MOVESTARTED)
        super(SpecMotorA, self).move_relative(inc_position)

    def wait_move_done(self):
        pass

    def getState(self):
        """Return the current motor state."""
        return self.state

if __name__ == '__main__':
    mot = SpecMotor("chi", "fourc")
    print(mot.get_position())
    mot.end()
