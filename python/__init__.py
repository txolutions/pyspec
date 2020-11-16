#
#  %W%  %G% CSS
#  "pyspec" Release %R%
#

import sys
import os

_pyspec_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(_pyspec_dir)

from VERSION import getVersion, getFullVersion

__version__ = getVersion()
__fullversion__ = getFullVersion()

