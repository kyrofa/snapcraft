# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2015-2017 Canonical Ltd
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

import os
import logging
import subprocess
import sys

from snapcraft.internal import repo

logger = logging.getLogger(__name__)


class Vcs:
    def __init__(self, *, work_dir, ubuntu_sources, project):
        self._work_dir = work_dir
        self._ubuntu_sources = ubuntu_sources
        self._project = project

        self._vcs_install_path = os.path.join(self._work_dir, 'install')

    def setup(self):
        os.makedirs(self._vcs_install_path, exist_ok=True)

        logger.info('Preparing to fetch vcstool...')
        ubuntu = repo.Ubuntu(self._work_dir, sources=self._ubuntu_sources,
                             project_options=self._project)

        logger.info('Fetching vcstool...')
        ubuntu.get(['python3-vcstool'])

        logger.info('Installing vcstool...')
        ubuntu.unpack(self._vcs_install_path)

    def import_repositories(self, path, destination):
        """Import repositories read from a file.

        :param str path: Path to file containing list of repositories.
        :param str destination: Path where repositories will be imported.
        """
        self._run(
            ['import', '--input', path, destination])

    def _run(self, arguments):
        env = os.environ.copy()

        env['PATH'] = env['PATH'] + ':' + os.path.join(
            self._vcs_install_path, 'usr', 'bin')

        env['PYTHONPATH'] = os.path.join(
            self._vcs_install_path, 'usr', 'lib', 'python3', 'dist-packages')

        subprocess.check_call(['vcs'] + arguments, env=env)
