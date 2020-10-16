
import os

with open('README.rst') as dfd:
    long_description = dfd.read()

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

setup(name='certif_pyspec',
	version='1.0',
	description='Python SPEC modules and tools',
        download_url='https://github.com/txolutions/pyspec/archive/v1.0.tar.gz',
        long_description=long_description,
	author='TXOlutions',
	author_email='txo@txolutions.com',
        url='http://github.com/txolutions/pyspec',
        packages = packages,
 	ext_modules=[ datashm_ext ],
        install_requires = install_requires,
        scripts=['tools/specfile', 'tools/roi_selector']
)

