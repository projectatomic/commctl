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
Test cases for the commctl.client_script script.

.. note:: The use of \ in the with/mock blocks is required for readability.
          Unfortunately, ()'s for multiline statements do not work with
          the with structure in 2.7.
"""
import argparse
import json
import socket

import six

if six.PY2:
    import mock
else:
    from unittest import mock

from . import TestCase, get_fixture_file_path
from commctl import cli


class TestCliHostAddress(TestCase):
    """
    Tests for cli.host_address function.
    """

    def test_host_address(self):
        """
        Verify host_address resolves to a host name.
        """
        with mock.patch('socket.gethostbyname') as _ghn:
            _ghn.return_value = 'example.org'
            result = cli.host_address('192.168.0.1')

            self.assertEquals(
                result,
                _ghn.return_value)

    def test_host_address_unable_to_resolve(self):
        """
        Verify host_address raises on failed resolves.
        """
        with mock.patch('socket.gethostbyname') as _ghn:
            _ghn.side_effect = socket.gaierror('test')
            self.assertRaises(
                argparse.ArgumentTypeError,
                cli.host_address,
                '192.168.0.1')


class TestCliAssembleOptions(TestCase):
    """
    Tests for cli.assemble_options function.
    """

    def test_assemble_options_with_equals(self):
        """
        Verify assemble_options works with ['a=b',...].
        """
        data = ['a=b', 'c=d']
        expected = {'a': 'b', 'c': 'd'}
        self.assertEquals(
            cli.assemble_options(data),
            expected)

    def test_assemble_options_with_list_of_json(self):
        """
        Verify assemble_options works with list of json.
        """
        expected = {'a': 'b', 'c': 'd'}
        self.assertEquals(
            cli.assemble_options([json.dumps(expected)]),
            expected)

    def test_assemble_options_with_bad_json_data(self):
        """
        Verify assemble_options fails when bad json data is provided.
        """
        # The input data must be a list of one or more serialize dicts.
        # Here we pass in variations that do not match what is expected.
        for tc in (
                True,
                None,
                [{'a': 'b'}],
            ):
            self.assertRaises(
                TypeError,
                cli.assemble_options, 
                [json.dumps(tc)])
