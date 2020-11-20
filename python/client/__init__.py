#  %W%  %G% CSS
#  "pyspec" Release %R%
#
#  

import sys
import os
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

__all__ = [
    'saferef.py',
    'Spec.py',
    'SpecArray.py',
    'SpecChannel.py',
    'SpecClientError.py',
    'SpecCommand.py',
    'SpecConnection.py',
    'SpecConnectionsManager.py',
    'SpecCounter.py',
    'SpecEventsDispatcher.py',
    'SpecMessage.py',
    'SpecMotor.py',
    'SpecReply.py',
    'SpecScan.py'
    'SpecServer.py',
    'SpecVariable.py',
    'SpecWaitObject.py',
    ]


from SpecConnection import SpecConnection
spec = SpecConnection

import SpecMotor
import SpecCommand

import sys

from SpecMotor import NOTINITIALIZED, UNUSABLE, READY, \
            MOVESTARTED, MOVING, ONLIMIT

def is_python2():
    return sys.version_info[0] == 2

# Use as a decorator to override __init__  for classes
#    - checks the connection parameter and, if it is a string, opens
#    - the corresponding connection
#
#    This allows user classes to use either a string to specify the spec application
#    or an already existing connection


def spec_connector(cls):
    cls_init = cls.__init__
    def connect_init(self, specapp, command, *args, **kwargs):
        if isinstance(specapp, str) or (is_python2() and isinstance(specapp, unicode)):
             conn = SpecConnection(specapp)
        else:
             conn = specapp
        cls_init(self, conn, command, *args, **kwargs)

    cls.__init__ == connect_init
    return cls

@spec_connector
class motor(SpecMotor.SpecMotor):
    pass

@spec_connector
class motor_async(SpecMotor.SpecMotorA):
    pass

@spec_connector
class command(SpecCommand.SpecCommand):
    pass

@spec_connector
class command_async(SpecCommand.SpecCommandA):
    pass

