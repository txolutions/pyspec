#******************************************************************************
#
#  @(#)QVariant.py	3.15  02/18/21 CSS
#
#  "pyspec" Release %R%
#
#  Copyright (c) 2013,2014,2015,2016,2017,2018,2020,2021
#  by Certified Scientific Software.
#  All rights reserved.
#
#  Permission is hereby granted, free of charge, to any person obtaining a
#  copy of this software ("pyspec") and associated documentation files (the
#  "Software"), to deal in the Software without restriction, including
#  without limitation the rights to use, copy, modify, merge, publish,
#  distribute, sublicense, and/or sell copies of the Software, and to
#  permit persons to whom the Software is furnished to do so, subject to
#  the following conditions:
#
#  The above copyright notice and this permission notice shall be included
#  in all copies or substantial portions of the Software.
#
#  Neither the name of the copyright holder nor the names of its contributors
#  may be used to endorse or promote products derived from this software
#  without specific prior written permission.
#
#     * The software is provided "as is", without warranty of any   *
#     * kind, express or implied, including but not limited to the  *
#     * warranties of merchantability, fitness for a particular     *
#     * purpose and noninfringement.  In no event shall the authors *
#     * or copyright holders be liable for any claim, damages or    *
#     * other liability, whether in an action of contract, tort     *
#     * or otherwise, arising from, out of or in connection with    *
#     * the software or the use of other dealings in the software.  *
#
#******************************************************************************


#
# File to load the Qt toolkit module
#   - it is possible to load qt4, qt5 or qtside with this module
#
#
# Choice method:
#
#   1.  command line flag
#       The following flags are recognided if provided in the command line
#         --pyside
#         --pyside2
#         --pyside6
#         --pyqt4
#         --pyqt5
#         --pyqt6
#         --matplotlib
#         --qwt
#
#   2.  QT_API  and GRAPH_LIB environment variables
#         If no flag is provided, the module will check the QT_API
#         environment variable for one of the following values
#            'pyside', 'pyside6', 'pyside2', 'pyqt4', 'pyqt5', 'pyqt6'
#
#         If no flag for graphics is provided, the module will check the GRAPH_API
#         environment variable for one of the following values
#            'matplotlib', 'qwt'
#
#         The environment variable setting is case-insensitive
#
#   3.  Try and fail
#         If no flag is provided and the QT_API and/or GRAPH_API environment 
#         variables are not set with any of the recognized values the module 
#         with try to import a possible compatible combination.
#

import sys
import os

from graphics_rc import g_rc

cmdline = False
varset = False

env_api = os.environ.get('QT_API', None)
env_graphics = os.environ.get('GRAPH_LIB', None)

if '--pyside' in sys.argv:
    g_rc.qt_variant = 'PySide'
    cmdline = True
elif '--pyside2' in sys.argv:
    g_rc.qt_variant = 'PySide2'
    cmdline = True
elif '--pyside6' in sys.argv:
    g_rc.qt_variant = 'PySide6'
    cmdline = True
elif '--pyqt4' in sys.argv:
    g_rc.qt_variant = 'PyQt4'
    cmdline = True
elif '--pyqt5' in sys.argv:
    g_rc.qt_variant = 'PyQt5'
    cmdline = True
elif '--pyqt6' in sys.argv:
    g_rc.qt_variant = 'PyQt6'
    cmdline = True
elif env_api is not None:
    if env_api.lower() == 'pyside':
        g_rc.qt_variant = 'PySide'
        varset = True
    elif env_api.lower() == 'pyside2':
        g_rc.qt_variant = 'PySide2'
        varset = True
    elif env_api.lower() == 'pyside6':
        g_rc.qt_variant = 'PySide6'
        varset = True
    elif env_api.lower() == 'pyqt4':
        g_rc.qt_variant = 'PyQt4'
        varset = True
    elif env_api.lower() == 'pyqt5':
        g_rc.qt_variant = 'PyQt5'
        varset = True
    elif env_api.lower() == 'pyqt6':
        g_rc.qt_variant = 'PyQt6'
        varset = True
    else:
        varset = None

if '--matplotlib' in sys.argv:
    g_rc.graph_variant = "matplotlib"
elif '--qwt' in sys.argv:
    g_rc.graph_variant = "qwt"
elif env_graphics is not None:
    if env_graphics.lower() == 'matplotlib':
        g_rc.graph_variant = "matplotlib"
    elif env_graphics.lower() == 'qwt':
        g_rc.graph_variant = "qwt"

user_selected = cmdline or varset

# decide whether importing qwt or matplotlib. default: matplotlib

def check_compatible():

    # returns 0 if incompatible

    if (not g_rc.qwt_imported) and (not g_rc.mpl_imported):
        return(False)

    elif g_rc.mpl_imported:
        if g_rc.qt_imported == False:
            print("qt is not imported")
            return(False)
        elif g_rc.qt_variant in ["PySide", "PySide2"]:
            if g_rc.mpl_version_no < [1,1,0]:
                return(False)
        elif g_rc.qt_variant in ["PyQt6", "PySide6"]:
            if g_rc.mpl_version_no < [2,0,1]:
                return(False)
        elif g_rc.qt_variant == "PyQt5":
            if g_rc.mpl_version_no < [1,4,1]:
                return(False)
        elif g_rc.qt_variant != "PyQt4":
            return(False)
    elif g_rc.qwt_imported and g_rc.qt_variant != "PyQt4":
        return(False)

    return(True)

def check(fix_wayland=False):
    compat = check_compatible() and 1 or 0

    # if imports ok try to figure out a buggy python3/PyQt5 installation 
    if compat:
        from subprocess import Popen, PIPE

        if sys.version_info[0] == 3:
            py_exec = 'python3'
        elif sys.version_info[1] > 6:
            py_exec = 'python2'
        else:
            py_exec = 'python'

        from pyspec import _pyspec_dir
        inst_path = os.path.join(_pyspec_dir,'..') 
        shell_command  = "%s -c" % py_exec
        shell_command += " 'import sys;sys.path.append(\"%s\");" % inst_path
        shell_command += " from pyspec.graphics.QVariant import QApplication; app=QApplication([])'"
        proc = Popen(shell_command, shell=True, stdout=PIPE, stderr=PIPE)
        out, err = proc.communicate()

        if fix_wayland and proc.returncode != 0:
            os.environ['QT_QPA_PLATFORM']='x11'
            proc = Popen(shell_command, shell=True, stdout=PIPE, stderr=PIPE)
            out, err = proc.communicate()

        if proc.returncode != 0:
            # if starting a qt application ends abnormally
            compat = -1



    return compat

def app_libraries():
    import pyspec
    if g_rc.mpl_imported:
         graph_string = "matplotlib %s" % g_rc.mpl_version
    elif g_rc.qwt_imported:
         graph_string = "qwt5" 
 
    qt_string = "%s %s" % (g_rc.qt_variant, ".".join(map(str, g_rc.qt_version)))
    py_vers = sys.version_info
    py_string = "%s.%s" % (py_vers[0], py_vers[1])
    pyspec_vers = pyspec.__version__

    return {"python": py_string, "qt": qt_string, 
            "graphics": graph_string, "pyspec": pyspec_vers}
    
def print_selection():
    if g_rc.mpl_imported:
        print("   Matplotlib selected / version %s (no=%s)" % (g_rc.mpl_version, g_rc.mpl_version_no))
    elif g_rc.qwt_imported:
        print("   Qwt selected ")
    else:
        print("   No graphics library found")

    if not g_rc.qt_imported:
        print("   QtVariant is %s (cannot import)" % g_rc.qt_variant)
    else:
        print("   QtVariant is %s / version %s" % (g_rc.qt_variant, ".".join(map(str,g_rc.qt_version))))

    if check_compatible():
        print("\nCOMPATIBLE\n")
    else:
        print("\nINCOMPATIBLE\n")

    print("To change the library selection you may want to use:")
    print("    -    command line options: ['--matplotlib','--qwt','--pyqt4','--pyqt5','--pyqt6','--pyside','--pyside2', '--pyside6']")
    print("    -    QT_API env. variable: ['pyqt4','pyside','pyside2', 'pyside6', 'pyqt5','pyqt6']")
    print("    - GRAPH_LIB env. variable: ['matplotlib','qwt']")

def debug_trace(obj):
    '''Set a tracepoint in the Python debugger that works with Qt'''

    import pdb

    if g_rc.qt_variant in ['PyQt4','PyQt5', 'PyQt6']:
       pyqtRemoveInputHook()

    pdb.set_trace()
 
#
#  MAIN importing.  
#    It cannot be done in a function as we want to do  
#         from <module> import *
#    not allowed inside a function
#

  # 
  # IMPORT Graphics
  # 
graphics_failed = False

  # matplotlib if selected by user
if g_rc.graph_variant == 'matplotlib':
    try:
        #from matplotlib import rcParams
        g_rc.mpl_available = True
    except:
        g_rc.mpl_available = False
        
    if not g_rc.mpl_available:
        graphics_failed = True

  # qwt if selected by user
if not graphics_failed and g_rc.graph_variant == 'qwt':
    if user_selected and g_rc.qt_variant != 'PyQt4':
        graphics_failed = True
    else:
        from qwt_import import *

    if not g_rc.qwt_imported:
        graphics_failed = True

  # matplotlib as default choice
if not graphics_failed and not g_rc.mpl_available and not g_rc.qwt_imported:
    try:
        #from matplotlib import rcParams
        g_rc.mpl_available = True
    except:
        g_rc.mpl_available = False
        

  # qwt as last choice
if not graphics_failed and not g_rc.mpl_available and not g_rc.qwt_imported:
    from qwt_import import *

if not g_rc.mpl_available and not g_rc.qwt_imported:
    graphics_failed = True

if graphics_failed:
    print("Cannot find a supported graphical library.")

# if qwt has been imported only pyqt4 is possible
if g_rc.qwt_imported:
    if g_rc.qt_variant is None or g_rc.qt_variant == "PyQt4":
        from PyQt4_import import * 
elif g_rc.mpl_available:
    # first check what to do if there is a user selection (cmdline or env-variable)
    if g_rc.qt_variant == "PyQt6": 
        from PyQt6_import import *
    if g_rc.qt_variant == "PySide6": 
        from PySide6_import import *
    if g_rc.qt_variant == "PyQt5": 
        from PyQt5_import import *
    elif g_rc.qt_variant == "PySide": 
        from PySide_import import *
    elif g_rc.qt_variant == "PySide2": 
        from PySide2_import import *
    elif g_rc.qt_variant == "PyQt4": 
        from PyQt4_import import * 
 
    if not g_rc.qt_imported: 
        if user_selected:
             print("Could not import selected Qt toolkit %s " % g_rc.qt_variant)
        else:
             # if there is still no qt try pyqt6 - pyqt5 - pyside2 - pyqt4 in that order
            from PyQt6_import import *
            if not g_rc.qt_imported:
                from PySide6_import import *
                if not g_rc.qt_imported:
                    from PyQt5_import import *
                    if not g_rc.qt_imported:
                        from PySide2_import import *
                        if not g_rc.qt_imported:
                            from PyQt4_import import * 
                            if not g_rc.qt_imported:
                                from PySide_import import *

    if g_rc.mpl_available:
        # now really import matplotlib with g_rc.qt_imported known
        from matplotlib_import import *
else:
    # if there is no graphics library imported. do not even try
    pass

if not g_rc.qt_imported:
    if not user_selected:
        print("Cannot find a supported Qt toolkit library.")
    else:
        print("Cannot import selected Qt toolkit library %s."  % g_rc.qt_variant)
    
if __name__ == '__main__':
   # If run standalone print selection
   if "check" in sys.argv:
       print( check() )
   else:
       print_selection()
else:
    if (not check_compatible()):
        print_selection()
        progname=os.path.basename(sys.argv[0])
        print( """
%s needs graphical libraries installed in your system.

%s can run in the following environment:
   - matplotlib version 1.4.1 or later together with PyQt5
   - matplotlib version 1.1 or later together with PySide 
   - matplotlib version 0.99 or later together with PyQt4 
   - pyqwt5 with pyqt4 

No compatible installation was found.

Make sure compatible graphical libraries are installed in your system.
""" % (progname, progname))
        raise ImportError
