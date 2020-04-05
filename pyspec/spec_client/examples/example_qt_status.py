from SpecClient.SpecConnectionsManager import SpecConnectionsManager
from SpecClient import SpecEventsDispatcher
from SpecClient.SpecCommand import SpecCommand

from PyQt4.QtGui import *
from PyQt4.QtCore import *

import sys
sys.path.append('..')

class StatusWidget(QWidget):

    def __init__(self, specname, *args): 
        self.specname = specname
        QWidget.__init__(self, *args)

        layout = QVBoxLayout()
        self.setLayout(layout)
        self.abort_button = QPushButton("Abort") 
        self.abort_button.clicked.connect(self.abort_cmd)
        self.status_value_label = QLabel()

        layout.addWidget( self.status_value_label )
        layout.addWidget( self.abort_button )

        self.is_connected = False
        self.ready = False

        self._update_status()

        self.conn = SpecConnectionsManager().getConnection(specname)

        SpecEventsDispatcher.connect(self.conn, 'connected', self.server_connected)
        SpecEventsDispatcher.connect(self.conn, 'disconnected', self.server_disconnected)

    def abort_cmd(self):
        self.conn.abort()

    def server_connected(self):
        print self.specname + " is now connected"
        self.is_connected = True
        self.conn.registerChannel('status/ready', self.status_ready,
                                         dispatchMode=SpecEventsDispatcher.UPDATEVALUE)
        self._update_status()
        SpecCommand("print ",self.specname)()

    def server_disconnected(self):
        print self.specname + " is now disconnected"
        self.is_connected = False
        self.conn.unregisterChannel('status/ready')
        self._update_status()

    def status_ready(self, value):
        print "  - Ready is ", value
        self.ready = value
        self._update_status()
     
    def _update_status(self):
        connected = self.is_connected and "ON" or "OFF"
        busy = self.ready and "READY" or "BUSY"
        status_str = "%s<br> <b>%s</b> %s" % (self.specname,connected, busy)

        executing = False
        if not self.is_connected:
            color = '#a0a0a0'
        else:
            if self.ready:
                color = '#a0e0a0'
            else:
                color = '#d0d0a0'
                executing = True

        self.status_value_label.setText(status_str)
        self.status_value_label.setStyleSheet("background-color: %s" % color)

        if executing:
             self.abort_button.setEnabled(True)
             self.abort_button.setStyleSheet('background-color: #e0a0a0')
        else:
             self.abort_button.setEnabled(False)
             self.abort_button.setStyleSheet('background-color: #a0a0a0')

def update_spec_events():
    from SpecClient import SpecEventsDispatcher
    SpecEventsDispatcher.dispatch()

def main():
    app = QApplication([])
    win = QMainWindow()
    var =  StatusWidget("localhost:fourc")

    win.setCentralWidget(var)
    win.show()

    timer = QTimer()
    timer.timeout.connect(update_spec_events)
    timer.start(10)

    app.exec_()

if __name__ == '__main__':
    main()

