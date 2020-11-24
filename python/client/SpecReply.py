#  %W%  %G% CSS
#  "pyspec" Release %R%
#
#$Id: SpecReply.py,v 1.1 2004/08/23 11:16:09 guijarro Exp $
"""SpecReply module

This module defines the SpecReply class
"""
import SpecEventsDispatcher as SpecEventsDispatcher

from pyspec.css_logger import log

REPLY_ID_LIMIT = 2**30
current_id = 0

def next_id():
    global current_id
    current_id = (current_id + 1) % REPLY_ID_LIMIT
    return current_id

class SpecReply(object):
    """SpecReply class

    Represent a reply received from a remote Spec server

    Signals:
    replyFromSpec(self) -- emitted on update
    """
    def __init__(self):
        """Constructor."""
        self.data = None
        self.error = False
        self.error_code = 0 #no error
        self.id = next_id()
        self.pending = True

    def update(self, data, error, error_code):
        """Emit the 'replyFromSpec' signal."""

        self.data = data
        self.error = error
        self.error_code = error_code

        self.pending = False
        SpecEventsDispatcher.emit(self, 'replyFromSpec', (self, ))

    def is_pending(self):
        return self.pending

    def get_data(self):
        """Return the value of the reply object (data field)."""
        return self.data
