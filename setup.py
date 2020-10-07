
import os

try:
    from setuptools import setup, Extension, find_packages
    packages = find_packages()
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

setup(name='pyspec',
	version='1.0',
	description='Python SPEC modules and tools',
	author='TXOlutions',
	author_email='txo@txolutions.com',
        url='http://certif.com',
        packages = packages,
 	ext_modules=[ datashm_ext ],
        install_requires = install_requires,
        scripts=['tools/specfile', 'tools/roi_selector']
)

