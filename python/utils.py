#******************************************************************************
#
#  @(#)utils.py	6.3  12/13/20 CSS
#
#  "pyspec" Release 6
#
#  Copyright (c) 2017,2020
#  by Certified Scientific Software.
#  All rights reserved.
#
#  Permission is hereby granted, free of charge, to any person obtaining a
#  copy of this software ("pyspec") and associated documentation files (the
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

import sys
import platform
import os
import socket
import asyncore

def is_macos():
    return sys.platform == "darwin" 

def is_windows():
    return sys.platform == "win32" 

def is_unity():
    desktop_session = os.environ.get("DESKTOP_SESSION", None) 
    if desktop_session in ["ubuntu-2d", "ubuntu"]:
        return True
    else:
        return False

def is_remote_host(host):
    if host == 'localhost' or host is None:
         return False

    local_ip = socket.gethostbyname(socket.gethostname())
    host_ip = socket.gethostbyname(host)

    if local_ip == host_ip:
        return False
    else:
        return True

def is_python2():
    return sys.version_info[0]== 2

def is_python3():
    return sys.version_info[0] == 3

def is_centos8():
    import platform
    linux_dist = platform.linux_distribution()
    if linux_dist[0].lower().find('centos') != -1 and \
        linux_dist[1][0] == '8':
            return True
    else:
        return False

def async_loop(timeout=0.01, use_poll=True, count=None):
    """Start asyncore and scheduler loop.
    Use this as replacement of the original asyncore.loop() function.
    """
    if use_poll and hasattr(asyncore.select, 'poll'):
        poll_sock = asyncore.poll2
    else:
        poll_sock = asyncore.poll

    sockmap = asyncore.socket_map

    if count is None:
        while sockmap:
            poll_sock(timeout, sockmap)
    else:
        while sockmap and count > 0:
            poll_sock(timeout, sockmap)
            count -= 1

if __name__ == '__main__':
   print("MacOS: ", is_macos())
   print("Ubuntu Unity: ", is_unity())
   print("Windows: ", is_windows())
   print("Python 2: ", is_python2())
   print("Python 3: ", is_python3())

