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
import socket
import tempfile
import yaml

import requests

# If we are on Python 2.x use raw_input as input
if platform.python_version_tuple()[0] == '2':
    input = raw_input


def default_config_file():
    return os.path.realpath(os.path.expanduser('~/.commissaire.json'))


def host_address(arg):
    """
    Conversion function for host address arguments.  Attempts to resolve
    a host name to an IP address.

    :param arg: Input string from command-line
    :type arg: string
    :returns: IP address
    :rtype: string
    """
    try:
        return socket.gethostbyname(arg)
    except socket.gaierror as ex:
        message = '{0}: {1}'.format(arg, ex.strerror)
        raise argparse.ArgumentTypeError(message)


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


class InvalidConfiguration(ClientError):
    """
    Raised when a configuration element forces a stop of execution.
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
        # Favor a kubeconfig over user/pass
        if conf.get('kubeconfig', None):
            from commctl import kubeconfig
            try:
                kube_user = kubeconfig.KubeConfig(
                    conf['kubeconfig']).current_user

                for header in kube_user.auth_headers:
                    self._con.headers[header[0]] = header[1]
            except kubeconfig.KubeConfigNoUserError as error:
                raise InvalidConfiguration(
                    '{0}: {1}'.format(type(error), error))
        else:
            self._con.auth = (conf['username'], conf['password'])

    def _handle_status(self, resp):
        """
        Generic handling of status responses.

        :param resp: The response to look at.
        :type resp: requests.Response
        :rtype: varies
        :raises: ClientError
        """
        # Handle 204 No Content as its own case
        if resp.status_code == requests.codes.NO_CONTENT:
            return 'No instance'
        # Allow any other 2xx code
        elif str(resp.status_code).startswith('2'):
            try:
                ret = resp.json()
                if ret:
                    return ret
            except ValueError:
                # Not everything returns JSON.
                # TODO: If/when logging is added add a debug statement
                pass
            if resp.status_code == requests.codes.CREATED:
                return ['Created {0}'.format(
                    resp.request.path_url.rsplit('/')[-1])]
            return 'Success'
        elif resp.status_code == requests.codes.FORBIDDEN:
            raise ClientError('The provided credentials were incorrect.')
        elif resp.status_code == requests.codes.NOT_FOUND:
            return 'No object found.'
        raise ClientError(
            'Unable to {0} the object at {1}: {2}'.format(
                resp.request.method, resp.request.path_url, resp.status_code))

    def _get(self, path):
        """
        Shorthand for GETing.

        :param path: Path to request.
        :type path: str
        :return: None on success, requests.Response on failure.
        :rtype: None or requests.Response
        """
        resp = self._con.get(path)
        return self._handle_status(resp)

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
        return self._handle_status(resp)

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
        return self._handle_status(resp)

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
        data = {
            'type': kwargs['type'],
            'network': kwargs['network'],
        }

        if 'container_manager' in list(kwargs.keys()):
            data['container_manager'] = kwargs['container_manager']
        return self._put(path, data)

    def cluster_delete(self, name, **kwargs):
        """
        Attempts to delete a cluster.

        :param name: List of cluster names
        :type name: list
        :param kwargs: Any other keyword arguments
        :type kwargs: dict
        """
        result = []
        for item in name:
            path = '/api/v0/cluster/{0}'.format(item)
            result.append(self._delete(path))
        return result

    def container_manager_list(self, **kwargs):
        """
        Attempts to list available container_managers.

        :param kwargs: Keyword arguments
        :type kwargs: dict
        """
        path = '/api/v0/container_managers'
        return self._get(path)

    def container_manager_get(self, name, **kwargs):
        """
        Attempts to get container_manager information.

        :param name: The name of the container_manager
        :type name: str
        :param kwargs: Any other keyword arguments
        :type kwargs: dict
        """
        path = '/api/v0/container_managers/{0}'.format(name)
        return self._get(path)

    def container_manager_create(self, name, **kwargs):
        """
        Attempts to create a container_manager.

        :param name: The name of the container_manager
        :type name: str
        :param kwargs: Any other keyword arguments
        :type kwargs: dict
        """
        path = '/api/v0/container_managers/{0}'.format(name)
        print(path)
        data = {
            'type': kwargs['type'],
            'options': kwargs.get('options', {}),
        }

        return self._put(path, data)

    def container_manager_delete(self, name, **kwargs):
        """
        Attempts to delete a container_manager.

        :param name: List of container_manager names
        :type name: list
        :param kwargs: Any other keyword arguments
        :type kwargs: dict
        """
        result = []
        for item in name:
            path = '/api/v0/container_managers/{0}'.format(item)
            result.append(self._delete(path))
        return result

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

        :param address: List of host IP addresses
        :type address: list
        :param kwargs: Any other keyword arguments
        :type kwargs: dict
        """
        result = []
        for item in address:
            path = '/api/v0/host/{0}'.format(item)
            result.append(self._delete(path))
        return result

    def host_status(self, address, **kwargs):
        """
        Attempts to get the status of a host.

        :param address: The IP address of the host
        :type address: str
        :param kwargs: Any other keyword arguments
        :type kwargs: dict
        """
        path = '/api/v0/host/{0}/status'.format(address)
        return self._get(path)

    def cluster_deploy_status(self, name, **kwargs):
        """
        Attempts to get the status of an ongoing tree image deployment.

        :param name: The name of the cluster
        :type name: str
        :param kwargs: Any other keyword arguments
        :type kwargs: dict
        """
        path = '/api/v0/cluster/{0}/deploy'.format(name)
        return self._get(path)

    def cluster_deploy_start(self, name, version, **kwargs):
        """
        Attempts to initiate a tree image deployment across a cluster.

        :param name: The name of the cluster
        :type name: str
        :param version: The tree image version to deploy
        :type version: str
        :param kwargs: Any other keyword arguments
        :type kwargs: dict
        """
        path = '/api/v0/cluster/{0}/deploy'.format(name)
        return self._put(path, {'version': version})

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

    def cluster_upgrade_start(self, name, **kwargs):
        """
        Attempts to initiate a cluster upgrade.

        :param name: The name of the cluster
        :type name: str
        :param kwargs: Any other keyword arguments
        :type kwargs: dict
        """
        path = '/api/v0/cluster/{0}/upgrade'.format(name)
        return self._put(path)

    def network_get(self, name, **kwargs):
        """
        Attempts to get network information.

        :param name: The name of the network
        :type name: str
        :param kwargs: Any other keyword arguments
        :type kwargs: dict
        """
        path = '/api/v0/network/{0}'.format(name)
        return self._get(path)

    def network_create(self, name, **kwargs):
        """
        Attempts to create a network.

        :param name: The name of the network
        :type name: str
        :param kwargs: Any other keyword arguments
        :type kwargs: dict
        """
        path = '/api/v0/network/{0}'.format(name)
        data = {
            'type': kwargs.get('type'),
            'options': kwargs.get('options', {}),
        }
        return self._put(path, data)

    def network_delete(self, name, **kwargs):
        """
        Attempts to delete a network.

        :param name: List of network names
        :type name: list
        :param kwargs: Any other keyword arguments
        :type kwargs: dict
        """
        result = []
        for item in name:
            path = '/api/v0/network/{0}'.format(item)
            result.append(self._delete(path))
        return result

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
            # If it is a dict handle it as hosts
            if isinstance(result, dict):
                result = [host['address'] for host in result]
            # otherwise return as is
            return result
        else:
            path = '/api/v0/cluster/{0}/hosts'.format(name)
            return self._get(path)

    def network_list(self, **kwargs):
        """
        Attempts to list available networks.

        :param kwargs: Keyword arguments
        :type kwargs: dict
        """
        path = '/api/v0/networks'
        return self._get(path)

    def host_ssh(self, hostname, extra_args, **kwargs):
        """
        Uses the HostCreds endpoint to download credentials and execute ssh.

        :param hostname: The hostname or IP address
        :type hostname: str
        :param extra_args: Extra arguments to pass to ssh
        :type extra_args: list
        :param kwargs: Any other keyword arguments
        :type kwargs: dict
        """
        import subprocess
        # XXX: Normally we should use subprocess.call without the shell. Since
        #      this command is really a wrapper around a shell command we allow
        #      shell usage.
        path = '/api/v0/host/{0}/creds'.format(hostname)
        result = self._get(path)
        ssh_priv_key_path = None
        if result.get('ssh_priv_key') and result.get('remote_user'):
            try:
                fd, ssh_priv_key_path = tempfile.mkstemp()
                with open(ssh_priv_key_path, 'w') as ssh_priv_key_fobj:
                    ssh_priv_key_fobj.write(
                        base64.decodestring(result['ssh_priv_key']))
                os.close(fd)
                ssh_cmd = ('ssh -i {0} -l {1} {2} {3}'.format(
                    ssh_priv_key_path, result['remote_user'],
                    ' '.join(extra_args), hostname))
                print('Calling ssh command via shell: "{0}"'.format(ssh_cmd))
                subprocess.call(ssh_cmd, shell=True)
            finally:
                # Remove the keyfile
                if ssh_priv_key_path:
                    os.remove(ssh_priv_key_path)
                    print('Removed temporary ssh key')
        else:
            print('Unable to determine key and user from the server.')


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
        requires_user_pass = True

        if 'endpoint' not in conf.keys():
            conf['endpoint'] = input('Endpoint: ')
        if 'kubeconfig' in conf.keys():
            # If we have a kubeconfig entry move along. It will be handled
            # once the Client is created.
            requires_user_pass = False
        if requires_user_pass:
            if 'username' not in conf.keys():
                conf['username'] = input('Username: ')
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
            # XXX Don't dump scalars.  yaml.dump() appends an
            #     ugly-looking end-of-document marker (\n...).
            #
            #     Also avoid tick marks on a list of scalars
            #     so it can serve an input to another command.
            list_of_scalars = (
                type(call_result) is list and
                all(not hasattr(x, '__iter__') for x in call_result))
            if list_of_scalars:
                output_data = '\n'.join([str(x) for x in call_result])
            elif hasattr(call_result, '__iter__'):
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

    def dispatch_container_manager_command(self):
        """
        Dispatching callback for container_manager commands.
        """
        client_method = 'container_manager_' + self._args.command
        if hasattr(self._args, 'subcommand'):
            client_method += '_' + self._args.subcommand
        self._dispatch(client_method)

    def dispatch_host_command(self):
        """
        Dispatching callback for host commands.
        """
        client_method = 'host_' + self._args.command
        self._dispatch(client_method)

    def dispatch_network_command(self):
        """
        Dispatching callback for network commands.
        """
        client_method = 'network_' + self._args.command
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
    verb_parser.add_argument(
        '-t', '--type', help='Type of the cluster',
        choices=('kubernetes', 'host_only'), default='kubernetes')
    verb_parser.add_argument(
        '-n', '--network', help='The network configuration to use',
        default='default')
    verb_parser.add_argument('name', help='Name of the cluster')

    # Sub-command: cluster delete
    verb_parser = subject_subparser.add_parser('delete')
    verb_parser.required = True
    verb_parser.add_argument('name', nargs='+', help='Name of the cluster')

    # Sub-command: cluster get
    verb_parser = subject_subparser.add_parser('get')
    verb_parser.required = True
    verb_parser.add_argument('name', help='Name of the cluster')

    # Sub-command: cluster list
    subject_subparser.add_parser('list')
    # No arguments for 'cluster list' at present.

    # Command: cluster deploy ...

    object_parser = subject_subparser.add_parser('deploy')
    object_subparser = object_parser.add_subparsers(dest='subcommand')
    object_subparser.required = True

    # Sub-command: cluster deploy start
    verb_parser = object_subparser.add_parser('start')
    verb_parser.required = True
    verb_parser.add_argument('name', help='Name of the cluster')
    verb_parser.add_argument('version', help='Version to deploy')

    # Sub-command: cluster deploy status
    verb_parser = object_subparser.add_parser('status')
    verb_parser.required = True
    verb_parser.add_argument('name', help='Name of the cluster')

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

    # Sub-command: cluster upgrade status
    verb_parser = object_subparser.add_parser('status')
    verb_parser.required = True
    verb_parser.add_argument('name', help='Name of the cluster')


def add_container_manager_commands(argument_parser):
    """
    Augments the argument parser with "container_manager" subcommands.

    :param argument_parser: The argument parser to augment
    :type argument_parser: argparser.ArgumentParser
    """
    _configure_parser(argument_parser, 'dispatch_container_manager_command')

    # Note, commands follow a "subject-verb" or "subject-object-verb"
    # pattern.  e.g. "host create" or "cluster upgrade start"

    subject_subparser = argument_parser.add_subparsers(dest='command')

    # Sub-command: cluster create
    verb_parser = subject_subparser.add_parser('create')
    verb_parser.required = True
    verb_parser.add_argument(
        '-t', '--type', help='Type of the container manager',
        choices=('openshift', ), default='openshift')
    verb_parser.add_argument(
        '-o', '--options', help='Options for the container manager',
        default={})
    verb_parser.add_argument('name', help='Name of the container_manager')

    # Sub-command: cluster delete
    verb_parser = subject_subparser.add_parser('delete')
    verb_parser.required = True
    verb_parser.add_argument(
        'name', nargs='+', help='Name of the container manager')

    # Sub-command: cluster get
    verb_parser = subject_subparser.add_parser('get')
    verb_parser.required = True
    verb_parser.add_argument('name', help='Name of the container manager')

    # Sub-command: cluster list
    subject_subparser.add_parser('list')
    # No arguments for 'container_manager list' at present.


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
    verb_parser.add_argument(
        'address', type=host_address,
        help='Host name or IP address')
    verb_parser.add_argument(
        'ssh-priv-key', type=argparse.FileType('rb'),
        help='SSH private key file (or "-" for stdin)')
    verb_parser.add_argument(
        '-c', '--cluster', help='Add host to the cluster named CLUSTER')

    # Sub-command: host delete
    verb_parser = subject_subparser.add_parser('delete')
    verb_parser.required = True
    verb_parser.add_argument(
        'address', nargs='+', type=host_address,
        help='Host name or IP address')

    # Sub-command: host get
    verb_parser = subject_subparser.add_parser('get')
    verb_parser.required = True
    verb_parser.add_argument(
        'address', type=host_address,
        help='Host name or IP address')

    # Sub-command: host list
    verb_parser = subject_subparser.add_parser('list')
    verb_parser.add_argument(
        'name', nargs='?', default=None,
        help='Name of the cluster (omit to list all hosts)')

    # Sub-command: host status
    verb_parser = subject_subparser.add_parser('status')
    verb_parser.required = True
    verb_parser.add_argument(
        'address', type=host_address,
        help='Host name or IP address')

    # Sub-command: host ssh
    verb_parser = subject_subparser.add_parser('ssh')

    verb_parser.required = True
    verb_parser.add_argument(
        'hostname', help='Host to connect to. EX: 10.1.1.1')
    verb_parser.add_argument(
        'extra_args', nargs=argparse.REMAINDER,
        help='Any other arguments to pass to ssh')


def add_network_commands(argument_parser):
    """
    Augments the argument parser with "network" subcommands.

    :param argument_parser: The argument parser to augment
    :type argument_parser: argparser.ArgumentParser
    """
    _configure_parser(argument_parser, 'dispatch_network_command')

    # Note, commands follow a "subject-verb" or "subject-object-verb"
    # pattern.  e.g. "host create" or "cluster upgrade start"

    subject_subparser = argument_parser.add_subparsers(dest='command')

    # Sub-command: network create
    verb_parser = subject_subparser.add_parser('create')
    verb_parser.required = True
    verb_parser.add_argument(
        'name', type=str, help='Name of the network')
    verb_parser.add_argument(
        '-t', '--type', choices=('flannel_etcd', 'flannel_server'),
        default='flannel_etcd', help='Type of network')
    verb_parser.add_argument(
        '-o', '--options', type=json.loads,
        default={}, help='Options for the network')

    # Sub-command: network delete
    verb_parser = subject_subparser.add_parser('delete')
    verb_parser.required = True
    verb_parser.add_argument(
        'name', nargs='+', help='Name of one or more networks')

    # Sub-command: network get
    verb_parser = subject_subparser.add_parser('get')
    verb_parser.required = True
    verb_parser.add_argument(
        'name', type=str, help='Name of the network')

    verb_parser = subject_subparser.add_parser('list')
    # Sub-command: network list
    verb_parser.add_argument(
        'name', nargs='?', default=None,
        help='Name of the cluster (omit to list all hosts)')
