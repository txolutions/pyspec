#
#  %W%  %G% CSS
#  "pyspec" Release %R%
#

"""

This is a simple python server that can be called from spec 
It allows to use numpy for calculating values on data

The servers exposes 

channels:
   - data  (set and get possible)

commands:
   - sum
   - average


In spec (after a scan, supposing we want to use data from "i0" counter)

  542.SPEC> prop_put("localhost:calcserv", "data", SCAN_D[0:NPTS-1][i0+1])

  543.SPEC> p remote_eval("localhost:calcserv","sum")
  766.2169967824616


"""

from pyspec.client.SpecServer import SpecServer
import numpy as np

class CalculatorServer(SpecServer):

    def __init__(self, *args, **kwargs):
        super(CalculatorServer,self).__init__(*args,**kwargs)
        self.nparr = None

        # channame: [ set_func, get_func ]

        self._channels = {
            'data': [self.set_data, self.get_data]
        }

        # cmdname: [ func, ]
        self._commands = {
            'sum': [self.calc_sum,],
            'average': [self.calc_aver,],
        }

        self.set_channels(self._channels)
        self.set_commands(self._commands)

    def set_data(self,data):
        self.nparr = np.array(data)
        return 0

    def get_data(self,data):
        return self.nparr

    def calc_aver(self):
        if self.nparr is None:
            return -1
        return self.nparr.mean()

    def calc_sum(self):
        if self.nparr is None:
            return -1
        return self.nparr.sum()

if __name__ == '__main__':
    srv = CalculatorServer(name='calcserv')
    srv.run()
