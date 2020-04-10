
from pyspec.client.SpecVariable import SpecVariableA
from pyspec.client.SpecConnection import SpecConnection
from pyspec.graphics.QVariant import *

class VariableWidget(QWidget):

    def __init__(self, varname, specname, *args): 
        self.varname = varname
        self.specname = specname
        QWidget.__init__(self, *args)

        layout = QHBoxLayout()
        self.setLayout(layout)
        self.label = QLabel( self.varname )
        self.value_ledit = QLineEdit() 
        layout.addWidget( self.label )
        layout.addWidget( self.value_ledit )

        self.value_ledit.returnPressed.connect(self.do_setvar)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(10)

        callbacks = {'update': self.value_change}
        self.conn = SpecConnection(self.specname)
        self.variable = SpecVariableA(self.varname, self.conn, callbacks=callbacks)
        #self.variable = SpecVariableA(self.varname, self.specname, callbacks=callbacks)

    def do_setvar(self):
        target = self.value_ledit.text()
        print("setting %s to %s" % (self.varname, target))
        self.variable.setValue(str(target))

    def value_change(self, value):
        print("new value is  ", value)
        self.value_ledit.setText(str(value))

    def update(self):
        #self.variable.refresh()
        self.conn.update()

def main():
    app = QApplication([])
    win = QMainWindow()
    var =  VariableWidget("MYVAR", "localhost:fourc")

    win.setCentralWidget(var)
    win.show()

    app.exec_()

if __name__ == '__main__':
    main()

