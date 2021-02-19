#******************************************************************************
#
#  %W%  %G% CSS
#
#  "pyspec" Release %R%
#
#  Copyright (c) 2013,2014,2015,2016,2017,2019,2020,2021
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
import os

try:
    from PyQt4.QtCore import Qt

    from PyQt4.QtGui import QDialog, QVBoxLayout, QGridLayout, \
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

    from PyQt4.QtGui import QFont, QIcon, QFontMetrics, QPen, QColor, QPainter, \
        QPixmap, QBrush, QPainterPath , QDesktopServices

    from PyQt4.QtGui import QIntValidator, QRegExpValidator, QDoubleValidator, \
            QValidator

    from PyQt4.QtCore import QObject, QTimer,  QProcess, QEvent, QSize, \
            QLine, QRect, QPoint, QRectF, QUrl, QCoreApplication, \
            pyqtSignal

    from PyQt4.QtGui import QPrinter, QPrintDialog, qApp
    from PyQt4.QtCore import QT_VERSION_STR

    def getQApp():
        return qApp
    g_rc.qt_imported = True
    g_rc.qt_variant = 'PyQt4'
    g_rc.qt_version = map(int, QT_VERSION_STR.split("."))
except:
    pass


