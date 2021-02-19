#******************************************************************************
#
#  %W%  %G% CSS
#
#  "pyspec" Release %R%
#
#  Copyright (c) 2013,2014,2015,2016,2017,2018,2019,2020,2021
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

import os
from graphics_rc import g_rc

try:

    from PySide2.QtCore import Qt
    from PySide2.QtWidgets import QDialog, QVBoxLayout, QGridLayout, \
        QLabel, QComboBox, QHBoxLayout, QRadioButton, \
        QPushButton, QApplication, QColorDialog, QMainWindow, \
        QWidget, QTreeWidgetItem, QButtonGroup, QTreeWidget, \
        QListWidget, QListWidgetItem, QSplashScreen, \
        QSplitter,  QTabWidget, QMenuBar, QMessageBox, QSpacerItem,  \
        QLineEdit, QHeaderView, QSpinBox, QTextEdit, QTextBrowser,  \
        QMenu, QAction, QTabBar, QStackedWidget,  QFileDialog,  \
        QScrollArea, QProgressBar, QStyleOptionSlider, QGroupBox,  \
        QAbstractItemView, QSizePolicy, QFrame, QStyle, QScrollBar, QToolBar, \
        QDialogButtonBox, QToolButton, QCheckBox, QLayout, QInputDialog

    from PySide2.QtGui import QFont, QIcon, QFontMetrics, QPen, QColor, QPainter, \
        QPixmap, QBrush, QPainterPath , QDesktopServices 

    from PySide2.QtGui import QIntValidator, QRegExpValidator, QDoubleValidator, \
            QValidator

    from PySide2.QtCore import QObject, QTimer,  QProcess, QEvent, QSize, \
         QLine, QRect, QPoint, QRectF, QUrl, QUrlQuery, QCoreApplication, Signal

    from PySide2.QtPrintSupport import QPrinter, QPrintDialog

    from PySide2 import __version_info__

    pyqtSignal = Signal
    g_rc.qt_imported = True
    g_rc.qt_variant = 'PySide2'
    getQApp = QCoreApplication.instance
    g_rc.qt_version = __version_info__[:3]
except:
    pass


