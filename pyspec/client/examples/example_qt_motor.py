from pyspec.client.SpecMotor import SpecMotorA

from PyQt4.QtGui import *
from PyQt4.QtCore import *

class MotorWidget(QWidget):

    def __init__(self, motormne, specname, *args): 
        self.motormne = motormne
        self.specname = specname
        QWidget.__init__(self, *args)

        layout = QHBoxLayout()
        self.setLayout(layout)
        self.label = QLabel( self.motormne )
        self.position_ledit = QLineEdit() 
        layout.addWidget( self.label )
        layout.addWidget( self.position_ledit )
        self.position_ledit.returnPressed.connect(self.do_move)

        # need to define callbacks
        cb =  {"motorPositionChanged": self.position_change,
               "motorStateChanged": self.state_change}

        # create asyncronous motor
        self.motor = SpecMotorA(self.motormne, self.specname, callbacks=cb)

    def do_move(self):
        target = self.position_ledit.text()
        print "moving %s to %s" % (self.motormne, target)
        # call move
        self.motor.move(float(target))

    def position_change(self, value):
        print "position is now ", value
        self.position_ledit.setText(str(value))

    def state_change(self, value):
        print "state is now ", value
        if value == 4:
            self.position_ledit.setStyleSheet("background-color: #e0e000")
        else:
            self.position_ledit.setStyleSheet("background-color: #c0ffc0")


# this function have to be called regularly to update spec events
def update_spec_events():
    from pyspec.client import SpecEventsDispatcher
    SpecEventsDispatcher.dispatch()

def main():
    app = QApplication([])
    win = QMainWindow()
    motor = MotorWidget("chi", "localhost:fourc")

    win.setCentralWidget(motor)
    win.show()

    timer = QTimer()
    timer.timeout.connect(update_spec_events)
    timer.start(10)

    app.exec_()

if __name__ == '__main__':
    main()

