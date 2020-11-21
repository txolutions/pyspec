#
#  %W%  %G% CSS
#  "pyspec" Release %R%
#

from pyspec.client import motor, motor_async
from pyspec.graphics.QVariant import *
from pyspec.css_logger import log

class MotorWidget(QWidget):

    def __init__(self, specname, motormne, *args): 
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

        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(10)

        # need to define callbacks
        cb =  {"motorPositionChanged": self.position_changed,
               "motorStateChanged": self.state_changed}

        # create asyncronous motor
        self.motor = motor_async(self.specname, self.motormne, callbacks=cb)

    def do_move(self):
        target = self.position_ledit.text()
        # call move
        self.motor.move(float(target))

    def position_changed(self, value):
        self.position_ledit.setText(str(value))

    def state_changed(self, value):
        if value == 4:
            self.position_ledit.setStyleSheet("background-color: #e0e000")
        else:
            self.position_ledit.setStyleSheet("background-color: #c0ffc0")

    def update(self):
        self.motor.update()

def main():
    log.start()
    app = QApplication([])
    win = QMainWindow()
    motor = MotorWidget("fourc", "chi")

    win.setCentralWidget(motor)
    win.show()

    app.exec_()

if __name__ == '__main__':
    main()

