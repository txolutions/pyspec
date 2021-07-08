#
#  %W%  %G% CSS
#  "pyspec" Release %R%
#

from pyspec.client import variable_async
from pyspec.css_logger import log

from pyspec.client.SpecConnection import QSpecConnection
from pyspec.graphics.QVariant import *

class VariableWidget(QWidget):

    def __init__(self, specname, varname, *args): 

        self.specname = specname
        self.varname = varname

        QWidget.__init__(self, *args)

        layout = QHBoxLayout()
        self.setLayout(layout)
        self.label = QLabel( self.varname )
        self.value_ledit = QLineEdit() 
        layout.addWidget( self.label )
        layout.addWidget( self.value_ledit )

        self.value_ledit.returnPressed.connect(self.do_setvar)

        self.conn = QSpecConnection(self.specname)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(10)

        callbacks = {'update': self.value_change}

        self.variable = variable_async(self.conn, "MYVAR", callbacks=callbacks)

    def do_setvar(self):
        target = self.value_ledit.text()
        self.variable.setValue(str(target))

    def value_change(self, value):
        print("new value is  ", value)
        self.value_ledit.setText(str(value))

    def update(self):
        self.conn.update()

def main():
    log.start()

    app = QApplication([])
    win = QMainWindow()
    var =  VariableWidget("fourc", "MYVAR")

    win.setCentralWidget(var)
    win.show()

    app.exec_()

if __name__ == '__main__':
    main()

