from SpecClient.SpecCommand import SpecCommand

from PyQt4.QtGui import *
from PyQt4.QtCore import *

import sys
sys.append('..')

class CommandWidget(QWidget):

    def __init__(self, cmdname, specname, *args): 
        self.specname = specname
        QWidget.__init__(self, *args)

        layout = QVBoxLayout()
        self.setLayout(layout)
        self.cmd_button = QPushButton(cmdname) 
        self.cmd_button.clicked.connect(self.call_cmd)
        self._command = SpecCommand(cmdname, self.specname)

        self.name_box = QHBoxLayout()
        self.label = QLabel("Your name:" ) 
        self.name_ledit = QLineEdit()
        self.say_button = QPushButton("Say Hello") 
        self.say_button.clicked.connect(self.do_say)

        ##  this would be the definition of a macro function 
        #   with args and return value
        # def hello(name) '{
        #    retstr = sprintf("Hello %s", name) 
        #    print retstr
        #    return retstr 
        # }' 
        self._say_command = SpecCommand("hello", self.specname)

        self.name_box.addWidget(self.label)
        self.name_box.addWidget(self.name_ledit)
        self.name_box.addWidget(self.say_button)

        self.msg_label = QLabel()

        layout.addWidget( self.cmd_button )
        layout.addLayout( self.name_box )
        layout.addWidget( self.msg_label )

    def call_cmd(self):
        ret = self._command()
        print ret

    def do_say(self):
        name = str(self.name_ledit.text())
        return_value = self._say_command(name)
        self.msg_label.setText(return_value)
         
def update_spec_events():
    from SpecClient import SpecEventsDispatcher
    SpecEventsDispatcher.dispatch()

def main():
    app = QApplication([])
    win = QMainWindow()
    var =  CommandWidget("wa", "localhost:fourc")

    win.setCentralWidget(var)
    win.show()

    timer = QTimer()
    timer.timeout.connect(update_spec_events)
    timer.start(10)

    app.exec_()

if __name__ == '__main__':
    main()

