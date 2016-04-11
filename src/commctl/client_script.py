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
Client CLI for commissaire.
"""

import argparse
import json
import os.path
import platform

import requests

# If we are on Python 2.x use raw_input as input
if platform.python_version_tuple()[0] == 2:
    input = raw_input


class ClientError(Exception):
    """
    Base exception for Client Errors.
    """
    pass


class NoMoreServersError(ClientError):
    """
    Raised when no more servers are available to try.
    """
    pass


class MultiServerSession(requests.Session):
    """
    A requests Session which, when given a ConnectionError, will try the same
    request against the next server it has been provided with.
    """

    def __init__(self, servers=[]):
        """
        Initializes a new instance of the MultiServerSession.

        :param servers: List of servers to try on connection error.
        :type servers: list
        """
        super(MultiServerSession, self).__init__()
        self._servers = servers

    def request(self, method, path, *args, **kwargs):
        """
        Overriden request which tries all available servers in the event
        of a ConnectionError.

        .. note::

           This override uses ``path`` instead of ``uri``!

        :param method: method for the new :class:`Request` object.
        :type method: str
        :param path: Path to request.
        :type path: str
        :param args: All other non-keyword arguments.
        :type args: list
        :param kwargs: All other keyword arguments.
        :type kwargs: dict
        :returns: requests.models.Response
        :raises: requests.exceptions.ConnectionError
        """
        for x in range(0, len(self._servers)):
            target_url = self._servers[x] + path
            try:
                result = super(MultiServerSession, self).request(
                    method, target_url, *args, **kwargs)
                return result
            except requests.ConnectionError:
                if x != len(self._servers) - 1:
                    print(
                        "Could not connect to {0}. Retrying with {1}.".format(
                            self._servers[x], self._servers[x + 1]))
                    continue
                raise NoMoreServersError(*self._servers)


class Client(object):
    """
    Client for commissaire.
    """

    def __init__(self, conf):
        """
        Creates an instance of the Client.

        :param conf: Configuration dict
        :type conf: dict
        :returns: A Client instance
        :rtype: Client
        """
        self._endpoints = []
        for ep in conf['endpoint']:
            if ep.endswith('/'):
                ep = ep[:-1]
            self._endpoints.append(ep)

        # Take the first endpoint by default
        self.endpoint = conf['endpoint'][0]
        self._con = MultiServerSession(self._endpoints)
        self._con.headers['Content-Type'] = 'application/json'
        self._con.auth = (conf['username'], conf['password'])

    def _get(self, path):
        """
        Shorthand for GETing.

        :param path: Path to request.
        :type path: str
        :return: None on success, requests.Response on failure.
        :rtype: None or requests.Response
        """
        resp = self._con.get(path)
        # Allow any 2xx code
        if resp.status_code > 199 and resp.status_code < 300:
            ret = resp.json()
            if ret:
                return ret
            return
        if resp.status_code == 403:
            raise ClientError('Username/Password was incorrect.')
        raise ClientError(
            'Unable to get the object at {0}: {1}'.format(
                path, resp.status_code))

    def _put(self, path, data={}):
        """
        Shorthand for PUTting.

        :param path: Path to request.
        :type path: str
        :param data: Optional dictionary to jsonify and PUT.
        :type data: dict
        :return: None on success, requests.Response on failure.
        :rtype: None or requests.Response
        """
        resp = self._con.put(path, data=json.dumps(data))
        if resp.status_code == 201:
            ret = resp.json()
            if ret:
                return ret
            return ['Created']
        if resp.status_code == 403:
            raise ClientError('Username/Password was incorrect.')
        raise ClientError(
            'Unable to create an object at {0}: {1}'.format(
                path, resp.status_code))

    def get_cluster(self, name, **kwargs):
        """
        Attempts to get cluster information.

        :param name: The name of the cluster
        :type name: str
        :param kwargs: Any other keyword arguments
        :type kwargs: dict
        """
        path = '/api/v0/cluster/{0}'.format(name)
        return self._get(path)

    def create_cluster(self, name, **kwargs):
        """
        Attempts to create a cluster.

        :param name: The name of the cluster
        :type name: str
        :param kwargs: Any other keyword arguments
        :type kwargs: dict
        """
        path = '/api/v0/cluster/{0}'.format(name)
        return self._put(path)

    def get_restart(self, name, **kwargs):
        """
        Attempts to get a cluster restart.

        :param name: The name of the cluster
        :type name: str
        :param kwargs: Any other keyword arguments
        :type kwargs: dict
        """
        path = '/api/v0/cluster/{0}/restart'.format(name)
        return self._get(path)

    def create_restart(self, name, **kwargs):
        """
        Attempts to create a cluster restart.

        :param name: The name of the cluster
        :type name: str
        :param kwargs: Any other keyword arguments
        :type kwargs: dict
        """
        path = '/api/v0/cluster/{0}/restart'.format(name)
        return self._put(path)

    def get_upgrade(self, name, **kwargs):
        """
        Attempts to retrieve a cluster upgrade.

        :param name: The name of the cluster
        :type name: str
        :param kwargs: Any other keyword arguments
        :type kwargs: dict
        """
        path = '/api/v0/cluster/{0}/upgrade'.format(name)
        return self._get(path)

    def create_upgrade(self, name, **kwargs):
        """
        Attempts to create a cluster upgrade.

        :param name: The name of the cluster
        :type name: str
        :param kwargs: Any other keyword arguments
        :type kwargs: dict
        """
        path = '/api/v0/cluster/{0}/upgrade'.format(name)
        return self._put(path, {'upgrade_to': kwargs['upgrade_to']})

    def list_clusters(self, **kwargs):
        """
        Attempts to list available clusters.

        :param kwargs: Keyword arguments
        :type kwargs: dict
        """
        path = '/api/v0/clusters'
        return self._get(path)

    def list_hosts(self, name, **kwargs):
        """
        Attempts to list all hosts or hosts in particular cluster.

        :param name: The name of the cluster (optional)
        :type name: str or None
        :param kwargs: Any other keyword arguments
        :type kwargs: dict
        """
        if not name:
            path = '/api/v0/hosts'
            result = self._get(path)
            if result:
                result = [host['address'] for host in result]
            return result
        else:
            path = '/api/v0/cluster/{0}/hosts'.format(name)
            return self._get(path)


def main():
    """
    Main script entry point.
    """
    import yaml  # Used for output formatting
    epilog = 'Example: commctl create upgrade -n datacenter1 -u 7.2.2'

    parser = argparse.ArgumentParser(epilog=epilog)
    parser.add_argument(
        '--config', '-c', type=str, default=os.path.realpath(
            os.path.expanduser('~/.commissaire.json')),
        help='Full path to the configuration file.')

    # FIXME: It's not clear whether setting required=True on subparsers is
    #        really necessary.  Supposedly it's to work around some glitch
    #        in Python 3, but a 2v3 comparison of argparse.py doesn't show
    #        any relevant looking changes and the docs claim 'required' is
    #        only meant for arguments.  Reinvestigate.

    # Create command structure
    sp = parser.add_subparsers(dest='main_command')
    sp.required = True

    # Command: get ...

    get_parser = sp.add_parser('get')
    get_sp = get_parser.add_subparsers(dest='sub_command')
    get_sp.required = True

    cluster_parser = get_sp.add_parser('cluster')
    cluster_parser.required = True
    cluster_parser.add_argument('name', help='Name of the cluster')

    restart_parser = get_sp.add_parser('restart')
    restart_parser.required = True
    restart_parser.add_argument('name', help='Name of the cluster')

    upgrade_parser = get_sp.add_parser('upgrade')
    upgrade_parser.required = True
    upgrade_parser.add_argument('name', help='Name of the cluster')

    # Command: create ...

    create_parser = sp.add_parser('create')
    create_parser.required = True
    create_sp = create_parser.add_subparsers(dest='sub_command')
    create_sp.required = True

    cluster_parser = create_sp.add_parser('cluster')
    cluster_parser.required = True
    cluster_parser.add_argument('name', help='Name of the cluster')

    restart_parser = create_sp.add_parser('restart')
    restart_parser.required = True
    restart_parser.add_argument('name', help='Name of the cluster')

    upgrade_parser = create_sp.add_parser('upgrade')
    upgrade_parser.required = True
    upgrade_parser.add_argument('name', help='Name of the cluster')
    # XXX Should this be positional too since it's required?
    upgrade_parser.add_argument(
        '-u', '--upgrade-to', required=True,
        help='Version to upgrade to')

    # Command: list ...

    list_parser = sp.add_parser('list')
    list_sp = list_parser.add_subparsers(dest='sub_command')
    list_sp.required = True

    list_sp.add_parser('clusters')
    # No arguments for 'list clusters' at present.

    hosts_parser = list_sp.add_parser('hosts')
    hosts_parser.add_argument(
        'name', nargs='?', default=None,
        help='Name of the cluster (omit to list all hosts)')

    args = parser.parse_args()

    # Set up the configuration
    conf = {}
    try:
        with open(args.config) as cf:
            conf = json.load(cf)
            for required in ('username', 'endpoint'):
                if required not in conf.keys():
                    conf[required] = input(
                        '{0}: '.format(required.capitalize()))

            # Check password on it's own
            if 'password' not in conf.keys():
                import getpass
                conf['password'] = getpass.getpass()
            if type(conf['endpoint']) is not list:
                conf['endpoint'] = [conf['endpoint']]

    except IOError:  # pragma no cover
        parser.error(
            'Configuration file {0} could not be opened for reading'.format(
                args.config))
    except ValueError:  # pragma no cover
        parser.error((
            'Unable to parse configuration file. HINT: Make sure to use only '
            'double quotes and the last item should not end with a coma.'))

    client = Client(conf)
    # Execute client command
    try:
        call_result = getattr(client, '{0}_{1}'.format(
            args.main_command, args.sub_command))(**args.__dict__)
        print(yaml.dump(
            call_result, default_flow_style=False,
            Dumper=yaml.SafeDumper, explicit_end=False).strip())
    except NoMoreServersError as nmse:
        print("No servers could be reached. Tried the following:")
        for server in nmse.args:
            print("- {0}".format(server))
        print("Exiting...")
        raise SystemExit(1)
    except requests.exceptions.RequestException as re:
        parser.error(re)
    except ClientError as ce:
        parser.error(ce)


if __name__ == '__main__':  # pragma: no cover
    main()
