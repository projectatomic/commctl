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
Helper commands for use with the CLI but are not specific to the client.
"""


def do_passhash(args):
    """
    Uses bcrypt to hash a password.

    :param args: Parsed ArgumentParser args
    :type args: argparse.Namespace
    :returns: The hashed password
    :rtype: str
    """
    import bcrypt

    if args.password is not None:
        pw = args.password
    elif args.file is not None:
        pw = args.file.read()
    else:
        import getpass
        pw = getpass.getpass()
    salt = bcrypt.gensalt(log_rounds=args.rounds)
    return bcrypt.hashpw(pw, salt)
