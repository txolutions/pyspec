#
#  @(#)example_qt_command.py	6.2  12/13/20 CSS
#  "pyspec" Release 6
#

from pyspec.client import command
from pyspec.graphics.QVariant import *

class CommandWidget(QWidget):

    def __init__(self, cmdname, specname, *args): 
        self.specname = specname
        QWidget.__init__(self, *args)

        layout = QVBoxLayout()
        self.setLayout(layout)
        self.cmd_button = QPushButton(cmdname) 
        self.cmd_button.clicked.connect(self.call_cmd)
        self._command = command(specname, cmdname)

        self.name_box = QHBoxLayout()
        self.label = QLabel("Your name:" ) 
        self.name_ledit = QLineEdit()
        self.say_button = QPushButton("Say Hello") 
        self.say_button.clicked.connect(self.do_say)

        ##  this would be the definition of a macro function 
        #   with args and return value
        self.hello_mac = """
          def hello(name) '{
             retstr = sprintf("Hello %s", name) 
             print retstr
             return retstr 
          }' 
        """
        self._defmac_cmd = command(specname, self.hello_mac)
        self._say_command = command(specname, "hello")

        self.name_box.addWidget(self.label)
        self.name_box.addWidget(self.name_ledit)
        self.name_box.addWidget(self.say_button)

        self.msg_label = QLabel()

        layout.addWidget( self.cmd_button )
        layout.addLayout( self.name_box )
        layout.addWidget( self.msg_label )

    def call_cmd(self):
        ret = self._command()
        print(ret)

    def do_say(self):
        name = str(self.name_ledit.text())
        self._defmac_cmd() 
        return_value = self._say_command(name)
        self.msg_label.setText(return_value)
         
def main():
    app = QApplication([])
    win = QMainWindow()
    var =  CommandWidget("wa", "localhost:fourc")

    win.setCentralWidget(var)
    win.show()

    app.exec_()

if __name__ == '__main__':
    main()

