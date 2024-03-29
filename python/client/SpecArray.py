#  @(#)SpecArray.py	3.4  05/11/20 CSS
#  "pyspec" Release 3
#

from pyspec.css_logger import log
from pyspec.utils import is_python3

import numpy

from numpy.version import version
npvers = tuple(map(int, version.split('.')))

(ARRAY_DOUBLE, ARRAY_FLOAT, ARRAY_LONG, ARRAY_ULONG, ARRAY_SHORT, \
 ARRAY_USHORT, ARRAY_CHAR, ARRAY_UCHAR, \
 ARRAY_STRING, ARRAY_NUMERIC) = (5,6,7,8,9,10,11,12,13,14)

(ARRAY_MIN, ARRAY_MAX) = (ARRAY_DOUBLE, ARRAY_STRING)

SPEC_TO_NUM = {
    ARRAY_CHAR   :  numpy.byte,
    ARRAY_UCHAR  :  numpy.ubyte,
    ARRAY_SHORT  :  numpy.short,
    ARRAY_USHORT :  numpy.ushort,
    ARRAY_LONG   :  numpy.int32,
    ARRAY_ULONG  :  numpy.uint32,
    ARRAY_FLOAT  :  numpy.float32,
    ARRAY_DOUBLE :  numpy.float64
}

NUM_TO_SPEC = {
    numpy.ubyte : ARRAY_CHAR,
    numpy.uint : ARRAY_ULONG,
    numpy.uint16 : ARRAY_USHORT,
    numpy.uint32 : ARRAY_ULONG,
    numpy.uint8 : ARRAY_CHAR,
    numpy.ushort : ARRAY_USHORT,
    numpy.short : ARRAY_SHORT,
    numpy.int32 : ARRAY_LONG,
    numpy.int8 : ARRAY_CHAR,
    numpy.float32 : ARRAY_FLOAT,
    numpy.float64 : ARRAY_DOUBLE
}

if npvers >= (1,24):
    NUM_TO_SPEC[float] = ARRAY_FLOAT
else:
    NUM_TO_SPEC[numpy.float] = ARRAY_FLOAT

class SpecArrayError(Exception):
    pass

def isArrayType(datatype):
    is_int = isinstance(datatype,int)
    return is_int and datatype >= ARRAY_MIN and datatype <= ARRAY_MAX

def SpecArray(data, datatype = ARRAY_CHAR, rows = 0, cols = 0):

    if isinstance(data, SpecArrayData):
        # create a SpecArrayData from a SpecArrayData ("copy" constructor)
        return SpecArrayData(data.data, data.type, data.shape)

    if datatype == ARRAY_STRING:
        # a list of strings
        newArray = filter(None, [x != chr(0) and x or None for x in data.split(chr(0))])
        return newArray
    else:
        newArray = None

    if isinstance(data,numpy.ndarray) :
        # convert from a Num* array to a SpecArrayData instance
        # (when you send)
        if len(data.shape) > 2:
            raise SpecArrayError("Spec arrays cannot have more than 2 dimensions")

        try:
            if type(data) == numpy.ndarray:
                numtype = data.dtype.type
                datatype = NUM_TO_SPEC[numtype]
            else:
                numtype = data.typecode()
                datatype = NUM_TO_SPEC[numtype]
        except KeyError:
            data = ''
            datatype = ARRAY_CHAR
            rows = 0
            cols = 0
            log.error("Numerical type '%s' not supported" , numtype)
        else:
            if len(data.shape) == 2:
                rows, cols = data.shape
            else:
                rows, cols = 1, data.shape[0]
            data = data.tostring()

        newArray = SpecArrayData(data, datatype, (rows, cols))
    else:
        # return a new Num* array from data
        # (when you receive)
        try:
            numtype = SPEC_TO_NUM[datatype]
        except:
            raise SpecArrayError('Invalid Spec array type')
        else:
            if is_python3(): 
                newArray = numpy.frombuffer(data, dtype=numtype)
            else:
                newArray = numpy.fromstring(data, dtype=numtype)

            if rows==1:
              newArray.shape = (cols, )
            else:
              newArray.shape = (rows, cols)

    return newArray


class SpecArrayData:
    def __init__(self, data, datatype, shape):
        self.data = data
        self.type = datatype
        self.shape = shape


    def tostring(self):
        return str(self.data)
