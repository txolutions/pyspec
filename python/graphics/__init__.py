#
#  %W%  %G% CSS
#  "pyspec" Release %R%
#

import sys
import os
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

from graphics_rc import g_rc

def qt_imported():
    return g_rc.qt_imported

def qt_variant():
    return g_rc.qt_variant

def qt_version():
    return g_rc.qt_version

def graph_variant():
    return g_rc.graph_variant

def mpl_imported():
    return g_rc.mpl_imported

def mpl_available():
    return g_rc.mpl_available

def mpl_version():
    return g_rc.mpl_version

def mpl_version_no():
    return g_rc.mpl_version_no

def qwt_imported():
    return g_rc.qwt_imported 

