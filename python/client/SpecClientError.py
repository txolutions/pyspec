#  @(#)SpecClientError.py	3.3  12/13/20 CSS
#  "pyspec" Release 3
#
#
# Exception class
#
class SpecClientError(Exception):

    errstr = "pyspec.client error"

    def __init__(self, error = None, err = None):
        Exception.__init__(self)

        self.error = error
        self.err = err

    def __str__(self):
        errstr = self.errstr

        if self.error: 
            errstr += ". " + str(self.error)
        if self.err: 
            errstr += ". " + str(self.err)

        return errstr

class SpecClientProtocolError(SpecClientError):
    errstr = "pyspec.client error (spec protocol problem)"

class SpecClientVersionError(SpecClientError):
    errstr = "pyspec.client error (wrong server version)"

class SpecClientTimeoutError(SpecClientError):
    errstr = "pyspec.client error (request timeout)"

class SpecClientNotConnectedError(SpecClientError):
    errstr = "pyspec.client error (no connection)"
