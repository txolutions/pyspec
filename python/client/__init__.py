#  @(#)__init__.py	3.4  12/13/20 CSS
#  "pyspec" Release 3
#
#  

import sys
import os

from pyspec.css_logger import log

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

import sys

from SpecMotor import NOTINITIALIZED, UNUSABLE, READY, \
            MOVESTARTED, MOVING, ONLIMIT

import SpecMotor
import SpecCommand
import SpecVariable

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
    def connect_init(self, specapp, pname, *args, **kwargs):
        if isinstance(specapp, str) or (is_python2() and isinstance(specapp, unicode)):
             conn = spec(specapp)
        else:
             conn = specapp
        cls_init(self, conn, pname, *args, **kwargs)
    cls.__init__ = connect_init
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

@spec_connector
class variable(SpecVariable.SpecVariable):
    pass

@spec_connector
class variable_async(SpecVariable.SpecVariableA):
    pass

