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

import commctl.cli


def main():
    """
    Main script entry point.
    """
    epilog = 'Example: commctl create upgrade datacenter1 -u 7.2.2'

    parser = argparse.ArgumentParser(epilog=epilog)
    commctl.cli.add_subparsers(parser)

    args = parser.parse_args()
    dispatcher = args._class()
    dispatcher.set_args(args)
    dispatcher.dispatch()


if __name__ == '__main__':  # pragma: no cover
    main()
