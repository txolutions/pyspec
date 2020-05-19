#
#  %W%  %G% CSS
#  "pyspec" Release %R%
#

import sys
import os
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

class g_rc(object):
    qt_variant = None
    qt_version = None
    graph_variant = None

    qt_imported = False
    mpl_available = False
    mpl_imported = False
    qwt_imported = False

    mpl_version = None
    mpl_version_no = None
