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

import os
import subprocess

import fixtures
from unittest import mock

from testtools.matchers import (
    Contains,
    Equals,
    HasLength,
)

from snapcraft.plugins._python import (
    _pip,
    errors,
)

from snapcraft.tests import fixture_setup
from . import PythonBaseTestCase


class PipRunTestCase(PythonBaseTestCase):

    def setUp(self):
        super().setUp()

        self.fake = fixture_setup.FakePip()
        self.useFixture(self.fake)

    def _assert_expected_enviroment(self, expected_python, headers_path):
        _pip.Pip(
            python_major_version='test',
            part_dir='part_dir',
            install_dir='install_dir',
            stage_dir='stage_dir')

        class check_env():
            def __init__(self, test):
                self.test = test

            def __eq__(self, env):
                self.test.assertThat(env, Contains('PYTHONUSERBASE'))
                self.test.assertThat(
                    env['PYTHONUSERBASE'], Equals('install_dir'))

                self.test.assertThat(env, Contains('PYTHONHOME'))
                if expected_python.startswith('install_dir'):
                    self.test.assertThat(
                        env['PYTHONHOME'], Equals(os.path.join(
                            'install_dir', 'usr')))
                else:
                    self.test.assertThat(
                        env['PYTHONHOME'], Equals(os.path.join(
                            'stage_dir', 'usr')))

                self.test.assertThat(env, Contains('PATH'))
                self.test.assertThat(
                    env['PATH'], Contains(os.path.join(
                        'install_dir', 'usr', 'bin')))

                if headers_path:
                    self.test.assertThat(env, Contains('CPPFLAGS'))
                    self.test.assertThat(
                        env['CPPFLAGS'], Contains('-I{}'.format(headers_path)))

                return True

        self.fake.run_output.assert_called_once_with(
            [expected_python, '-m', 'pip'], env=check_env(self),
            stderr=subprocess.STDOUT)

    def test_environment_part_python_without_headers(self):
        expected_python = self._create_python_binary('install_dir')
        self._assert_expected_enviroment(expected_python, None)

    def test_environment_part_python_with_staged_headers(self):
        expected_python = self._create_python_binary('install_dir')
        # First, create staged headers
        staged_headers = os.path.join(
            'stage_dir', 'usr', 'include', 'pythontest')
        os.makedirs(staged_headers)
        self._assert_expected_enviroment(expected_python, staged_headers)

    @mock.patch('glob.glob')
    def test_environment_part_python_with_host_headers(self, mock_glob):
        host_headers = os.path.join(os.sep, 'usr', 'include', 'pythontest')

        # Fake out glob so it looks like the headers are installed on the host
        def _fake_glob(pattern):
            if pattern.startswith(os.sep):
                return [host_headers]
            return []
        mock_glob.side_effect = _fake_glob

        expected_python = self._create_python_binary('install_dir')
        self._assert_expected_enviroment(expected_python, host_headers)

    def test_environment_staged_python_without_headers(self):
        expected_python = self._create_python_binary('stage_dir')
        self._assert_expected_enviroment(expected_python, None)

    def test_environment_staged_python_with_staged_headers(self):
        # First, create staged headers
        staged_headers = os.path.join(
            'stage_dir', 'usr', 'include', 'pythontest')
        os.makedirs(staged_headers)

        # Also create staged python
        expected_python = self._create_python_binary('stage_dir')

        self._assert_expected_enviroment(expected_python, staged_headers)

    @mock.patch('glob.glob')
    def test_environment_staged_python_with_host_headers(self, mock_glob):
        host_headers = os.path.join(os.sep, 'usr', 'include', 'pythontest')

        # Fake out glob so it looks like the headers are installed on the host
        def _fake_glob(pattern):
            if pattern.startswith(os.sep):
                return [host_headers]
            return []
        mock_glob.side_effect = _fake_glob

        expected_python = self._create_python_binary('stage_dir')
        self._assert_expected_enviroment(expected_python, host_headers)

    def test_with_extra_cppflags(self):
        """Verify that existing CPPFLAGS are preserved"""

        expected_python = self._create_python_binary('install_dir')

        self.useFixture(fixtures.EnvironmentVariable(
                        'CPPFLAGS', '-I/opt/include'))
        _pip.Pip(
            python_major_version='test',
            part_dir='part_dir',
            install_dir='install_dir',
            stage_dir='stage_dir')

        class check_env():
            def __init__(self, test):
                self.test = test

            def __eq__(self, env):
                self.test.assertThat(env, Contains('CPPFLAGS'))
                self.test.assertThat(
                    env['CPPFLAGS'], Contains('-I/opt/include'))

                return True

        self.fake.run_output.assert_has_calls([
            mock.call([expected_python, '-m', 'pip'], env=check_env(self),
                      stderr=subprocess.STDOUT)])


class InitTestCase(PipRunTestCase):

    def setUp(self):
        super().setUp()

        self.command = [self._create_python_binary('install_dir'), '-m', 'pip']

    def test_init_with_pip_installed(self):
        """Test that no attempt is made to reinstall pip"""

        # Since _run doesn't raise an exception indicating pip isn't installed,
        # it must be installed.

        # Verify that no attempt is made to reinstall pip
        _pip.Pip(
            python_major_version='test',
            part_dir='part_dir',
            install_dir='install_dir',
            stage_dir='stage_dir')

        self.fake.run_output.assert_called_once_with(
            self.command, stderr=subprocess.STDOUT, env=mock.ANY)

    def test_init_without_pip_installed(self):
        """Test that the system pip is used to install our own pip"""

        # Raise an exception indicating that pip isn't installed
        def fake_run(command, **kwargs):
            if command == self.command:
                raise subprocess.CalledProcessError(
                    1, 'foo', b'no module named pip')
        self.fake.run_output.side_effect = fake_run

        # Verify that pip is then installed
        _pip.Pip(
            python_major_version='test',
            part_dir='part_dir',
            install_dir='install_dir',
            stage_dir='stage_dir')

        part_pythonhome = os.path.join('install_dir', 'usr')
        host_pythonhome = os.path.join(os.path.sep, 'usr')

        # What we're asserting here:
        # 1. That we test for the installed pip
        # 2. That we then download pip (and associated tools) using host pip
        # 3. That we then install pip (and associated tools) using host pip
        self.assertThat(self.fake.run_output.mock_calls, HasLength(3))
        self.fake.run_output.assert_has_calls([
            mock.call(
                self.command, env=_CheckPythonhomeEnv(self, part_pythonhome),
                stderr=subprocess.STDOUT),
            mock.call(
                _CheckCommand(
                    self, 'download', ['pip', 'setuptools', 'wheel'], []),
                env=_CheckPythonhomeEnv(self, host_pythonhome), cwd=None),
            mock.call(
                _CheckCommand(
                    self, 'install', ['pip', 'setuptools', 'wheel'],
                    ['--ignore-installed']),
                env=_CheckPythonhomeEnv(self, host_pythonhome), cwd=None),
        ])

    def test_init_unexpected_error(self):
        """Test that pip initialization doesn't eat legit errors"""

        # Raises an exception indicating something bad happened
        self.fake.run_output.side_effect = subprocess.CalledProcessError(
            1, 'foo', b'no good, very bad')

        # Verify that pip lets that exception through
        self.assertRaises(
            subprocess.CalledProcessError, _pip.Pip,
            python_major_version='test', part_dir='part_dir',
            install_dir='install_dir', stage_dir='stage_dir')


class PipTestCase(PipRunTestCase):

    def setUp(self):
        super().setUp()

        self._create_python_binary('install_dir')

    def test_clean_packages(self):
        pip = _pip.Pip(
            python_major_version='test',
            part_dir='part_dir',
            install_dir='install_dir',
            stage_dir='stage_dir')

        packages_dir = os.path.join('part_dir', 'python-packages')
        self.assertTrue(os.path.exists(packages_dir))

        # Now verify that asking pip to clean removes its packages
        pip.clean_packages()
        self.assertFalse(os.path.exists(packages_dir))


class PipCommandTestCase(PipTestCase):

    def setUp(self):
        super().setUp()

        self.pip = _pip.Pip(
            python_major_version='test',
            part_dir='part_dir',
            install_dir='install_dir',
            stage_dir='stage_dir')

        # We don't care about anything init did to the mock here: reset it
        self.fake.run_output.reset_mock()


class PipDownloadTestCase(PipCommandTestCase):

    scenarios = [
        ('packages', {
            'packages': ['foo', 'bar'],
            'kwargs': {},
            'expected_args': ['foo', 'bar'],
            'expected_kwargs': {'cwd': None, 'env': mock.ANY},
        }),
        ('setup_py_dir', {
            'packages': [],
            'kwargs': {'setup_py_dir': 'test_setup_py_dir'},
            'expected_args': ['.'],
            'expected_kwargs': {'cwd': 'test_setup_py_dir', 'env': mock.ANY},
        }),
        ('single constraint', {
            'packages': [],
            'kwargs': {'constraints': ['constraint']},
            'expected_args': ['--constraint', 'constraint'],
            'expected_kwargs': {'cwd': None, 'env': mock.ANY},
        }),
        ('multiple constraints', {
            'packages': [],
            'kwargs': {'constraints': ['constraint1', 'constraint2']},
            'expected_args': [
                '--constraint', 'constraint1', '--constraint', 'constraint2'],
            'expected_kwargs': {'cwd': None, 'env': mock.ANY},
        }),
        ('single requirement', {
            'packages': [],
            'kwargs': {'requirements': ['requirement']},
            'expected_args': ['--requirement', 'requirement'],
            'expected_kwargs': {'cwd': None, 'env': mock.ANY},
        }),
        ('multiple requirements', {
            'packages': [],
            'kwargs': {'requirements': ['requirement1', 'requirement2']},
            'expected_args': [
                '--requirement', 'requirement1', '--requirement',
                'requirement2'],
            'expected_kwargs': {'cwd': None, 'env': mock.ANY},
        }),
        ('process dependency links', {
            'packages': [],
            'kwargs': {'process_dependency_links': True},
            'expected_args': ['--process-dependency-links'],
            'expected_kwargs': {'cwd': None, 'env': mock.ANY},
        }),
        ('packages and setup_py_dir', {
            'packages': ['foo', 'bar'],
            'kwargs': {'setup_py_dir': 'test_setup_py_dir'},
            'expected_args': ['foo', 'bar', '.'],
            'expected_kwargs': {'cwd': 'test_setup_py_dir', 'env': mock.ANY},
        }),
    ]

    def _assert_mock_run_with(self, *args, **kwargs):
        common_args = [
            'install_dir/usr/bin/pythontest', '-m', 'pip', 'download',
            '--disable-pip-version-check', '--dest', mock.ANY]
        common_args.extend(*args)
        self.fake.run_output.assert_called_once_with(
            common_args, **kwargs)

    def test_without_packages_or_kwargs_should_noop(self):
        self.pip.download([])
        self.fake.run_output.assert_not_called()

    def test_with_packages_and_kwargs(self):
        self.pip.download(self.packages, **self.kwargs)
        self._assert_mock_run_with(self.expected_args, **self.expected_kwargs)


class PipInstallTestCase(PipCommandTestCase):

    scenarios = [
        ('packages', {
            'packages': ['foo', 'bar'],
            'kwargs': {},
            'expected_args': ['foo', 'bar'],
            'expected_kwargs': {'cwd': None, 'env': mock.ANY},
        }),
        ('setup_py_dir', {
            'packages': [],
            'kwargs': {'setup_py_dir': 'test_setup_py_dir'},
            'expected_args': ['.'],
            'expected_kwargs': {'cwd': 'test_setup_py_dir', 'env': mock.ANY},
        }),
        ('single constraint', {
            'packages': [],
            'kwargs': {'constraints': ['constraint']},
            'expected_args': ['--constraint', 'constraint'],
            'expected_kwargs': {'cwd': None, 'env': mock.ANY},
        }),
        ('multiple constraints', {
            'packages': [],
            'kwargs': {'constraints': ['constraint1', 'constraint2']},
            'expected_args': [
                '--constraint', 'constraint1', '--constraint', 'constraint2'],
            'expected_kwargs': {'cwd': None, 'env': mock.ANY},
        }),
        ('single requirement', {
            'packages': [],
            'kwargs': {'requirements': ['requirement']},
            'expected_args': ['--requirement', 'requirement'],
            'expected_kwargs': {'cwd': None, 'env': mock.ANY},
        }),
        ('multiple requirements', {
            'packages': [],
            'kwargs': {'requirements': ['requirement1', 'requirement2']},
            'expected_args': [
                '--requirement', 'requirement1', '--requirement',
                'requirement2'],
            'expected_kwargs': {'cwd': None, 'env': mock.ANY},
        }),
        ('process dependency links', {
            'packages': [],
            'kwargs': {'process_dependency_links': True},
            'expected_args': ['--process-dependency-links'],
            'expected_kwargs': {'cwd': None, 'env': mock.ANY},
        }),
        ('upgrade', {
            'packages': [],
            'kwargs': {'upgrade': True},
            'expected_args': ['--upgrade'],
            'expected_kwargs': {'cwd': None, 'env': mock.ANY},
        }),
        ('install_deps', {
            'packages': [],
            'kwargs': {'install_deps': False},
            'expected_args': ['--no-deps'],
            'expected_kwargs': {'cwd': None, 'env': mock.ANY},
        }),
        ('ignore_installed', {
            'packages': [],
            'kwargs': {'ignore_installed': True},
            'expected_args': ['--ignore-installed'],
            'expected_kwargs': {'cwd': None, 'env': mock.ANY},
        }),
        ('packages and setup_py_dir', {
            'packages': ['foo', 'bar'],
            'kwargs': {'setup_py_dir': 'test_setup_py_dir'},
            'expected_args': ['foo', 'bar', '.'],
            'expected_kwargs': {'cwd': 'test_setup_py_dir', 'env': mock.ANY},
        }),
    ]

    def _assert_mock_run_with(self, *args, **kwargs):
        common_args = [
            'install_dir/usr/bin/pythontest', '-m', 'pip', 'install', '--user',
            '--no-compile', '--no-index', '--find-links', mock.ANY]
        common_args.extend(*args)
        self.fake.run_output.assert_called_once_with(
            common_args, **kwargs)

    def test_without_packages_or_kwargs_should_noop(self):
        self.pip.install([])
        self.fake.run_output.assert_not_called()

    def test_with_packages_and_kwargs(self):
        self.pip.download(self.packages)
        self.fake.run_output.reset_mock()
        self.pip.install(self.packages, **self.kwargs)
        self._assert_mock_run_with(self.expected_args, **self.expected_kwargs)


class PipWheelTestCase(PipCommandTestCase):

    scenarios = [
        ('packages', {
            'packages': ['foo', 'bar'],
            'kwargs': {},
            'expected_args': ['foo', 'bar'],
            'expected_kwargs': {'cwd': None, 'env': mock.ANY},
        }),
        ('setup_py_dir', {
            'packages': [],
            'kwargs': {'setup_py_dir': 'test_setup_py_dir'},
            'expected_args': ['.'],
            'expected_kwargs': {'cwd': 'test_setup_py_dir', 'env': mock.ANY},
        }),
        ('single constraint', {
            'packages': [],
            'kwargs': {'constraints': ['constraint']},
            'expected_args': ['--constraint', 'constraint'],
            'expected_kwargs': {'cwd': None, 'env': mock.ANY},
        }),
        ('multiple constraints', {
            'packages': [],
            'kwargs': {'constraints': ['constraint1', 'constraint2']},
            'expected_args': [
                '--constraint', 'constraint1', '--constraint', 'constraint2'],
            'expected_kwargs': {'cwd': None, 'env': mock.ANY},
        }),
        ('single requirement', {
            'packages': [],
            'kwargs': {'requirements': ['requirement']},
            'expected_args': ['--requirement', 'requirement'],
            'expected_kwargs': {'cwd': None, 'env': mock.ANY},
        }),
        ('multiple requirements', {
            'packages': [],
            'kwargs': {'requirements': ['requirement1', 'requirement2']},
            'expected_args': [
                '--requirement', 'requirement1', '--requirement',
                'requirement2'],
            'expected_kwargs': {'cwd': None, 'env': mock.ANY},
        }),
        ('process dependency links', {
            'packages': [],
            'kwargs': {'process_dependency_links': True},
            'expected_args': ['--process-dependency-links'],
            'expected_kwargs': {'cwd': None, 'env': mock.ANY},
        }),
        ('packages and setup_py_dir', {
            'packages': ['foo', 'bar'],
            'kwargs': {'setup_py_dir': 'test_setup_py_dir'},
            'expected_args': ['foo', 'bar', '.'],
            'expected_kwargs': {'cwd': 'test_setup_py_dir', 'env': mock.ANY},
        }),
    ]

    def _assert_mock_run_with(self, *args, **kwargs):
        common_args = [
            'install_dir/usr/bin/pythontest', '-m', 'pip', 'wheel',
            '--no-index', '--find-links', mock.ANY, '--wheel-dir', mock.ANY]
        common_args.extend(*args)
        self.fake.run_output.assert_called_once_with(
            common_args, **kwargs)

    def test_without_packages_or_kwargs_should_noop(self):
        self.pip.wheel([])
        self.fake.run_output.assert_not_called()

    def test_with_packages_and_kwargs(self):
        self.pip.wheel(self.packages, **self.kwargs)
        self._assert_mock_run_with(self.expected_args, **self.expected_kwargs)


class PipListTestCase(PipCommandTestCase):

    def test_none(self):
        self.assertFalse(self.pip.list())
        self.fake.run_output.assert_called_once_with([
            'install_dir/usr/bin/pythontest', '-m', 'pip', 'list',
            '--format=json'], env=mock.ANY)

    def test_package(self):
        # First, download something and install it
        self.pip.download(['foo==1.0'])
        self.pip.install(['foo==1.0'])

        self.fake.run_output.reset_mock()

        # Now verify that list works as expected
        self.assertThat(self.pip.list(), Equals({'foo': '1.0'}))
        self.fake.run_output.assert_called_once_with([
            'install_dir/usr/bin/pythontest', '-m', 'pip', 'list',
            '--format=json'], env=mock.ANY)

    def test_missing_name(self):
        self.fake.fake_list_return = '[{"version": "1.0"}]'
        raised = self.assertRaises(
            errors.PipListMissingFieldError, self.pip.list)
        self.assertThat(
            str(raised), Contains("Pip packages json missing 'name' field"))

    def test_missing_version(self):
        self.fake.fake_list_return = '[{"name": "foo"}]'
        raised = self.assertRaises(
            errors.PipListMissingFieldError, self.pip.list)
        self.assertThat(
            str(raised), Contains("Pip packages json missing 'version' field"))

    def test_invalid_json(self):
        self.fake.fake_list_return = '[{]'
        raised = self.assertRaises(
            errors.PipListInvalidJsonError, self.pip.list)
        self.assertThat(
            str(raised), Contains("Pip packages output isn't valid json"))


class _CheckPythonhomeEnv():
    def __init__(self, test, expected_pythonhome):
        self.test = test
        self.expected_pythonhome = expected_pythonhome

    def __eq__(self, env):
        # Verify that we're using the installed pip
        self.test.assertThat(env, Contains('PYTHONHOME'))
        self.test.assertThat(
            env['PYTHONHOME'], Equals(self.expected_pythonhome))

        return True


class _CheckCommand():
    def __init__(self, test, command, packages, flags):
        self.test = test
        self.command = command
        self.packages = packages
        self.flags = flags

    def __eq__(self, command):
        # Not worrying about the command arguments here, those are
        # tested elsewhere. Just want to test that the right command
        # is called with the right packages.
        self.test.assertTrue(command)
        self.test.assertThat(
            command[len(self.test.command)], Equals(self.command))

        for package in self.packages:
            self.test.assertThat(command, Contains(package))

        for flag in self.flags:
            self.test.assertThat(command, Contains(flag))

        return True
