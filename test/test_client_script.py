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

import os
import sys

import requests
import bcrypt
import tempfile
import six

if six.PY2:
    import mock
else:
    from unittest import mock

from . import TestCase, get_fixture_file_path
from commctl import client_script, cli


class TestClientScript(TestCase):
    """
    Tests for the client_script.
    """

    def debug_exit(self, status=0, message=None):
        """
        Override to keep ArgumentParser.exit() from throwing a SystemExit.
        """
        import traceback
        traceback.print_exc(file=sys.stdout)

    def setUp(self):
        """
        Runs before each test.
        """
        self.conf = get_fixture_file_path('test/commissaire.json')
        self.argv = sys.argv
        sys.argv = ['']

        patcher = mock.patch(
            'argparse.ArgumentParser.exit', self.debug_exit)
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        """
        Runs after each test.
        """
        sys.argv = self.argv

    def test_client_script_get(self):
        """
        Verify use cases for the client_script get requests.
        """
        sys.argv = ['']
        with mock.patch('requests.Session.get') as _get, \
                mock.patch('os.path.realpath') as _realpath:
            _realpath.return_value = self.conf
            for cmd, content in (
                    (['cluster', 'get', 'test'], '{}'),
                    (['cluster', 'list'], '[]'),
                    (['cluster', 'restart', 'status', 'test'], '{}'),
                    (['cluster', 'upgrade', 'status', 'test'], '{}'),
                    (['cluster', 'restart', 'status', 'test'], '{}'),
                    (['container_manager', 'get', 'test'], '{}'),
                    (['container_manager', 'list'], '[]'),
                    (['host', 'get', 'localhost'], '{}'),
                    (['host', 'list'], '[]'),
                    (['host', 'list', 'test'], '[]'),
                    (['host', 'status', 'localhost'], '{}'),
                    (['network', 'get', 'test'], '{}'),
                    (['network', 'list'], '[]'),
                    ):
                mock_return = requests.Response()
                mock_return._content = six.b(content)
                mock_return.status_code = 200
                _get.return_value = mock_return

                sys.argv[1:] = cmd
                print(sys.argv)
                client_script.main()
                self.assertEquals(1, _get.call_count)
                _get.reset_mock()

    def test_client_script_put(self):
        """
        Verify use cases for the client_script put requests.
        """
        sys.argv = ['']
        read_data = six.b('1234567890')
        with mock.patch('requests.Session.put') as _put, \
                mock.patch('os.path.realpath') as _realpath, \
                mock.patch(
                    'argparse.FileType.__call__',
                    mock.mock_open(read_data=read_data),
                    create=True) as _filetype:
            _realpath.return_value = self.conf
            for cmd in (
                    ['cluster', 'create'],
                    ['cluster', 'create', '-n', 'default'],
                    ['cluster', 'create', '-t', 'kubernetes'],
                    ['cluster', 'create', '-t', 'kubernetes', '-n', 'default'],
                    ['cluster', 'deploy', 'start'],
                    ['cluster', 'restart', 'start'],
                    ['cluster', 'upgrade', 'start'],
                    ['container_manager', 'create'],
                    ['container_manager', 'create', '-o', '{}'],
                    ['container_manager', 'create'],
                    ['host', 'create', '-c', 'honeynut', '1.2.3.4'],
                    ['host', 'join', '1.2.3.4'],
                    ['network', 'create', '-n', 'test']):
                mock_return = requests.Response()
                mock_return._content = six.b('{}')
                mock_return.status_code = 201
                mock_return.request = mock.MagicMock(path_url='/fake/path')
                _put.return_value = mock_return

                sys.argv[1:] = cmd + ['test']
                if cmd[1] == 'deploy':
                    sys.argv.append('1')  # arbitrary version
                print(sys.argv)
                client_script.main()
                self.assertEquals(1, _put.call_count)
                _put.reset_mock()

    def test_client_script_delete(self):
        """
        Verify use cases for the client_script delete requests.
        """
        sys.argv = ['', 'delete']
        with mock.patch('requests.Session.delete') as _delete, \
                mock.patch('os.path.realpath') as  _realpath:
            _realpath.return_value = self.conf
            for cmd in (
                    ['cluster', 'delete', 'test'],
                    ['cluster', 'delete', 'test1', 'test2'],
                    ['container_manager', 'delete', 'test'],
                    ['container_manager', 'delete', 'test', 'test2'],
                    ['host', 'delete', 'localhost'],
                    ['host', 'delete', '10.0.0.1', '10.0.0.2', '10.0.0.3'],
                    ['host', 'unjoin', '1.2.3.4', 'honeynut'],
                    ['network', 'delete', 'test'],
                    ['network', 'delete', 'test', 'test2', 'test3']):
                mock_return = requests.Response()
                mock_return._content = six.b('{}')
                mock_return.status_code = 200
                _delete.return_value = mock_return

                sys.argv[1:] = cmd
                print(sys.argv)
                client_script.main()
                if cmd[1] == 'unjoin':
                    num_things = 1
                else:
                    num_things = len(cmd) - 2
                self.assertEquals(num_things, _delete.call_count)
                _delete.reset_mock()

    def test_client_script_host_ssh(self):
        """
        Verify use cases for the client_script ssh requests.
        """
        sys.argv = ['', 'host', 'ssh']
        with mock.patch('requests.Session.get') as _get, \
                mock.patch('os.path.realpath') as _realpath, \
                mock.patch('subprocess.call') as _call, \
                mock.patch('tempfile.mkstemp') as _mkstemp, \
                mock.patch('os.close') as _close:
            _realpath.return_value = self.conf
            _mkstemp.return_value = (1, '/tmp/test_key_file')
            for cmd in (
                    ['127.0.0.1'],
                    ['127.0.0.1', '-p 22'],
                    ['127.0.0.1', '-p 22 -v']):
                content = six.b(
                    '{"ssh_priv_key": "dGVzdAo=", "remote_user": "root"}')
                mock_return = requests.Response()
                mock_return._content = content
                mock_return.status_code = 200
                _get.return_value = mock_return

                sys.argv[3:] = cmd
                expected = 'ssh -i /tmp/test_key_file -l root {0} {1}'.format(
                    ' '.join(cmd[1:]), cmd[0])
                print(sys.argv)
                client_script.main()
                _get.assert_called_once_with(mock.ANY)
                _call.assert_called_once_with(expected, shell=True)
                _call.reset_mock()
                _get.reset_mock()

    def test_client_script_passhash_with_password(self):
        """
        Verify passhash works via --password
        """
        sys.argv = ['', 'passhash', '--password', 'mypass']
        with mock.patch('sys.stdout', new_callable=six.StringIO) as _out, \
                mock.patch('os.path.realpath') as _realpath:
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
        sys.argv = ['', 'passhash', '--file', 'pwdfile']
        with mock.patch('sys.stdout', new_callable=six.StringIO) as _out, \
                mock.patch('os.path.realpath') as _realpath:
            _realpath.return_value = self.conf
            client_script.main()
            os.remove('pwdfile')
            hashed = _out.getvalue().strip()
            self.assertEquals(bcrypt.hashpw('mypass', hashed), hashed)

    def test_client_script_passhash_with_stdin(self):
        """
        Verify passhash works via stdin
        """
        sys.argv = ['', 'passhash', '--file', '-']
        with mock.patch('sys.stdout', new_callable=six.StringIO) as _out, \
                 mock.patch('sys.stdin', six.StringIO("mypass")) as _in, \
                 mock.patch('os.path.realpath') as _realpath:
            _realpath.return_value = self.conf
            client_script.main()
            hashed = _out.getvalue().strip()
            self.assertEquals(bcrypt.hashpw('mypass', hashed), hashed)

    def test_client_script_passhash_with_prompt(self):
        """
        Verify passhash works via getpass prompt
        """
        sys.argv = ['', 'passhash']
        with mock.patch('sys.stdout', new_callable=six.StringIO) as _out, \
                mock.patch('getpass.getpass') as _gp, \
                mock.patch('os.path.realpath') as _realpath:
            _realpath.return_value = self.conf
            _gp.return_value = 'mypass'
            client_script.main()
            hashed = _out.getvalue().strip()
            self.assertEquals(bcrypt.hashpw('mypass', hashed), hashed)

    def test_client_script_user_data(self):
        """
        Verify user-data generates a user-data file.
        """
        from email.mime.multipart import MIMEMultipart

        try:
            output_file = tempfile.mktemp()
            sys.argv = [
                '', 'user-data',
                '-e', 'https://example.com', '-o', output_file]
            client_script.main()
            with open(output_file, 'r') as f:
                m = MIMEMultipart(f.read())
                self.assertTrue(m.is_multipart())
            filename_count = 0
            for param in m.get_params():
                if param[0] == 'filename':
                    filename_count += 1

            # We should have 3 filenames
            self.assertEquals(3, filename_count)
        finally:
            os.unlink(output_file)


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
