#
#  %W%  %G% CSS
#  "pyspec" Release %R%
#

from pyspec.client.SpecConnection import SpecConnection
from pyspec.graphics.QVariant import *
from pyspec.css_logger import log, addStdOutHandler

addStdOutHandler()
log.setLevel(2)
log.log(2, "hello")

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

        self.conn = SpecConnection(specname)

        #self.timer = QTimer()
        #self.timer.timeout.connect(self.poll)
        #self.timer.start(10)

        self.conn.connect_event('connected', self.server_connected)
        self.conn.connect_event('disconnected', self.server_disconnected)

    def poll(self,timeout=0.01):
        self.conn.update()

    def abort_cmd(self):
        self.conn.abort()

    def server_connected(self):
        self.is_connected = True
        self.conn.registerChannel('status/ready', self.status_ready)
        self._update_status()

    def server_disconnected(self):
        self.is_connected = False
        self.conn.unregisterChannel('status/ready')
        self._update_status()

    def status_ready(self, value):
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

def main():
    app = QApplication([])
    win = QMainWindow()
    var =  StatusWidget("fourc")
    win.setCentralWidget(var)
    win.show()

    app.exec_()

if __name__ == '__main__':
    main()

