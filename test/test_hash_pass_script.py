# Copyright (C) 2016  Red Hat, Inc
#
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
Test cases for the commctl.hash_pass_script script.
"""

import contextlib
import sys

import mock

from . import TestCase
from commctl import hash_pass_script


class TestHashPassScript(TestCase):
    """
    Tests for the hash_pass_script.
    """

    def setUp(self):
        sys.argv = ['']

    def test_hash_pass_script_with_input(self):
        """
        Verify giving a password works with hash_pass_script.
        """
        sys.argv = ['']
        with contextlib.nested(
                mock.patch('getpass.getpass'),
                mock.patch('sys.stdout.write')) as (_gp, _out):
            _gp.return_value = 'test'
            hash_pass_script.main()
            self.assertEquals(1, _gp.call_count)
            self.assertEquals(1, _out.call_count)

    def test_hash_pass_script_with_stdin(self):
        """
        Verify giving a password via stdin works with hash_pass_script.
        """
        sys.argv += ['--pwfile', '-']
        with contextlib.nested(
                mock.patch('argparse.FileType'),
                mock.patch('sys.stdout.write')) as (_in, _out):
            _in()().readline.return_value = 'test\n'
            hash_pass_script.main()
            self.assertEquals(1, _out.call_count)
