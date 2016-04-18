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

import os
import sys

import contextlib
import mock
import requests
import bcrypt
import tempfile

from StringIO import StringIO

from . import TestCase, get_fixture_file_path
from commctl import client_script, cli


class TestClientScript(TestCase):
    """
    Tests for the client_script.
    """

    def setUp(self):
        """
        Runs before each test.
        """
        self.conf = get_fixture_file_path('test/commissaire.json')
        self.argv = sys.argv
        sys.argv = ['']

    def tearDown(self):
        """
        Runs after each test.
        """
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
            for subcmd in ('cluster', 'host', 'restart', 'upgrade'):
                mock_return = requests.Response()
                mock_return._content = '{}'
                mock_return.status_code = 200
                _get.return_value = mock_return

                sys.argv[2:] = [subcmd, 'test']
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
                mock.patch('os.path.realpath'),
                mock.patch('argparse.FileType.__call__',
                           mock.mock_open(read_data='1234567890'),
                           create=True)
                ) as (_put, _realpath, _filetype):
            _realpath.return_value = self.conf
            for subcmd in (
                    ['cluster'],
                    ['host', '-c', 'honeynut', '1.2.3.4'],
                    ['restart'],
                    ['upgrade', '-u', '1']):
                mock_return = requests.Response()
                mock_return._content = '{}'
                mock_return.status_code = 201
                _put.return_value = mock_return

                sys.argv[2:] = subcmd + ['test']
                print sys.argv
                client_script.main()
                self.assertEquals(1, _put.call_count)
                _put.reset_mock()

    def test_client_script_delete(self):
        """
        Verify use cases for the client_script delete command.
        """
        sys.argv = ['', 'delete']
        with contextlib.nested(
                mock.patch('requests.Session.delete'),
                mock.patch('os.path.realpath')) as (_delete, _realpath):
            _realpath.return_value = self.conf
            for subcmd in (['cluster'], ['host']):
                mock_return = requests.Response()
                mock_return._content = '{}'
                mock_return.status_code = 200
                _delete.return_value = mock_return

                sys.argv[2:] = subcmd + ['test']
                print sys.argv
                client_script.main()
                self.assertEquals(1, _delete.call_count)
                _delete.reset_mock()

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
                                    (['hosts'], '[]'),
                                    (['hosts', 'test'], '[]')):
                mock_return = requests.Response()
                mock_return._content = content
                mock_return.status_code = 200
                _get.return_value = mock_return

                sys.argv[2:] = subcmd
                client_script.main()
                self.assertEquals(1, _get.call_count)
                _get.reset_mock()

    def test_client_script_passhash_with_password(self):
        """
        Verify passhash works via --password
        """
        sys.argv = ['', 'create', 'passhash', '--password', 'mypass']
        with contextlib.nested(
                mock.patch('sys.stdout', new_callable=StringIO),
                mock.patch('os.path.realpath')) as (_out, _realpath):
            _realpath.return_value = self.conf
            client_script.main()
            hashed = _out.getvalue().strip()
            self.assertEquals(bcrypt.hashpw('mypass', hashed), hashed)

    def test_client_script_passhash_with_file(self):
        """
        Verify passhash works via --file
        """
        with open('pwdfile', 'w') as f:
            f.write("mypass");
        sys.argv = ['', 'create', 'passhash', '--file', 'pwdfile']
        with contextlib.nested(
                mock.patch('sys.stdout', new_callable=StringIO),
                mock.patch('os.path.realpath')) as (_out, _realpath):
            _realpath.return_value = self.conf
            client_script.main()
            os.remove('pwdfile')
            hashed = _out.getvalue().strip()
            self.assertEquals(bcrypt.hashpw('mypass', hashed), hashed)

    def test_client_script_passhash_with_stdin(self):
        """
        Verify passhash works via stdin
        """
        sys.argv = ['', 'create', 'passhash', '--file', '-']
        with contextlib.nested(
                mock.patch('sys.stdout', new_callable=StringIO),
                mock.patch('sys.stdin', StringIO("mypass")),
                mock.patch('os.path.realpath')) as (_out, _in, _realpath):
            _realpath.return_value = self.conf
            client_script.main()
            hashed = _out.getvalue().strip()
            self.assertEquals(bcrypt.hashpw('mypass', hashed), hashed)

    def test_client_script_passhash_with_prompt(self):
        """
        Verify passhash works via getpass prompt
        """
        sys.argv = ['', 'create', 'passhash']
        with contextlib.nested(
                mock.patch('sys.stdout', new_callable=StringIO),
                mock.patch('getpass.getpass'),
                mock.patch('os.path.realpath')) as (_out, _gp, _realpath):
            _realpath.return_value = self.conf
            _gp.return_value = 'mypass'
            client_script.main()
            hashed = _out.getvalue().strip()
            self.assertEquals(bcrypt.hashpw('mypass', hashed), hashed)

class TestMultiServerSession(TestCase):
    """
    Tests for the MultiServerSession class.
    """

    def test_request(self):
        """
        Verify requests attempt all servers provided.
        """
        with mock.patch('requests.Session.request') as _request:
            _request.side_effect = (
                requests.ConnectionError,
                requests.ConnectionError)
            mss = cli.MultiServerSession(
                ['http://127.0.0.1:8000', 'http://127.0.0.1:9000'])
            self.assertRaises(
                cli.NoMoreServersError,
                mss.get,
                '/test')
            self.assertEquals(2, _request.call_count)
