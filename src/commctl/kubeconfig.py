# Copyright (C) 2016  Red Hat, Inc
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Class for working with a kubeconfig file.
"""

import os
import yaml


class KubeConfigError(Exception):
    """
    Base error for all KubeConfig errors.
    """
    pass


class KubeConfigInvalidFileError(KubeConfigError):
    """
    Used when the kubeconfig file is invalid.
    """
    pass


class KubeConfigNoContextError(KubeConfigError):
    """
    Used when there is no context set.
    """
    pass


class KubeConfigUserTypeError(KubeConfigError):
    """
    Used when a user type can not be identified.
    """
    pass


class KubeConfigNoUserError(KubeConfigError):
    """
    Used when a user can not be found.
    """
    pass


class KubeUser:
    """
    Abstraction for a Kubernetes user.

    Each instance will have the following attributes:

    - name: The name of the user.
    - type: The type of the credentials: token, password, client-certificate
    - auth_headers: Additional authentication headers which should be used.
    """

    def __init__(self, spec):
        """
        Initializes a new KubeUser instance.

        :param spec: A kubeconfig user spec.
        :type spec: dict
        :raises: commctl.kubeconfig.KubeConfigUserTypeError
        """
        self.name = spec['name']

        if spec['user'].get('token'):
            self.token = spec['user']['token']
            self.auth_headers = [('Authorization', 'Bearer ' + self.token)]
            self.type = 'token'
        elif spec['user'].get('username') and spec['user'].get('password'):
            import base64
            self.username = spec['user']['username']
            self.password = spec['user']['password']
            self.auth_headers = [(
                'Authorization', 'Basic ' + base64.encodestring(
                    '{}:{}'.format(self.username, self.password)))]
            self.type = 'password'
        elif (spec['user'].get('client-certificate') and
                spec['user'].get('client-key')):  # pragma: no cover
            self.client_certificate = os.path.realpath(
                spec['user']['client-certificate'])
            self.client_key = os.path.realpath(spec['user']['client-key'])
            # TODO
            self.auth_headers = ()
            self.type = 'client-certificate'
        else:
            raise KubeConfigUserTypeError(
                'Unknown user type: {0}'.format(spec))


class KubeConfig:
    """
    Abstraction for a kubeconfig file.
    """

    def __init__(self, file_path):
        """
        Initializes an instance of KubeConfig.

        :param file_path: Path to a kubeconfig file.
        :type file_path: str
        :raises: commctl.kubeconfig.KubeConfigInvalidFileError
        """
        self.file_path = os.path.realpath(file_path)
        with open(self.file_path, 'r') as f:
            try:
                self._kubeconfig = yaml.safe_load(f)
            except yaml.error.YAMLError as error:
                raise KubeConfigInvalidFileError(error)

    @property
    def current_context(self):
        """
        Returns the current context.

        :raises: commctl.kubeconfig.KubeConfigNoContextError
        """
        ctx_name = self._kubeconfig.get('current-context', None)
        for ctx in self._kubeconfig.get('contexts', []):
            if ctx_name == ctx['name']:
                return ctx
        raise KubeConfigNoContextError('No context has been set.')

    @property
    def current_user(self):
        """
        Returns the current user for the current context.

        :raises: commctl.kubeconfig.KubeConfigNoUserError
        """
        username = self.current_context.get('context', {}).get('user', None)
        for user_spec in self._kubeconfig.get('users', []):
            if username == user_spec['name']:
                return KubeUser(user_spec)
        raise KubeConfigNoUserError(
            'Can not find data for user {0}'.format(username))
