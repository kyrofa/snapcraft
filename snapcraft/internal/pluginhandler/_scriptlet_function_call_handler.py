# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2016 Canonical Ltd
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

import http.server
import json
import socketserver
import uuid


_SNAPCRAFTCTL_SOCKET_TEMPLATE = "/tmp/snapcraft_sock_{id}"


class ScriptletFunctionCallHandler:

    def __init__(self, function_mapping):
        self._function_mapping = function_mapping
        self.socket_path = _SNAPCRAFTCTL_SOCKET_TEMPLATE.format(
            id=uuid.uuid4().hex)
        self._server = socketserver.UnixStreamServer(self.socket_path, RequestHandler)
        self._server._function_mapping = function_mapping

    def check(self):
        self._server.handle_request()

    def close(self):
        self._server.server_close()


class RequestHandler(http.server.BaseHTTPRequestHandler):

    def do_POST(self):
        function_name = self.path.lstrip('/')
        string_kwargs = self.rfile.read(
            int(self.headers['Content-Length'])).decode('utf8')
        kwargs = json.loads(string_kwargs)

        try:
            function = self.server._function_mapping[function_name]
            function(**kwargs)
            self.send_response(200)
        except KeyError as e:
            # This also means a snapcraft developer messed up. Should never
            # be encountered in real life.
            raise ValueError(
                'undefined builtin function: {}'.format(function_name)) from e


# server_address = './uds_socket'

# # Make sure the socket does not already exist
# try:
#     os.unlink(server_address)
# except OSError:
#     if os.path.exists(server_address):
#         raise

# # Create a UDS socket
# sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

# # Bind the socket to the address
# print('starting up on {}'.format(server_address))
# sock.bind(server_address)

# # Listen for incoming connections
# sock.listen(1)

# while True:
#     # Wait for a connection
#     print('waiting for a connection')
#     connection, client_address = sock.accept()
#     try:
#         print('connection from', client_address)

#         # Receive the data in small chunks and retransmit it
#         while True:
#             data = connection.recv(16)
#             print('received {!r}'.format(data))
#             if data:
#                 print('sending data back to the client')
#                 connection.sendall(data)
#             else:
#                 print('no data from', client_address)
#                 break

#     finally:
#         # Clean up the connection
#         connection.close()
