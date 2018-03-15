# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2016, 2018 Canonical Ltd
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

import contextlib
import json
import os
import shlex
import subprocess
import sys
import tempfile
import textwrap
from typing import Any, Callable, Dict  # noqa

from snapcraft.internal import (
    common,
    errors,
)

from ._scriptlet_function_call_handler import ScriptletFunctionCallHandler


class Runner:
    """The Runner class is responsible for orchestrating scriptlets."""

    # FIXME: Need to quote builtin_functions typing because of
    # https://github.com/python/typing/issues/259 which is fixed in Python
    # 3.5.3.
    def __init__(self, *, part_properties: Dict[str, Any], builddir: str,
                 builtin_functions: 'Dict[str, Callable[..., None]]') -> None:
        """Create a new Runner.
        :param dict part_properties: YAML properties set for this part.
        :param str builddir: The build directory for this part.
        :param dict builtin_functions: Dict of builtin function names to
                                       actual callables.
        """
        self._builddir = builddir
        self._builtin_functions = builtin_functions

        self._prepare_scriptlet = part_properties.get('prepare')
        self._build_scriptlet = part_properties.get('build')
        self._install_scriptlet = part_properties.get('install')

    def prepare(self) -> None:
        """Run prepare scriptlet."""
        if self._prepare_scriptlet:
            self._run_scriptlet(
                'prepare', self._prepare_scriptlet, self._builddir)

    def build(self) -> None:
        """Run build scriptlet."""
        if self._build_scriptlet:
            self._run_scriptlet(
                'build', self._build_scriptlet, self._builddir)

    def install(self) -> None:
        """Run install scriptlet."""
        if self._install_scriptlet:
            self._run_scriptlet(
                'install', self._install_scriptlet, self._builddir)

    def _run_scriptlet(self, scriptlet_name: str, scriptlet: str,
                       workdir: str) -> None:
        function_handler = ScriptletFunctionCallHandler(self._builtin_functions)

        with tempfile.TemporaryDirectory() as tempdir:
            call_fifo = _NonBlockingFifo(
                path=os.path.join(tempdir, 'function_call'),
                permissions=os.O_RDONLY)
            feedback_fifo = _NonBlockingFifo(
                path=os.path.join(tempdir, 'call_feedback'),
                permissions=os.O_WRONLY)

            script = textwrap.dedent("""\
                export SNAPCRAFTCTL_SOCKET={socket_path}
                {env}
                {scriptlet}
            """.format(
                socket_path=function_handler.socket_path, env=common.assemble_env(),
                scriptlet=scriptlet))

            process = subprocess.Popen(
                ['/bin/sh', '-e', '-c', script], cwd=self._builddir)

            status = None
            try:
                while status is None:
                    function_handler.check()
                    status = process.poll()
            finally:
                function_handler.close()

            if status:
                raise errors.ScriptletRunError(
                    scriptlet_name=scriptlet_name, code=status)

    def _handle_builtin_function(self, scriptlet_name, function_call):
        function_call_components = shlex.split(function_call)
        if len(function_call_components) == 0:
            # This means a snapcraft developer messed up. Should never be
            # encountered in real life.
            raise ValueError(
                '{!r} scriptlet somehow managed to call a function without '
                'providing a function name: {}'.format(
                    scriptlet_name, function_call))

        if len(function_call_components) > 2:
            # This also means a snapcraft developer messed up. Should never be
            # encountered in real life.
            raise ValueError(
                '{!r} scriptlet called a function with too many args (a max '
                'of 1 arg is supported): {}'.format(
                    scriptlet_name, function_call))

        function_name = function_call_components[0]
        kwargs = {}
        if len(function_call_components) == 2:
            try:
                kwargs = json.loads(function_call_components[1])
            except json.decoder.JSONDecodeError as e:
                # This also means a snapcraft developer messed up. Should
                # never be encountered in real life.
                raise ValueError(
                    '{!r} scriptlet called a function with its arg as invalid '
                    'json: {}'.format(scriptlet_name, function_call)) from e

        try:
            function = self._builtin_functions[function_name]
            function(**kwargs)
        except KeyError as e:
            # This also means a snapcraft developer messed up. Should never
            # be encountered in real life.
            raise ValueError(
                '{!r} scriptlet called an undefined builtin function: '
                '{}'.format(scriptlet_name, function_call)) from e


class _NonBlockingFifo:

    def __init__(self, *, path: str, permissions) -> None:
        os.mkfifo(path)
        self.path = path
        self._permissions = permissions
        self._fd = None  # type: int

    def read(self) -> str:
        total_read = ''
        if self._fifo_open():
            with contextlib.suppress(BlockingIOError):
                value = os.read(self._fd, 1024)
                while value:
                    total_read += value.decode(sys.getfilesystemencoding())
                    value = os.read(self._fd, 1024)
        return total_read

    def write(self, data: str) -> int:
        if self._fifo_open():
            return os.write(self._fd, data.encode(sys.getfilesystemencoding()))
        return 0

    def close(self) -> None:
        if self._fd is not None:
            os.close(self._fd)

    def _fifo_open(self) -> bool:
        """Return whether or not fifo is open. Attempt to open if not."""

        if self._fd is None:
            try:
                # Read-only should work, but write-only may toss OSErrors if
                # reader isn't hooked up.
                self._fd = os.open(
                    self.path, self._permissions | os.O_NONBLOCK)
            except OSError:
                return False
        return True
