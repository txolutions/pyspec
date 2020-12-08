#!/usr/bin/env python

#******************************************************************************
#
#  %W%  %G%0 CSS
#
#  "pyspec" Release %R%
#
#  Copyright (c) 2020
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


import os

with open('README.rst') as dfd:
    long_description = dfd.read()

try:
    from setuptools import setup, Extension, find_packages
    packages = find_packages(exclude=['python/graphics'])
except ImportError:
    # for python2 compatability
    from distutils.core import setup, Extension
    packages=['pyspec', 
        'pyspec/tools', 
        'pyspec/graphics',
        'pyspec/hardware',
        'pyspec/file', 
        'pyspec/client', 
        ]

install_requires = ['numpy']

datashm_dir = 'pyspec/datashm'
datashm_sources = ['datashm_py.c', 'sps.c']
datashm_sources = [os.path.join(datashm_dir, c_file) for c_file in datashm_sources]

datashm_ext = Extension('pyspec/datashm',
                    include_dirs = [datashm_dir],
                    sources = datashm_sources,)

#try:
from VERSION import getVersion
__version__ = getVersion()
#except:
    #__version__ = '1.1.10'

setup(name='certif_pyspec',
	version= __version__,
	description='Python SPEC modules and tools',
        download_url='https://pypi.org/projects/certif-pyspec/',
        long_description=long_description,
	author='TXOlutions',
	author_email='txo@txolutions.com',
        url='http://github.com/txolutions/pyspec',
        packages = packages,
 	ext_modules=[ datashm_ext ],
        install_requires = install_requires,
        scripts=['tools/specfile', 'tools/roi_selector']
)

