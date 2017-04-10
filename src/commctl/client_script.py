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

from __future__ import print_function

import argparse

import commctl.cli


def main():
    """
    Main script entry point.
    """
    epilog = 'Example: commctl create deploy datacenter1 -u 7.2.2'

    parser = argparse.ArgumentParser(epilog=epilog)
    subparser = parser.add_subparsers(dest='command')

    cluster_parser = subparser.add_parser('cluster')
    commctl.cli.add_cluster_commands(cluster_parser)

    container_manager_parser = subparser.add_parser('container_manager')
    commctl.cli.add_container_manager_commands(container_manager_parser)

    host_parser = subparser.add_parser('host')
    commctl.cli.add_host_commands(host_parser)

    networks_parser = subparser.add_parser('network')
    commctl.cli.add_network_commands(networks_parser)

    # XXX passhash is more like a helper script.  Keep it out
    #     of the shared API for now, and exclusive to commctl.
    subcmd_parser = subparser.add_parser('passhash')
    subcmd_parser.add_argument(
        '-p', '--password', help='Password to hash')
    subcmd_parser.add_argument(
        '-f', '--file', type=argparse.FileType('rb'),
        help='Password file to hash (or "-" for stdin)')
    subcmd_parser.add_argument(
        '-r', '--rounds', type=int, default=12, help='Number of rounds')

    args = parser.parse_args()

    try:
        if args.command == 'passhash':
            from commctl.helpers import do_passhash
            print(do_passhash(args))
        else:
            dispatcher = args._class()
            dispatcher.set_args(args)
            getattr(dispatcher, args.func)()
    except Exception as ex:
        parser.error(ex)


if __name__ == '__main__':  # pragma: no cover
    main()
