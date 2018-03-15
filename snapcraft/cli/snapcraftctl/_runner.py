# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2017 Canonical Ltd
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import functools
import json
import logging
import os
import sys
import urllib

import click
import requests_unixsocket

from snapcraft.internal.errors import SnapcraftEnvironmentError
from snapcraft.cli._errors import exception_handler
from snapcraft.internal import log


@click.group()
@click.option('--debug', '-d', is_flag=True)
@click.pass_context
def run(ctx, debug):
    """snapcraftctl is how snapcraft.yaml can communicate with snapcraft"""

    if debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    # Setup global exception handler (to be called for unhandled exceptions)
    sys.excepthook = functools.partial(exception_handler, debug=debug)

    # In an ideal world, this logger setup would be replaced
    log.configure(log_level=log_level)

    if 'SNAPCRAFTCTL_SOCKET' not in os.environ:
        raise SnapcraftEnvironmentError(
            "'SNAPCRAFTCTL_SOCKET' environment variable must be defined")

    ctx.obj = {'session': requests_unixsocket.Session()}


@run.command()
@click.pass_context
def build(ctx):
    _call_function(ctx, 'build')


def _call_function(ctx, function_name, data=None):
    if not data:
        data = {}

    session = ctx.obj['session']

    response = session.post('http+unix://{}/{}'.format(
            urllib.parse.quote(os.environ['SNAPCRAFTCTL_SOCKET'], safe=''),
            function_name), data=json.dumps(data))






# import requests_unixsocket

# session = requests_unixsocket.Session()

# # Access /path/to/page from /tmp/profilesvc.sock
# r = session.get('http+unix://%2Ftmp%2Fprofilesvc.sock/path/to/page')
# assert r.status_code == 200




# import socket
# import sys

# # Create a UDS socket
# sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

# # Connect the socket to the port where the server is listening
# server_address = './uds_socket'
# print('connecting to {}'.format(server_address))
# try:
#     sock.connect(server_address)
# except socket.error as msg:
#     print(msg)
#     sys.exit(1)

# try:

#     # Send data
#     message = b'This is the message.  It will be repeated.'
#     print('sending {!r}'.format(message))
#     sock.sendall(message)

#     amount_received = 0
#     amount_expected = len(message)

#     while amount_received < amount_expected:
#         data = sock.recv(16)
#         amount_received += len(data)
#         print('received {!r}'.format(data))

# finally:
#     print('closing socket')
#     sock.close()
