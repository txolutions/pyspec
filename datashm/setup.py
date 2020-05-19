#!/usr/bin/env python

#******************************************************************************
#
#  %W%  %G% CSS
#
#  "pyspec" Release %R%
#
#  Copyright (c) 2012,2013,2014,2015,2016,2020
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

"""Setup script for the datashm module distribution."""

import os, sys

import platform
from distutils.core import setup
from distutils.extension import Extension
from distutils.fancy_getopt import FancyGetopt

# Parse options for specsrc
lopt = 'specsrc='; sopt = 'z'
idopt = 'prefix='; isopt = 'd'
ldopt = 'install-lib='; lsopt = 'i'

opts = [( lopt, sopt,'location of spec sources'), (ldopt,lsopt, 'installation directory'), (idopt,isopt, 'installation directory')]
args, options = FancyGetopt(opts).getopt()

specsrc = "../.." # default value for specsrc

# if SPECSRC in environment use that 
if "SPECSRC" in os.environ:
  specsrc = os.environ["SPECSRC"]

# Assing specsrc if it is in option list 
# then leave a clean sys.argv for distutils
try:
  specsrc = options.specsrc
  lopt = '--%s%s' % (lopt, specsrc)
  sopt = '-%s' % sopt
  if lopt in sys.argv:
     sys.argv.remove( lopt )
  elif sopt in sys.argv:
     sys.argv.remove( sopt )
     sys.argv.remove( specsrc )
except:
  pass

print( "Compiling datashm python module - Using sps.c source from", specsrc )

if platform.system() == 'Darwin' :
    # ALL default compiler / linker options come from _sysconfigdata

    from distutils.sysconfig import get_config_vars
    get_config_vars("CFLAGS")  # need to call get_config_vars once to populate _config_vars
    from distutils.sysconfig import _config_vars
    # 'CCSHARED': '-arch x86_64 -arch i386 -pipe',
    _config_vars['CCSHARED']='-arch x86_64 -pipe'
    # 'LDSHARED': 'cc -bundle -undefined dynamic_lookup -arch x86_64 -arch i386 -Wl,-F.',
    _config_vars['LDSHARED']='/usr/bin/clang -bundle -undefined dynamic_lookup -arch x86_64 -Wl,-F.'
    #_config_vars.build_time_vars['OPT']='-DNDEBUG -g -fwrapv -Os -Wall -Wstrict-prototypes'
    _config_vars['OPT']='-DNDEBUG -g -fwrapv -Os -Wall -Wstrict-prototypes'

    from os import environ

    environ['CFLAGS'] = '-Qunused-arguments'   #  appended to CFLAGS or CCSHARED
    #environ['BASECFLAGS'] = ''
    #environ['OPT'] = ''

    # from os import environ
    # macver  = platform.mac_ver()[0]
    # macvers = macver.split(".")

    # for 10.9 Mavericks (and later). Maybe it works for all versions
    #if macvers[0] >= 10 and macvers[1] >=9:
    #    environ['CFLAGS'] = '-Qunused-arguments'
    extra_compile_args = ['-w'] # disable all diagnostics for clang
else:  # Linux
    extra_compile_args = ['-pthread'] # enable multithreading

setup (
        name         = "datashm",
        version      = "1.0",
	description  = "spec shared data access",
        author       = "CSS",
        author_email = "txo@txolutions.com",
        url          = "http://www.certif.com",

        ext_modules  = [( 
            Extension( name = 'datashm',
                sources=[ os.path.join(specsrc,'sps.c'), 'datashm_py.c'],
                extra_compile_args = extra_compile_args,
                include_dirs  = [ specsrc, ]
            )
        ),]
)
