# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2016-2018 Canonical Ltd
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

import multiprocessing
import os

from testtools.matchers import Contains, FileContains, FileExists

from tests import integration


class ScriptletTestCase(integration.TestCase):

    def test_pre_build_scriptlet(self):
        self.run_snapcraft('build', 'scriptlet-pre-build')

        installdir = os.path.join(
            self.parts_dir, 'pre-build-scriptlet-test', 'install')
        touch_file_path = os.path.join(installdir, 'prepared')
        self.assertThat(touch_file_path, FileExists())

    def test_build_scriptlet(self):
        self.run_snapcraft('build', 'scriptlet-build')

        partdir = os.path.join(self.parts_dir, 'build-scriptlet-test')
        builddir = os.path.join(partdir, 'build')
        installdir = os.path.join(partdir, 'install')

        touch_file_path = os.path.join(builddir, 'build-build')
        self.assertThat(touch_file_path, FileExists())
        jobs_file_name = 'jobs-{}'.format(multiprocessing.cpu_count())
        touch_file_path = os.path.join(builddir, jobs_file_name)
        self.assertThat(touch_file_path, FileExists())
        touch_file_path = os.path.join(installdir, 'build-install')
        self.assertThat(touch_file_path, FileExists())

    def test_post_build_scriptlet(self):
        self.run_snapcraft('build', 'scriptlet-post-build')

        installdir = os.path.join(
            self.parts_dir, 'post-build-scriptlet-test', 'install')
        touch_file_path = os.path.join(installdir, 'build-done')
        self.assertThat(touch_file_path, FileExists())
        echoed_file_path = os.path.join(installdir, 'config.ini')
        self.assertThat(echoed_file_path, FileExists())
        self.assertThat(echoed_file_path,
                        FileContains('config-key=config-value\n'))
        arch_triplet_file = os.path.join(installdir, 'lib',
                                         self.arch_triplet, 'lib.so')
        self.assertThat(arch_triplet_file, FileExists())


class DeprecatedScriptletsTestCase(integration.TestCase):

    def test_prepare_scriptlet_deprecated(self):
        output = self.run_snapcraft('build', 'scriptlet-prepare')

        installdir = os.path.join(
            self.parts_dir, 'prepare-scriptlet-test', 'install')
        touch_file_path = os.path.join(installdir, 'prepared')
        self.assertThat(touch_file_path, FileExists())

        # Verify that the `prepare` keyword is deprecated.
        self.assertThat(
            output, Contains(
                "DEPRECATED: The 'prepare' keyword has been replaced by "
                "'pre-build'"))

    def test_install_scriptlet_deprecated(self):
        output = self.run_snapcraft('build', 'scriptlet-install')

        installdir = os.path.join(
            self.parts_dir, 'install-scriptlet-test', 'install')
        touch_file_path = os.path.join(installdir, 'build-done')
        self.assertThat(touch_file_path, FileExists())
        echoed_file_path = os.path.join(installdir, 'config.ini')
        self.assertThat(echoed_file_path, FileExists())
        self.assertThat(echoed_file_path,
                        FileContains('config-key=config-value\n'))
        arch_triplet_file = os.path.join(installdir, 'lib',
                                         self.arch_triplet, 'lib.so')
        self.assertThat(arch_triplet_file, FileExists())

        # Verify that the `install` keyword is deprecated.
        self.assertThat(
            output, Contains(
                "DEPRECATED: The 'install' keyword has been replaced by "
                "'post-build'"))
