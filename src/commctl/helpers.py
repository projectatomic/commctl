# Copyright (C) 2016-2017  Red Hat, Inc
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


def do_user_data(args):
    """
    Generates a user-data file for cloud-init

    :param args: Parsed ArgumentParser args
    :type args: argparse.Namespace
    """
    import json
    import os.path
    import sys
    import tempfile

    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    # Holds all thre required files to make our user-data
    # Keys are the mime-type, values are the paths to the files
    files = {
        'cloud-config': os.path.sep.join([
            os.path.dirname(os.path.realpath(
                __file__)), 'data', 'cloud-init.txt']),
        'x-commissaire-host': None,
        'part-handler': os.path.sep.join([os.path.dirname(
            os.path.realpath(__file__)), 'data', 'part-handler.py']),
    }

    if args.cloud_init is not None:
        files['cloud-config'] = args.cloud_init

    # Create and populate the configuration
    config_struct = {
        'endpoint': args.endpoint,
    }
    for key in (
        'username', 'password', 'cluster', 'remote_user',
            'ssh_key_path', 'authorized_keys_path'):
        value = getattr(args, key)
        if value is not None:
            config_struct[key] = value

    try:
        # Write the configuration out
        files['x-commissaire-host'] = tempfile.mktemp()
        with open(files['x-commissaire-host'], 'w') as f_obj:
            json.dump(config_struct, f_obj, indent=True)

        sub_messages = []
        for mtype, fname in files.items():
            with open(fname, 'r') as f_obj:
                sub_message = MIMEText(
                    f_obj.read(),
                    mtype,
                    sys.getdefaultencoding())
                sub_message.add_header(
                    'Content-Disposition',
                    'attachment; filename="{}"'.format(
                        os.path.basename(fname)))
                sub_messages.append(sub_message)
        # Pull it all together
        combined_message = MIMEMultipart()
        for msg in sub_messages:
            combined_message.attach(msg)

        # Write out the user-data file
        with open(args.outfile, 'w') as out:
            out.write(str(combined_message))
    finally:
        os.unlink(files['x-commissaire-host'])
