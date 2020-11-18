#******************************************************************************
#
#  %W%  %G% CSS
#
#  "pyspec" Release %R%
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

if __name__ == '__main__':
   print("MacOS: ", is_macos())
   print("Ubuntu Unity: ", is_unity())
   print("Windows: ", is_windows())
   print("Python 2: ", is_python2())
   print("Python 3: ", is_python3())

