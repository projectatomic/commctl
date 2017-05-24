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
Test cases for the commctl.kubeconfig classes.
"""

import os
import mock

from . import TestCase, get_fixture_file_path
from commctl import kubeconfig


class TestKubeConfig(TestCase):
    """
    Tests for the KubeConfig class.
    """

    def test_kube_config__init(self):
        """
        Verify creating a new instance of KubeConfig works as it should.
        """
        file_path = get_fixture_file_path('test/kubeconfig.good')
        kc = kubeconfig.KubeConfig(file_path)
        kc.file_path = os.path.realpath(file_path)

    def test_kube_config__init_fails_with_a_missing_config(self):
        """
        Verify KubeConfig raises when the file path does not exist.
        """
        file_path = 'confi'
        self.assertRaises(
            IOError,
            kubeconfig.KubeConfig,
            file_path)

    def test_kube_config__init_fails_with_a_bad_config(self):
        """
        Verify KubeConfig raises when the configuration data is bad.
        """
        file_path = get_fixture_file_path('test/kubeconfig.bad')
        self.assertRaises(
            kubeconfig.KubeConfigInvalidFileError,
            kubeconfig.KubeConfig,
            file_path)

    def test_kube_config_current_context(self):
        """
        Verify KubeConfig.current_context returns the proper context.
        """
        expected = {
            'context': {
                'cluster': 'commissaire',
                'user': 'a'},
            'name': 'commissaire',
        }
        kc = kubeconfig.KubeConfig(
            get_fixture_file_path('test/kubeconfig.good'))
        self.assertEquals(expected, kc.current_context)

    def test_kube_config_current_user_with_token(self):
        """
        Verify KubeConfig.current_user returns the proper user data with token.
        """
        kc = kubeconfig.KubeConfig(
            get_fixture_file_path('test/kubeconfig.good'))
        self.assertEquals('token', kc.current_user.type)
        self.assertEquals('a', kc.current_user.token)
        self.assertEquals('a', kc.current_user.name)

    def test_kube_config_current_user_with_password(self):
        """
        Verify KubeConfig.current_user returns the proper user data with password.
        """
        kc = kubeconfig.KubeConfig(
            get_fixture_file_path('test/kubeconfig.password'))
        self.assertEquals('password', kc.current_user.type)
        self.assertEquals('a', kc.current_user.username)
        self.assertEquals('a', kc.current_user.password)
        self.assertEquals('a', kc.current_user.name)
