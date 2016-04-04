#!/usr/bin/env python
#
# Copyright (C) 2016  Red Hat, Inc
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Library General Public License for more details.
#
# You should have received a copy of the GNU Library General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301  USA
"""
Source build and installation script.
"""

from setuptools import setup, find_packages


def extract_names(filename):
    names = ''
    with open(filename, 'r') as m:
        names = ', '.join([x.strip() for x in m.readlines()])
    return names


def extract_requirements(filename):
    with open(filename, 'r') as requirements_file:
        return [x[:-1] for x in requirements_file.readlines()]


install_requires = extract_requirements('requirements.txt')
test_require = extract_requirements('test-requirements.txt')


setup(
    name='commctl',
    version='0.0.1rc2',
    description='CLI for Commissaire',
    author=extract_names('CONTRIBUTORS'),
    maintainer=extract_names('MAINTAINERS'),
    url='https://github.com/projectatomic/commctl',
    license="LGPL2+",

    install_requires=install_requires,
    tests_require=test_require,
    package_dir={'': 'src'},
    packages=find_packages('src'),
    package_data={
        '': ['data/ansible/playbooks/*', 'data/templates/*'],
    },
    entry_points={
        'console_scripts': [
            'commissaire-hashpass = commctl.hash_pass_script:main',
            'commctl = commctl.client_script:main',
        ],
    }
)
