# Copyright (C) 2016-2017  Red Hat, Inc
#
# Copyright (C) 2016-2017  Red Hat, Inc
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
Unittests.
"""

import os
import unittest


def get_fixture_file_path(filename):
    """
    Attempts to return the path to a fixture file.

    :param filename: The name of the file to look for.
    :type filename: str
    :returns: Full path to the file
    :rtype: str
    :raises: Exception
    """
    for x in ('.', '..'):
        try:
            a_path = os.path.sep.join((x, filename))
            os.stat(a_path)
            return os.path.realpath(a_path)
        except:
            pass
    raise Exception(
        'Can not find path for config: {0}'.format(filename))


class TestCase(unittest.TestCase):
    """
    Parent class for all unittests.
    """
    pass
