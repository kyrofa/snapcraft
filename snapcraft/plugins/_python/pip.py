# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2016-2017 Canonical Ltd
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
import glob
import os
import subprocess
from textwrap import dedent

from snapcraft.common import isurl


_SITECUSTOMIZE_TEMPLATE = dedent("""\
    import site
    import os

    snap_dir = os.getenv("SNAP")
    snapcraft_stage_dir = os.getenv("SNAPCRAFT_STAGE")
    snapcraft_part_install = os.getenv("SNAPCRAFT_PART_INSTALL")

    for d in (snap_dir, snapcraft_stage_dir, snapcraft_part_install):
        if d:
            site_dir = os.path.join(d, "{site_dir}")
            site.addsitedir(site_dir)

    if snap_dir:
        site.ENABLE_USER_SITE = False""")


class Pip:

    def __init__(self, *, python_version, part_dir, install_dir,
                 stage_dir):
        self._python_version = python_version
        self._part_dir = part_dir
        self._install_dir = install_dir
        self._stage_dir = stage_dir

        self._python_command = get_python_command(
            self._python_version, self._stage_dir, self._install_dir)
        self._python_package_dir = os.path.join(self._part_dir, 'packages')

        # Install pip and other tools we need
        self.download(['pip', 'setuptools', 'wheel'])
        self.install(['pip', 'setuptools', 'wheel'])

    def download(self, args):
        os.makedirs(self._python_package_dir, exist_ok=True)
        self._run(['download', '--disable-pip-version-check', '--dest',
                   self._python_package_dir] + args)

    def install(self, args):
        self._run(['install', '--user', '--no-compile', '--no-index',
                   '--disable-pip-version-check', '--find-links',
                   '--ignore-installed', self._python_package_dir] + args)

    def install_from_setup_py(self, *, setup_py, constraints=None,
                              dependency_links=None):
        extra_args = []
        if self.options.constraints:
            if isurl(self.options.constraints):
                constraints = self.options.constraints
            else:
                constraints = os.path.join(self.sourcedir,
                                           self.options.constraints)
            extra_args.extend(['--constraint', constraints])

        if dependency_links:
            extra_args.append('--process-dependency-links')

        commands = self._get_commands(setup_py)

        for command in commands:
            self.download(**command)
        else:
            for command in commands:
                wheels = self.wheel(**command)
                installed = self.list()
                wheel_names = [os.path.basename(w).split('-')[0]
                               for w in wheels]
                # we want to avoid installing what is already provided in
                # stage-packages
                need_install = [k for k in wheel_names if k not in installed]
                self.install(need_install + ['--no-deps', '--upgrade'])
            if os.path.exists(setup_py):
                # pbr and others don't work using `pip install .`
                # LP: #1670852
                # There is also a chance that this setup.py is distutils based
                # in which case we will rely on the `pip install .` ran before
                #  this.
                with contextlib.suppress(subprocess.CalledProcessError):
                    self._setup_tools_install(setup_py)
        return self.list()

    def _run(self, args):
        env = self._get_build_env()
        # since we are using an independent env we need to export this too
        # TODO: figure out if we can move back to common.run
        env['SNAPCRAFT_STAGE'] = self._stage_dir
        env['SNAPCRAFT_PART_INSTALL'] = self._install_dir

        # If python_command is not from stage we don't have pip, which means
        # we are going to need to resort to the pip installed on the system
        # that came from build-packages. This shouldn't be a problem as
        # stage-packages and build-packages should match.
        if not self._python_command.startswith(self._stage_dir):
            env['PYTHONHOME'] = '/usr'

        subprocess.check_call(
            [self._python_command, '-m', 'pip'] + args, env=env)

    def _get_build_env(self):
        env = os.environ.copy()
        env['PYTHONUSERBASE'] = self._install_dir
        if self._python_command.startswith(self._stage_dir):
            env['PYTHONHOME'] = os.path.join(self._stage_dir, 'usr')
        else:
            env['PYTHONHOME'] = os.path.join(self._install_dir, 'usr')

        env['PATH'] = '{}:{}'.format(
            os.path.join(self._install_dir, 'usr', 'bin'),
            os.path.expandvars('$PATH'))

        headers = _get_python_headers(self._python_version, self._stage_dir)
        if headers:
            current_cppflags = env.get('CPPFLAGS', '')
            env['CPPFLAGS'] = '-I{}'.format(headers)
            if current_cppflags:
                env['CPPFLAGS'] = '{} {}'.format(
                    env['CPPFLAGS'], current_cppflags)

        return env

    def _get_commands(self, setup):
        args = []
        cwd = None
        if self.options.requirements:
            requirements = self.options.requirements
            if not isurl(requirements):
                requirements = os.path.join(self.sourcedir,
                                            self.options.requirements)

            args.extend(['--requirement', requirements])
        if os.path.exists(setup):
            args.append('.')
            cwd = os.path.dirname(setup)

        if self.options.python_packages:
            args.extend(self.options.python_packages)

        if args:
            return [dict(args=args, cwd=cwd)]
        else:
            return []

    def _setup_tools_install(self, setup_file):
        command = [
            self._python_command,
            os.path.basename(setup_file), '--no-user-cfg', 'install',
            '--single-version-externally-managed',
            '--user', '--record', 'install.txt']
        self.run(
            command, env=self._get_build_env(),
            cwd=os.path.dirname(setup_file))


def get_python_command(python_version, stage_dir, install_dir):
    python_command = os.path.join('usr', 'bin', python_version)

    # staged as in the stage dir, not from stage-packages
    staged_python = os.path.join(stage_dir, python_command)
    unstaged_python = os.path.join(install_dir, python_command)

    if os.path.exists(staged_python):
        return staged_python
    else:
        return unstaged_python


def _get_python_headers(python_version, stage_dir):
    base_match = os.path.join('usr', 'include', '{}*'.format(python_version))
    unstaged_python = glob.glob(os.path.join(os.path.sep, base_match))
    staged_python = glob.glob(os.path.join(stage_dir, base_match))

    if staged_python:
        return staged_python[0]
    elif unstaged_python:
        return unstaged_python[0]
    else:
        return ''
