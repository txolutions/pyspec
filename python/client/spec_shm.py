#******************************************************************************
#
#  @(#)spec_shm.py	6.1  11/02/20 CSS
#
#  "splot" Release 6
#
#  Copyright (c) 2020
#  by Certified Scientific Software.
#  All rights reserved.
#
#  Permission is hereby granted, free of charge, to any person obtaining a
#  copy of this software ("splot") and associated documentation files (the
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

import time

from pyspec.css_logger import log

from pyspec import datashm

# provide through this module all functionalities of datashm
from pyspec.datashm import getdata, getspeclist
from pyspec.datashm import getinfo, getdatacol, getdatarow
from pyspec.datashm import getarrayinfo, getarraylist
from pyspec.datashm import getmetadata

class _UpdateTable(object):

    def __init__(self):
        self.created = time.time()
        self._update = {}

    def isupdated(self, spec, var, client):
        if client not in self._update:
            self._update[client] = {}
        if spec not in self._update[client]:
            self._update[client][spec] = {}
        if var not in self._update[client][spec]:
            self._update[client][spec][var] = True

        if datashm.isupdated(spec, var):
            for clnt in self._update:
                try:
                    self._update[clnt][spec][var] = True
                except:
                    pass

        retval = self._update[client][spec][var]
        self._update[client][spec][var] = False
        return retval

class UpdateTable(_UpdateTable):

    def __new__(cls):
        if not hasattr(cls, '_inst'):
            cls._inst = super(UpdateTable, cls).__new__(cls)
        else:
            def init_pass(self, *dt, **mp): pass
            cls.__init__ = init_pass

        return cls._inst

global utbl
utbl = UpdateTable()

def is_updated(spec, var, client):
    return utbl.isupdated(spec, var, client)
