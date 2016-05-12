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

    def cluster_get(self, name, **kwargs):
        """
        Attempts to get cluster information.

        :param name: The name of the cluster
        :type name: str
        :param kwargs: Any other keyword arguments
        :type kwargs: dict
        """
        path = '/api/v0/cluster/{0}'.format(name)
        return self._get(path)

    def cluster_create(self, name, **kwargs):
        """
        Attempts to create a cluster.

        :param name: The name of the cluster
        :type name: str
        :param kwargs: Any other keyword arguments
        :type kwargs: dict
        """
        path = '/api/v0/cluster/{0}'.format(name)
        return self._put(path)

    def cluster_delete(self, name, **kwargs):
        """
        Attempts to delete a cluster.

        :param name: The name of the cluster
        :type name: str
        :param kwargs: Any other keyword arguments
        :type kwargs: dict
        """
        path = '/api/v0/cluster/{0}'.format(name)
        return self._delete(path)

    def host_get(self, address, **kwargs):
        """
        Attempts to get host information.

        :param address: The IP address of the host
        :type address: str
        :param kwargs: Any other keyword arguments
        :type kwargs: dict
        """
        path = '/api/v0/host/{0}'.format(address)
        return self._get(path)

    def host_create(self, address, **kwargs):
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

    def host_delete(self, address, **kwargs):
        """
        Attempts to delete a host.

        :param address: The IP address of the host
        :type address: str
        :param kwargs: Any other keyword arguments
        :type kwargs: dict
        """
        path = '/api/v0/host/{0}'.format(address)
        return self._delete(path)

    def cluster_restart_status(self, name, **kwargs):
        """
        Attempts to get the status of an ongoing cluster restart.

        :param name: The name of the cluster
        :type name: str
        :param kwargs: Any other keyword arguments
        :type kwargs: dict
        """
        path = '/api/v0/cluster/{0}/restart'.format(name)
        return self._get(path)

    def cluster_restart_start(self, name, **kwargs):
        """
        Attempts to initiate a cluster restart.

        :param name: The name of the cluster
        :type name: str
        :param kwargs: Any other keyword arguments
        :type kwargs: dict
        """
        path = '/api/v0/cluster/{0}/restart'.format(name)
        return self._put(path)

    def cluster_upgrade_status(self, name, **kwargs):
        """
        Attempts to get the status of an ongoing cluster upgrade.

        :param name: The name of the cluster
        :type name: str
        :param kwargs: Any other keyword arguments
        :type kwargs: dict
        """
        path = '/api/v0/cluster/{0}/upgrade'.format(name)
        return self._get(path)

    def cluster_upgrade_start(self, name, version, **kwargs):
        """
        Attempts to initiate a cluster upgrade.

        :param name: The name of the cluster
        :type name: str
        :param kwargs: Any other keyword arguments
        :type kwargs: dict
        """
        path = '/api/v0/cluster/{0}/upgrade'.format(name)
        return self._put(path, {'upgrade_to': version})

    def cluster_list(self, **kwargs):
        """
        Attempts to list available clusters.

        :param kwargs: Keyword arguments
        :type kwargs: dict
        """
        path = '/api/v0/clusters'
        return self._get(path)

    def host_list(self, name, **kwargs):
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

    def _dispatch(self, client_method):
        """
        Dispatches a single command, and also handles session setup and
        some types of errors.  The set_args() method MUST be called first.

        :param client_method: Method name to invoke on the Client instance
        :type client_method: str
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

        # Dispatch the appropriate method for the command.

        try:
            bound_method = getattr(client, client_method)
            call_result = bound_method(**self._args.__dict__)
            # XXX Don't dump literals.  yaml.dump() appends an
            #     ugly-looking end-of-document marker (\n...).
            if hasattr(call_result, '__iter__'):
                output_data = yaml.dump(
                    call_result,
                    default_flow_style=False,
                    Dumper=yaml.SafeDumper,
                    explicit_end=False)
            else:
                output_data = str(call_result)
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

    def dispatch_cluster_command(self):
        """
        Dispatching callback for cluster commands.
        """
        client_method = 'cluster_' + self._args.command
        if hasattr(self._args, 'subcommand'):
            client_method += '_' + self._args.subcommand
        self._dispatch(client_method)

    def dispatch_host_command(self):
        """
        Dispatching callback for host commands.
        """
        client_method = 'host_' + self._args.command
        self._dispatch(client_method)


def _configure_parser(argument_parser, method_name):
    """
    Configures a Dispatcher subclass for the argument parser.

    We have to conform with how atomic handles arguments:

      args = parser.parse_args()
      _class = args._class()
      _class.set_args(args)
      _func = getattr(_class, args.func)
      sys.exit(_func())

    Note, this is the only chance we get to stash the ArgumentParser
    which we'd like to keep for use in error handling later.  But we
    have to stash it in a Dispatcher CLASS definition because of the
    atomic logic above.  So this next part defines a unique subclass
    with the parser instance stored as a class variable.  Weird, but
    it works around the limitation.

    :param argument_parser: The argument parser to configure
    :type argument_parser: argparser.ArgumentParser
    :param method_name: The Dispatcher method to call
    :type method_name: str
    """
    class_name = 'Dispatcher_' + str(id(argument_parser))
    class_defs = {'argument_parser': argument_parser}
    subclass = type(class_name, (Dispatcher,), class_defs)
    argument_parser.set_defaults(_class=subclass, func=method_name)


def add_cluster_commands(argument_parser):
    """
    Augments the argument parser with "cluster" subcommands.

    :param argument_parser: The argument parser to augment
    :type argument_parser: argparser.ArgumentParser
    """
    _configure_parser(argument_parser, 'dispatch_cluster_command')

    # Note, commands follow a "subject-verb" or "subject-object-verb"
    # pattern.  e.g. "host create" or "cluster upgrade start"

    subject_subparser = argument_parser.add_subparsers(dest='command')

    # FIXME: It's not clear whether setting required=True on subparsers is
    #        really necessary.  Supposedly it's to work around some glitch
    #        in Python 3, but a 2v3 comparison of argparse.py doesn't show
    #        any relevant looking changes and the docs claim 'required' is
    #        only meant for arguments.  Reinvestigate.

    # Sub-command: cluster create
    verb_parser = subject_subparser.add_parser('create')
    verb_parser.required = True
    verb_parser.add_argument('name', help='Name of the cluster')

    # Sub-command: cluster delete
    verb_parser = subject_subparser.add_parser('delete')
    verb_parser.required = True
    verb_parser.add_argument('name', help='Name of the cluster')

    # Sub-command: cluster get
    verb_parser = subject_subparser.add_parser('get')
    verb_parser.required = True
    verb_parser.add_argument('name', help='Name of the cluster')

    # Sub-command: cluster list
    subject_subparser.add_parser('list')
    # No arguments for 'cluster list' at present.

    # Command: cluster restart ...

    object_parser = subject_subparser.add_parser('restart')
    object_subparser = object_parser.add_subparsers(dest='subcommand')
    object_subparser.required = True

    # Sub-command: cluster restart start
    restart_parser = object_subparser.add_parser('start')
    restart_parser.required = True
    restart_parser.add_argument('name', help='Name of the cluster')

    # Sub-command: cluster restart status
    verb_parser = object_subparser.add_parser('status')
    verb_parser.required = True
    verb_parser.add_argument('name', help='Name of the cluster')

    # Command: cluster upgrade ...

    object_parser = subject_subparser.add_parser('upgrade')
    object_subparser = object_parser.add_subparsers(dest='subcommand')
    object_subparser.required = True

    # Sub-command: cluster upgrade start
    verb_parser = object_subparser.add_parser('start')
    verb_parser.required = True
    verb_parser.add_argument('name', help='Name of the cluster')
    verb_parser.add_argument('version', help='Version to upgrade to')

    # Sub-command: cluster upgrade status
    verb_parser = object_subparser.add_parser('status')
    verb_parser.required = True
    verb_parser.add_argument('name', help='Name of the cluster')


def add_host_commands(argument_parser):
    """
    Augments the argument parser with "host" subcommands.

    :param argument_parser: The argument parser to augment
    :type argument_parser: argparser.ArgumentParser
    """
    _configure_parser(argument_parser, 'dispatch_host_command')

    # Note, commands follow a "subject-verb" or "subject-object-verb"
    # pattern.  e.g. "host create" or "cluster upgrade start"

    subject_subparser = argument_parser.add_subparsers(dest='command')

    # FIXME: It's not clear whether setting required=True on subparsers is
    #        really necessary.  Supposedly it's to work around some glitch
    #        in Python 3, but a 2v3 comparison of argparse.py doesn't show
    #        any relevant looking changes and the docs claim 'required' is
    #        only meant for arguments.  Reinvestigate.

    # Sub-command: host create
    verb_parser = subject_subparser.add_parser('create')
    verb_parser.required = True
    verb_parser.add_argument('address', help='IP address of the host')
    verb_parser.add_argument(
        'ssh-priv-key', type=argparse.FileType('rb'),
        help='SSH private key file (or "-" for stdin)')
    verb_parser.add_argument(
        '-c', '--cluster', help='Add host to the cluster named CLUSTER')

    # Sub-command: host delete
    verb_parser = subject_subparser.add_parser('delete')
    verb_parser.required = True
    verb_parser.add_argument('address', help='IP address of the host')

    # Sub-command: host get
    verb_parser = subject_subparser.add_parser('get')
    verb_parser.required = True
    verb_parser.add_argument('address', help='IP address of the host')

    # Sub-command: host list
    verb_parser = subject_subparser.add_parser('list')
    verb_parser.add_argument(
        'name', nargs='?', default=None,
        help='Name of the cluster (omit to list all hosts)')
