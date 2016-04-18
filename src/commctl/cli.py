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
Commissaire command-line interface (CLI) functions.
"""

from __future__ import print_function

import argparse
import base64
import errno
import json
import os
import os.path
import platform
import yaml

import requests

# If we are on Python 2.x use raw_input as input
if platform.python_version_tuple()[0] == '2':
    input = raw_input


def default_config_file():
    return os.path.realpath(os.path.expanduser('~/.commissaire.json'))


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

    def _delete(self, path, data={}):
        """
        Shorthand for DELETEing.

        :param path: Path to request.
        :type path: str
        :param data: Optional dictionary to jsonify and DELETE.
        :type data: dict
        :return: None on success, requests.Response on failure.
        :rtype: None or requests.Response
        """
        resp = self._con.delete(path, data=json.dumps(data))
        if resp.status_code == 200:
            ret = resp.json()
            if ret:
                return ret
            return ['Deleted']
        if resp.status_code == 403:
            raise ClientError('Username/Password was incorrect.')
        raise ClientError(
            'Unable to delete an object at {0}: {1}'.format(
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

    def delete_cluster(self, name, **kwargs):
        """
        Attempts to delete a cluster.

        :param name: The name of the cluster
        :type name: str
        :param kwargs: Any other keyword arguments
        :type kwargs: dict
        """
        path = '/api/v0/cluster/{0}'.format(name)
        return self._delete(path)

    def get_host(self, address, **kwargs):
        """
        Attempts to get host information.

        :param address: The IP address of the host
        :type address: str
        :param kwargs: Any other keyword arguments
        :type kwargs: dict
        """
        path = '/api/v0/host/{0}'.format(address)
        return self._get(path)

    def create_host(self, address, **kwargs):
        """
        Attempts to create a host.

        :param address: The IP address of the host
        :type address: str
        :param kwargs: Any other keyword arguments
        :type kwargs: dict
        """
        path = '/api/v0/host/{0}'.format(address)
        data = {}
        infile = kwargs['ssh-priv-key']
        b64_bytes = base64.b64encode(infile.read())
        data['ssh_priv_key'] = b64_bytes.decode()
        if kwargs['cluster'] is not None:
            data['cluster'] = kwargs['cluster']
        return self._put(path, data)

    def delete_host(self, address, **kwargs):
        """
        Attempts to delete a host.

        :param address: The IP address of the host
        :type address: str
        :param kwargs: Any other keyword arguments
        :type kwargs: dict
        """
        path = '/api/v0/host/{0}'.format(address)
        return self._delete(path)

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

    def create_passhash(self, **kwargs):
        """
        Uses bcrypt to hash a password.
        """
        import bcrypt
        if kwargs['password'] is not None:
            pw = kwargs['password']
        elif kwargs['file'] is not None:
            pw = kwargs['file'].read()
        else:
            import getpass
            pw = getpass.getpass()
        return bcrypt.hashpw(pw, bcrypt.gensalt(log_rounds=kwargs['rounds']))

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


class Dispatcher(object):
    """
    Dispatches the appropriate Client method for the given set of
    command-line arguments.

    This class is abstract.  Subclasses provide the argument_parser.
    """

    # This is overridden by subclasses.
    argument_parser = None

    def __init__(self):
        self._args = None

    def set_args(self, args):
        """
        Stashes an argument namespace returned by ArgumentParser.parse_args(),
        to be used later in the dispatch() method.

        :param args: Parsed command-line arguments.
        :type args: argparse.Namespace
        """
        self._args = args

    def dispatch(self):
        """
        Dispatches a single command, and also handles session setup and
        some types of errors.  The set_args() method MUST be called first.
        """

        assert(type(self._args) is argparse.Namespace)

        # Find a configuration file.  The path can be specified as an
        # argument or an environment variable.  Failing those we fall
        # back to a default location.
        filename = getattr(
            self._args, 'config',
            os.getenv('COMMCTL_CONFIG', default_config_file()))

        # Set up the Client instance, maybe interactively.

        conf = {}
        try:
            with open(filename) as cf:
                conf = json.load(cf)
        except IOError as ex:  # pragma no cover
            # If file not found, prompt.
            if ex.errno != errno.ENOENT:
                self.argument_parser.error(
                    'Configuration file {0} could not be opened '
                    'for reading'.format(self._args.config))
        except ValueError:  # pragma no cover
            self.argument_parser.error((
                'Unable to parse configuration file. HINT: Make sure to '
                'use only double quotes and the last item should not end '
                'with a comma.'))

        # Prompt for any missing configuration.

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

        client = Client(conf)

        # Dispatch the command+subcommand.

        try:
            method_name = '{0}_{1}'.format(
                self._args.main_command, self._args.sub_command)
            bound_method = getattr(client, method_name)
            call_result = bound_method(**self._args.__dict__)
            output_data = yaml.dump(
                call_result,
                default_flow_style=False,
                Dumper=yaml.SafeDumper,
                explicit_end=False)
            print(output_data.strip())
        except NoMoreServersError as nmse:
            print("No servers could be reached. Tried the following:")
            for server in nmse.args:
                print("- {0}".format(server))
            print("Exiting...")
            raise SystemExit(1)
        except requests.exceptions.RequestException as re:
            self.argument_parser.error(re)
        except ClientError as ce:
            self.argument_parser.error(ce)


def add_subparsers(argument_parser):
    """
    Augments the given argparse.ArgumentParser with subparsers for the
    Commissaire command-line interface.

    :param argument_parser: The argument parser to augment
    :type argument_parser: argparse.ArgumentParser
    """

    # We have to conform with how atomic handles arguments:
    #
    #   args = parser.parse_args()
    #   _class = args._class()
    #   _class.set_args(args)
    #   _func = getattr(_class, args.func)
    #   sys.exit(_func())
    #
    # Note, this is the only chance we get to stash the ArgumentParser
    # which we'd like to keep for use in error handling later.  But we
    # have to stash it in a Dispatcher CLASS definition because of the
    # atomic logic above.  So this next part defines a unique subclass
    # with the parser instance stored as a class variable.  Weird, but
    # it works around the limitation.

    class_name = 'Dispatcher_' + str(id(argument_parser))
    class_defs = {'argument_parser': argument_parser}
    subclass = type(class_name, (Dispatcher,), class_defs)

    argument_parser.set_defaults(_class=subclass, func='dispatch')

    # FIXME: It's not clear whether setting required=True on subparsers is
    #        really necessary.  Supposedly it's to work around some glitch
    #        in Python 3, but a 2v3 comparison of argparse.py doesn't show
    #        any relevant looking changes and the docs claim 'required' is
    #        only meant for arguments.  Reinvestigate.

    # Create command structure
    sp = argument_parser.add_subparsers(dest='main_command')
    sp.required = True

    # Command: get ...

    get_parser = sp.add_parser('get')
    get_sp = get_parser.add_subparsers(dest='sub_command')
    get_sp.required = True

    cluster_parser = get_sp.add_parser('cluster')
    cluster_parser.required = True
    cluster_parser.add_argument('name', help='Name of the cluster')

    host_parser = get_sp.add_parser('host')
    host_parser.required = True
    host_parser.add_argument('address', help='IP address of the host')

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

    host_parser = create_sp.add_parser('host')
    host_parser.required = True
    host_parser.add_argument('address', help='IP address of the host')
    host_parser.add_argument(
        'ssh-priv-key', type=argparse.FileType('rb'),
        help='SSH private key file (or "-" for stdin)')
    host_parser.add_argument(
        '-c', '--cluster', help='Add host to the cluster named CLUSTER')

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

    passhash_parser = create_sp.add_parser('passhash')
    passhash_parser.required = True
    passhash_parser.add_argument(
        '-p', '--password', help='Password to hash')
    passhash_parser.add_argument(
        '-f', '--file', type=argparse.FileType('rb'),
        help='Password file to hash (or "-" for stdin)')
    passhash_parser.add_argument(
        '-r', '--rounds', type=int, default=12, help='Number of rounds')

    # Command: delete ...

    delete_parser = sp.add_parser('delete')
    delete_parser.required = True
    delete_sp = delete_parser.add_subparsers(dest='sub_command')
    delete_sp.required = True

    cluster_parser = delete_sp.add_parser('cluster')
    cluster_parser.required = True
    cluster_parser.add_argument('name', help='Name of the cluster')

    host_parser = delete_sp.add_parser('host')
    host_parser.required = True
    host_parser.add_argument('address', help='IP address of the host')

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
