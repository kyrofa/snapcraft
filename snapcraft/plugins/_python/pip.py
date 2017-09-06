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

import collections
import contextlib
import glob
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile

import snapcraft
from snapcraft import (
    common,
    file_utils,
)

logger = logging.getLogger(__name__)


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

        os.makedirs(self._python_package_dir, exist_ok=True)

        self._setup()

    def _setup(self):
        # Check to see if we have our own pip, yet. If not, we need to use the
        # pip on the host (installed via build-packages) to grab our own.
        try:
            self._run([], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            output = e.output.decode(sys.getfilesystemencoding()).strip()
            if 'no module named pip' in output.lower():
                logger.info('Fetching pip, setuptools, and wheel...')
                env = {'PYTHONHOME': '/usr'}

                # Using the host's pip, install our own pip and other tools we
                # need.
                self.download(['pip', 'setuptools', 'wheel'], env=env)
                self.install(['pip', 'setuptools', 'wheel'], env=env)
            else:
                raise e

    def download(self, args, **kwargs):
        if not args:
            return  # No packages to download

        # Using pip with a few special parameters:
        #
        # --disable-pip-version-check: Don't whine if pip is out-of-date with
        #                              the version on pypi.
        # --dest: Download packages into the directory we've set aside for it.
        self._run(['download', '--disable-pip-version-check', '--dest',
                   self._python_package_dir] + args, **kwargs)

    def install(self, args, **kwargs):
        if not args:
            return  # No packages to install

        # Using pip with a few special parameters:
        #
        # --user: Install packages to PYTHONUSERBASE, which we've pointed to
        #         the installdir.
        # --no-compile: Don't compile .pyc files. FIXME: Not sure why
        # --no-index: Don't hit pypi, assume the packages are already
        #             downloaded (i.e. by using `self.download()`)
        # --find-links: Provide the directory into which the packages should
        #               have already been fetched
        # --ignore-installed: If the package is already installed, reinstall
        #                     it. FIXME: Not sure why
        self._run(['install', '--user', '--no-compile', '--no-index',
                   '--find-links', self._python_package_dir,
                   '--ignore-installed'] + args, **kwargs)

    def list(self):
        """Return a dict of installed python packages with versions."""
        output = self._run(['list', '--format=json'])
        packages = collections.OrderedDict()
        for package in json.loads(
                output, object_pairs_hook=collections.OrderedDict):
            packages[package['name']] = package['version']
        return packages

    def wheel(self, args, **kwargs):
        wheels = []
        with tempfile.TemporaryDirectory() as temp_dir:

            # Using pip with a few special parameters:
            #
            # --no-index: Don't hit pypi, assume the packages are already
            #             downloaded (i.e. by using `self.download()`)
            # --find-links: Provide the directory into which the packages
            #               should have already been fetched
            # --wheel-dir: Build wheels into a temporary working area rather
            #              rather than cwd. We'll copy them over. FIXME: Why
            #              not just build them straight in the package_dir?
            self._run(['wheel', '--no-index', '--find-links',
                       self._python_package_dir, '--wheel-dir',
                       temp_dir] + args, **kwargs)
            wheels = os.listdir(temp_dir)
            for wheel in wheels:
                file_utils.link_or_copy(
                    os.path.join(temp_dir, wheel),
                    os.path.join(self._python_package_dir, wheel))

        return [os.path.join(self._python_package_dir, wheel)
                for wheel in wheels]

    def install_from_setup_py(self, *, setup_py, constraints=None,
                              dependency_links=None, requirements=None):
        extra_args = []
        cwd = None
        if os.path.exists(setup_py):
            extra_args.append('.')
            cwd = os.path.dirname(setup_py)
        if constraints:
            extra_args.extend(['--constraint', constraints])
        if dependency_links:
            extra_args.append('--process-dependency-links')
        if requirements:
            if not common.isurl(requirements):
                requirements = os.path.join(self.sourcedir, requirements)
            extra_args.extend(['--requirement', requirements])

        if extra_args:
            self.download(extra_args, cwd=cwd)
            wheels = self.wheel(extra_args, cwd=cwd)
            installed = self.list()
            wheel_names = [os.path.basename(w).split('-')[0]
                           for w in wheels]
            # we want to avoid installing what is already provided in
            # stage-packages
            need_install = [k for k in wheel_names if k not in installed]
            self.install(
                need_install + ['--no-deps', '--upgrade'] + extra_args,
                cwd=cwd)

            if os.path.exists(setup_py):
                # pbr and others don't work using `pip install .`
                # LP: #1670852
                # There is also a chance that this setup.py is distutils based
                # in which case we will rely on the `pip install .` ran before
                #  this.
                with contextlib.suppress(subprocess.CalledProcessError):
                    self._setup_tools_install(setup_py)
        return self.list()

    def clean_packages(self):
        with contextlib.suppress(FileNotFoundError):
            shutil.rmtree(self._python_package_dir)

    def _run(self, args, **kwargs):
        env = self._get_build_env()
        if 'env' in kwargs:
            env.update(kwargs.pop('env'))

        return snapcraft.internal.common.run_output(
            [self._python_command, '-m', 'pip'] + args, env=env,
            **kwargs)

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

    def _setup_tools_install(self, setup_file):
        command = [
            self._python_command,
            os.path.basename(setup_file), '--no-user-cfg', 'install',
            '--single-version-externally-managed',
            '--user', '--record', 'install.txt']
        snapcraft.internal.common.run(
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
