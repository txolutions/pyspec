#******************************************************************************
#
#  @(#)matplotlib_import.py	3.8  05/11/20 CSS
#
#  "pyspec" Release 3
#
#  Copyright (c) 2016,2017,2018,2020
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

from graphics_rc import g_rc

try:
    import matplotlib

    if g_rc.qt_variant == "PySide":
        matplotlib.use("Qt4Agg")
        from matplotlib import rcParams
        rcParams["backend.qt4"] = "PySide"
        import matplotlib.backends.backend_qt4agg as mpl_backend
    elif g_rc.qt_variant == "PySide2":
        matplotlib.use("Qt5Agg")
        #from matplotlib import rcParams
        #rcParams["backend.qt5"] = "PySide2"
        import matplotlib.backends.backend_qt5agg as mpl_backend
    elif g_rc.qt_variant in ["PyQt5", "PySide2"]:
        matplotlib.use("Qt5Agg")
        import matplotlib.backends.backend_qt5agg as mpl_backend
    else:
        matplotlib.use("Qt4Agg")
        import matplotlib.backends.backend_qt4agg as mpl_backend

    g_rc.mpl_imported = True
    g_rc.mpl_version = matplotlib.__version__
    version_parts = g_rc.mpl_version.split(".")
    mpl_major, mpl_minor = version_parts[:2]
    g_rc.mpl_version_no = [int(mpl_major), int(mpl_minor), 0]

    if len(version_parts) > 2:
       try:
           import re
           rel = version_parts[2]
           m = re.search("(?P<rel>\d+)", rel )
           if m:
               mrel = int(m.group('rel'))
               g_rc.mpl_version_no[2] = mrel
       except:
          pass

    g_rc.graph_variant = "matplotlib"

except:
    pass

