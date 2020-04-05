#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

import sys
from setuptools import setup, find_packages


TESTING = any(x in sys.argv for x in ["test", "pytest"])

requirements = ['numpy']

setup_requirements = []

setup(
    author="TXOlutions",
    author_email='txo@txolutions.com',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    description="spec CSS python interface",
    entry_points={
        'console_scripts': [
            'specfile = pyspec.specfile:main',
        ]
    },
    install_requires=requirements,
    license="MIT license",
    long_description="spec CSS python interface",
    include_package_data=True,
    keywords='spec',
    name='pyspec',
    packages=find_packages(include=['pyspec']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    extras_require=extras_requirements,
    url='https://certif.com',
    version='0.1.0',
    zip_safe=True
)
