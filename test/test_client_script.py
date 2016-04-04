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
Test cases for the commctl.client_script script.
"""

import sys

import contextlib
import mock
import requests

from . import TestCase, get_fixture_file_path
from commctl import client_script


class TestClientScript(TestCase):
    """
    Tests for the client_script.
    """

    def setUp(self):
        self.conf = get_fixture_file_path('test/commissaire.json')
        self.argv = sys.argv
        sys.argv = ['']

    def tearDown(self):
        sys.argv = self.argv

    def test_client_script_get(self):
        """
        Verify use cases for the client_script get command.
        """
        sys.argv = ['', 'get']
        with contextlib.nested(
                mock.patch('requests.Session.get'),
                mock.patch('os.path.realpath')) as (_get, _realpath):
            _realpath.return_value = self.conf
            for subcmd in ('cluster', 'restart', 'upgrade'):
                mock_return = requests.Response()
                mock_return._content = '{}'
                mock_return.status_code = 200
                _get.return_value = mock_return

                sys.argv[2:] = [subcmd, '-n test']
                print sys.argv
                client_script.main()
                self.assertEquals(1, _get.call_count)
                _get.reset_mock()

    def test_client_script_create(self):
        """
        Verify use cases for the client_script create command.
        """
        sys.argv = ['', 'create']
        with contextlib.nested(
                mock.patch('requests.Session.put'),
                mock.patch('os.path.realpath')) as (_put, _realpath):
            _realpath.return_value = self.conf
            for subcmd in (['cluster'], ['restart'], ['upgrade', '-u', '1']):
                mock_return = requests.Response()
                mock_return._content = '{}'
                mock_return.status_code = 201
                _put.return_value = mock_return

                sys.argv[2:] = subcmd + ['-n test']
                print sys.argv
                client_script.main()
                self.assertEquals(1, _put.call_count)
                _put.reset_mock()

    def test_client_script_list(self):
        """
        Verify use cases for the client_script list command.
        """
        sys.argv = ['', 'list']
        with contextlib.nested(
                mock.patch('requests.Session.get'),
                mock.patch('os.path.realpath')) as (_get, _realpath):
            _realpath.return_value = self.conf
            for subcmd, content in ((['clusters'], '[]'),
                                    (['hosts'], '{}'),
                                    (['hosts', '-n', 'test'], '[]')):
                mock_return = requests.Response()
                mock_return._content = content
                mock_return.status_code = 200
                _get.return_value = mock_return

                sys.argv[2:] = subcmd
                print sys.argv
                client_script.main()
                self.assertEquals(1, _get.call_count)
                _get.reset_mock()
