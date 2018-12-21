#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    setup.py
    ~~~~~~~~

    no description available

    :copyright: (c) 2018 by diamondman.
    :license: see LICENSE for more details.
"""

import codecs
import os
import re
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    """Taken from pypa pip setup.py:
    intentionally *not* adding an encoding option to open, See:
       https://github.com/pypa/virtualenv/issues/201#issuecomment-3145690
    """
    return codecs.open(os.path.join(here, *parts), 'r').read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")

setup(
    name='rompar',
    version=find_version("rompar", "__init__.py"),
    description='Masked ROM optical data extraction tool.',
    long_description=read('README.md'),
    classifiers=[
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)',
        'Topic :: Scientific/Engineering :: Image Recognition',
        'Topic :: System :: Hardware',
        ],
    author='John McMasters',
    author_email='JohnDMcMaster@gmail.com',
    url='https://github.com/SiliconAnalysis/rompar',
    packages=[
        'rompar',
        'rompar.qtui',
        ],
    package_data={'rompar.qtui': ['*.ui', '*.html', '*.txt']},
    entry_points={'console_scripts': [
        'romparqt = rompar.qtui.romparqtui:main',
    ]},
    platforms='any',
    license='LICENSE',
    install_requires=[
        'pep8>=1.5.7',
        'virtualenv>=1.11.6',
        'pyflakes>=0.8.1',
        'numpy>=1.13.3',
        'PyQt5>=5.11.3',
        ]
)
