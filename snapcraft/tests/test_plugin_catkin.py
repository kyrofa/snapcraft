# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2015 Canonical Ltd
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
import os.path
import subprocess
import builtins

from unittest import mock

from snapcraft import (repo,
                       tests)
from snapcraft.plugins import catkin


class _CompareLists():
    def __init__(self, test, expected):
        self.test = test
        self.expected = expected

    def __eq__(self, packages):
        self.test.assertEqual(len(packages), len(self.expected),
                              'Expected {} packages to be installed, '
                              'got {}'.format(len(self.expected),
                                              len(packages)))

        for expectation in self.expected:
            self.test.assertTrue(expectation in packages,
                                 'Expected "{}" to be installed'
                                 .format(expectation))

        return True


#class CatkinPluginTestCase(tests.TestCase):

#    def setUp(self):
#        super().setUp()

#        class props:
#            rosdistro = 'indigo'
#            catkin_packages = ['my_package']
#            source_space = 'src'
#            source_subdir = None

#        self.properties = props()

#        patcher = mock.patch('snapcraft.repo.Ubuntu')
#        self.ubuntu_mock = patcher.start()
#        self.addCleanup(patcher.stop)

#        patcher = mock.patch(
#            'snapcraft.plugins.catkin._find_extra_dependencies')
#        self.extra_dependencies_mock = patcher.start()
#        self.addCleanup(patcher.stop)

#        patcher = mock.patch(
#            'snapcraft.plugins.catkin._find_system_dependencies')
#        self.dependencies_mock = patcher.start()
#        self.addCleanup(patcher.stop)

#    def test_schema(self):
#        schema = catkin.CatkinPlugin.schema()

#        # Check rosdistro property
#        properties = schema['properties']
#        self.assertTrue('rosdistro' in properties,
#                        'Expected "rosdistro" to be included in properties')

#        rosdistro = properties['rosdistro']
#        self.assertTrue('type' in rosdistro,
#                        'Expected "type" to be included in "rosdistro"')
#        self.assertTrue('default' in rosdistro,
#                        'Expected "default" to be included in "rosdistro"')

#        rosdistro_type = rosdistro['type']
#        self.assertEqual(rosdistro_type, 'string',
#                         'Expected "rosdistro" "type" to be "string", but it '
#                         'was "{}"'.format(rosdistro_type))

#        rosdistro_default = rosdistro['default']
#        self.assertEqual(rosdistro_default, 'indigo',
#                         'Expected "rosdistro" "default" to be "indigo", but '
#                         'it was "{}"'.format(rosdistro_default))

#        # Check catkin-packages property
#        self.assertTrue('catkin-packages' in properties,
#                        'Expected "catkin-packages" to be included in '
#                        'properties')

#        catkin_packages = properties['catkin-packages']
#        self.assertTrue('type' in catkin_packages,
#                        'Expected "type" to be included in "catkin-packages"')
#        self.assertTrue('default' in catkin_packages,
#                        'Expected "default" to be included in '
#                        '"catkin-packages"')
#        self.assertTrue('minitems' in catkin_packages,
#                        'Expected "minitems" to be included in '
#                        '"catkin-packages"')
#        self.assertTrue('uniqueItems' in catkin_packages,
#                        'Expected "uniqueItems" to be included in '
#                        '"catkin-packages"')
#        self.assertTrue('items' in catkin_packages,
#                        'Expected "items" to be included in "catkin-packages"')

#        catkin_packages_type = catkin_packages['type']
#        self.assertEqual(catkin_packages_type, 'array',
#                         'Expected "catkin-packages" "type" to be "aray", but '
#                         'it was "{}"'.format(catkin_packages_type))

#        catkin_packages_default = catkin_packages['default']
#        self.assertEqual(catkin_packages_default, [],
#                         'Expected "catkin-packages" "default" to be [], but '
#                         'it was {}'.format(catkin_packages_default))

#        catkin_packages_minitems = catkin_packages['minitems']
#        self.assertEqual(catkin_packages_minitems, 1,
#                         'Expected "catkin-packages" "minitems" to be 1, but '
#                         'it was {}'.format(catkin_packages_minitems))

#        self.assertTrue(catkin_packages['uniqueItems'])

#        catkin_packages_items = catkin_packages['items']
#        self.assertTrue('type' in catkin_packages_items,
#                        'Expected "type" to be included in "catkin-packages" '
#                        '"items"')

#        catkin_packages_items_type = catkin_packages_items['type']
#        self.assertEqual(catkin_packages_items_type, 'string',
#                         'Expected "catkin-packages" "item" "type" to be '
#                         '"string", but it was "{}"'
#                         .format(catkin_packages_items_type))

#        # Check source-space property
#        self.assertTrue('source-space' in properties,
#                        'Expected "source-space" to be included in properties')

#        source_space = properties['source-space']
#        self.assertTrue('type' in rosdistro,
#                        'Expected "type" to be included in "source-space"')
#        self.assertTrue('default' in rosdistro,
#                        'Expected "default" to be included in "source-space"')

#        source_space_type = source_space['type']
#        self.assertEqual(source_space_type, 'string',
#                         'Expected "source-space" "type" to be "string", but '
#                         'it was "{}"'.format(source_space_type))

#        source_space_default = source_space['default']
#        self.assertEqual(source_space_default, 'src',
#                         'Expected "source-space" "default" to be "src", but '
#                         'it was "{}"'.format(source_space_default))

#        # Check required
#        self.assertTrue('catkin-packages' in schema['required'],
#                        'Expected "catkin-packages" to be included in '
#                        '"required"')

#    def test_pull_debian_dependencies(self):
#        plugin = catkin.CatkinPlugin('test-part', self.properties)
#        os.makedirs(os.path.join(plugin.sourcedir, 'src'))

#        self.dependencies_mock.return_value = ['foo', 'bar', 'baz']

#        plugin.pull()

#        # Verify that dependencies were found as expected
#        self.dependencies_mock.assert_called_once_with(
#            {'my_package'}, self.properties.rosdistro,
#            os.path.join(plugin.sourcedir, 'src'),
#            os.path.join(plugin.partdir, 'rosdep'),
#            plugin.PLUGIN_STAGE_SOURCES)

#        # Verify that the dependencies were installed
#        self.ubuntu_mock.return_value.get.assert_called_with(
#            _CompareLists(self, ['foo', 'bar', 'baz']))
#        self.ubuntu_mock.return_value.unpack.assert_called_with(
#            plugin.installdir)

#    def test_pull_local_dependencies(self):
#        self.properties.catkin_packages.append('package_2')

#        plugin = catkin.CatkinPlugin('test-part', self.properties)
#        os.makedirs(os.path.join(plugin.sourcedir, 'src'))

#        # No system dependencies (only local)
#        self.dependencies_mock.return_value = []

#        plugin.pull()

#        # Verify that dependencies were found as expected
#        self.dependencies_mock.assert_called_once_with(
#            {'my_package', 'package_2'}, self.properties.rosdistro,
#            os.path.join(plugin.sourcedir, 'src'),
#            os.path.join(plugin.partdir, 'rosdep'),
#            plugin.PLUGIN_STAGE_SOURCES)

#        # Verify that no .deb packages were installed
#        self.assertTrue(mock.call().unpack(plugin.installdir) not in
#                        self.ubuntu_mock.mock_calls)

#    def test_valid_catkin_workspace_src(self):
#        # sourcedir is expected to be the root of the Catkin workspace. Since
#        # it contains a 'src' directory, this is a valid Catkin workspace.
#        try:
#            plugin = catkin.CatkinPlugin('test-part', self.properties)
#            os.makedirs(os.path.join(plugin.sourcedir, 'src'))
#            plugin.pull()
#        except FileNotFoundError:
#            self.fail('Unexpectedly raised an exception when the Catkin '
#                      'workspace was valid')

#    def test_invalid_catkin_workspace_no_src(self):
#        # sourcedir is expected to be the root of the Catkin workspace. Since
#        # it does not contain a `src` folder and `source-space` is 'src', this
#        # should fail.
#        with self.assertRaises(FileNotFoundError) as raised:
#            plugin = catkin.CatkinPlugin('test-part', self.properties)
#            plugin.pull()

#        self.assertEqual(
#            str(raised.exception),
#            'Unable to find package path: "{}"'.format(os.path.join(
#                plugin.sourcedir, 'src')))

#    def test_valid_catkin_workspace_source_space(self):
#        self.properties.source_space = 'foo'

#        # sourcedir is expected to be the root of the Catkin workspace.
#        # Normally this would mean it contained a `src` directory, but it can
#        # be remapped via the `source-space` key.
#        try:
#            plugin = catkin.CatkinPlugin('test-part', self.properties)
#            os.makedirs(os.path.join(plugin.sourcedir,
#                        self.properties.source_space))
#            plugin.pull()
#        except FileNotFoundError:
#            self.fail('Unexpectedly raised an exception when the Catkin '
#                      'src was remapped in a valid manner')

#    def test_invalid_catkin_workspace_invalid_source_space(self):
#        self.properties.source_space = 'foo'

#        # sourcedir is expected to be the root of the Catkin workspace. Since
#        # it does not contain a `src` folder and source_space wasn't
#        # specified, this should fail.
#        with self.assertRaises(FileNotFoundError) as raised:
#            plugin = catkin.CatkinPlugin('test-part', self.properties)
#            plugin.pull()

#        self.assertEqual(
#            str(raised.exception),
#            'Unable to find package path: "{}"'.format(os.path.join(
#                plugin.sourcedir, self.properties.source_space)))

#    def test_invalid_catkin_workspace_source_space_same_as_source(self):
#        self.properties.source_space = '.'

#        # sourcedir is expected to be the root of the Catkin workspace. Since
#        # source_space was specified to be the same as the root, this should
#        # fail.
#        with self.assertRaises(RuntimeError) as raised:
#            catkin.CatkinPlugin('test-part', self.properties).pull()

#        self.assertEqual(str(raised.exception),
#                         'source-space cannot be the root of the Catkin '
#                         'workspace')

#    @mock.patch.object(catkin.CatkinPlugin, 'run')
#    @mock.patch.object(catkin.CatkinPlugin, '_run_in_bash')
#    @mock.patch.object(catkin.CatkinPlugin, 'run_output', return_value='foo')
#    @mock.patch.object(catkin.CatkinPlugin, '_prepare_build')
#    @mock.patch.object(catkin.CatkinPlugin, '_finish_build')
#    def test_build(self, finish_build_mock, prepare_build_mock,
#                   run_output_mock, bashrun_mock, run_mock):
#        plugin = catkin.CatkinPlugin('test-part', self.properties)
#        os.makedirs(os.path.join(plugin.sourcedir, 'src'))

#        plugin.build()

#        prepare_build_mock.assert_called_once_with()

#        # Matching like this for order independence (otherwise it would be
#        # quite fragile)
#        class check_build_command():
#            def __eq__(self, args):
#                command = ' '.join(args)
#                return (
#                    args[0] == 'catkin_make_isolated' and
#                    '--install' in command and
#                    '--pkg my_package' in command and
#                    '--directory {}'.format(plugin.builddir) in command and
#                    '--install-space {}'.format(plugin.rosdir) in command and
#                    '--source-space {}'.format(os.path.join(
#                        plugin.builddir,
#                        plugin.options.source_space)) in command)

#        bashrun_mock.assert_called_with(check_build_command())

#        self.assertFalse(
#            self.dependencies_mock.called,
#            'Dependencies should have been discovered in the pull() step')

#        finish_build_mock.assert_called_once_with()

#    @mock.patch.object(catkin.CatkinPlugin, 'run')
#    @mock.patch.object(catkin.CatkinPlugin, '_run_in_bash')
#    @mock.patch.object(catkin.CatkinPlugin, 'run_output', return_value='foo')
#    @mock.patch.object(catkin.CatkinPlugin, '_prepare_build')
#    @mock.patch.object(catkin.CatkinPlugin, '_finish_build')
#    def test_build_multiple(self, finish_build_mock, prepare_build_mock,
#                            run_output_mock, bashrun_mock, run_mock):
#        self.properties.catkin_packages.append('package_2')

#        plugin = catkin.CatkinPlugin('test-part', self.properties)
#        os.makedirs(os.path.join(plugin.sourcedir, 'src'))

#        plugin.build()

#        class check_pkg_arguments():
#            def __init__(self, test):
#                self.test = test

#            def __eq__(self, args):
#                index = args.index('--pkg')
#                packages = args[index+1:index+3]
#                if 'my_package' not in packages:
#                    self.test.fail('Expected "my_package" to be installed '
#                                   'within the same command as "package_2"')

#                if 'package_2' not in packages:
#                    self.test.fail('Expected "package_2" to be installed '
#                                   'within the same command as "my_package"')

#                return True

#        bashrun_mock.assert_called_with(check_pkg_arguments(self))

#        self.assertFalse(
#            self.dependencies_mock.called,
#            'Dependencies should have been discovered in the pull() step')

#        finish_build_mock.assert_called_once_with()

#    @mock.patch.object(catkin.CatkinPlugin, 'run')
#    @mock.patch.object(catkin.CatkinPlugin, 'run_output', return_value='foo')
#    def test_build_runs_in_bash(self, run_output_mock, run_mock):
#        plugin = catkin.CatkinPlugin('test-part', self.properties)
#        os.makedirs(os.path.join(plugin.sourcedir, 'src'))

#        plugin.build()

#        run_mock.assert_has_calls([
#            mock.call(['/bin/bash', mock.ANY], cwd=mock.ANY)
#        ])

#    @mock.patch.object(catkin.CatkinPlugin, '_prepare_build')
#    @mock.patch.object(catkin.CatkinPlugin, '_finish_build')
#    def test_build_encompasses_source_space(self, finish_mock, prepare_mock):
#        self.properties.catkin_packages = []
#        plugin = catkin.CatkinPlugin('test-part', self.properties)
#        os.makedirs(os.path.join(plugin.sourcedir, 'src'))

#        plugin.build()

#        self.assertTrue(os.path.isdir(os.path.join(plugin.builddir, 'src')))

#    @mock.patch.object(catkin.CatkinPlugin, '_prepare_build')
#    @mock.patch.object(catkin.CatkinPlugin, '_finish_build')
#    def test_build_encompasses_remapped_source_space(self, finish_mock,
#                                                     prepare_mock):
#        self.properties.catkin_packages = []
#        self.properties.source_space = 'foo'
#        plugin = catkin.CatkinPlugin('test-part', self.properties)
#        os.makedirs(os.path.join(plugin.sourcedir, 'foo'))

#        plugin.build()

#        self.assertTrue(os.path.isdir(os.path.join(plugin.builddir, 'foo')))

#    @mock.patch.object(catkin.CatkinPlugin, '_prepare_build')
#    @mock.patch.object(catkin.CatkinPlugin, '_finish_build')
#    def test_build_accounts_for_source_subdir(self, finish_mock, prepare_mock):
#        self.properties.catkin_packages = []
#        self.properties.source_subdir = 'workspace'
#        self.properties.source_space = 'foo'
#        plugin = catkin.CatkinPlugin('test-part', self.properties)
#        os.makedirs(os.path.join(plugin.sourcedir, 'workspace', 'foo'))

#        plugin.build()

#        self.assertTrue(os.path.isdir(os.path.join(plugin.builddir, 'foo')))

#    def test_prepare_build(self):
#        plugin = catkin.CatkinPlugin('test-part', self.properties)
#        os.makedirs(os.path.join(plugin.rosdir, 'test'))

#        # Place a few .cmake files with incorrect paths, and some files that
#        # shouldn't be changed.
#        files = [
#            {
#                'path': 'fooConfig.cmake',
#                'contents': '"/usr/lib/foo"',
#                'expected': '"{}/usr/lib/foo"'.format(plugin.installdir),
#            },
#            {
#                'path': 'bar.cmake',
#                'contents': '"/usr/lib/bar"',
#                'expected': '"/usr/lib/bar"',
#            },
#            {
#                'path': 'test/bazConfig.cmake',
#                'contents': '"/test/baz;/usr/lib/baz"',
#                'expected': '"{0}/test/baz;{0}/usr/lib/baz"'.format(
#                    plugin.installdir),
#            },
#            {
#                'path': 'test/quxConfig.cmake',
#                'contents': 'qux',
#                'expected': 'qux',
#            },
#            {
#                'path': 'test/installedConfig.cmake',
#                'contents': '"{}/foo"'.format(plugin.installdir),
#                'expected': '"{}/foo"'.format(plugin.installdir),
#            }
#        ]

#        for fileInfo in files:
#            with open(os.path.join(plugin.rosdir, fileInfo['path']), 'w') as f:
#                f.write(fileInfo['contents'])

#        plugin._prepare_build()

#        for fileInfo in files:
#            with open(os.path.join(plugin.rosdir, fileInfo['path']), 'r') as f:
#                self.assertEqual(f.read(), fileInfo['expected'])

#    @mock.patch.object(catkin.CatkinPlugin, 'run')
#    @mock.patch.object(catkin.CatkinPlugin, 'run_output', return_value='foo')
#    def test_finish_build_python_shebangs(self, run_output_mock, run_mock):
#        plugin = catkin.CatkinPlugin('test-part', self.properties)
#        os.makedirs(os.path.join(plugin.rosdir, 'bin'))

#        # Place a few files with bad shebangs, and some files that shouldn't be
#        # changed.
#        files = [
#            {
#                'path': os.path.join(plugin.rosdir, '_setup_util.py'),
#                'contents': '#!/foo/bar/baz/python',
#                'expected': '#!/usr/bin/env python',
#            },
#            {
#                'path': os.path.join(plugin.rosdir, 'bin/catkin_find'),
#                'contents': '#!/foo/baz/python',
#                'expected': '#!/usr/bin/env python',
#            },
#            {
#                'path': os.path.join(plugin.rosdir, 'foo'),
#                'contents': 'foo',
#                'expected': 'foo',
#            }
#        ]

#        for file_info in files:
#            with open(file_info['path'], 'w') as f:
#                f.write(file_info['contents'])

#        plugin._finish_build()

#        for file_info in files:
#            with open(os.path.join(plugin.rosdir,
#                                   file_info['path']), 'r') as f:
#                self.assertEqual(f.read(), file_info['expected'])

#    @mock.patch.object(catkin.CatkinPlugin, 'run')
#    @mock.patch.object(catkin.CatkinPlugin, 'run_output', return_value='foo')
#    def test_finish_build_absolute_python(self, run_output_mock, run_mock):
#        plugin = catkin.CatkinPlugin('test-part', self.properties)
#        os.makedirs(os.path.join(plugin.rosdir, 'etc', 'catkin', 'profile.d'))

#        ros_profile = os.path.join(plugin.rosdir, 'etc', 'catkin', 'profile.d',
#                                   '10.ros.sh')

#        # Place 10.ros.sh with an absolute path to python
#        with open(ros_profile, 'w') as f:
#            f.write('/usr/bin/python foo')

#        plugin._finish_build()

#        # Verify that the absolute path in 10.ros.sh was rewritten correctly
#        with open(ros_profile, 'r') as f:
#            self.assertEqual(f.read(), 'python foo',
#                             'The absolute path to python was not replaced as '
#                             'expected')

#    @mock.patch.object(catkin.CatkinPlugin, 'run')
#    @mock.patch.object(catkin.CatkinPlugin, 'run_output', return_value='foo')
#    def test_finish_build_binary(self, run_output_mock, run_mock):
#        plugin = catkin.CatkinPlugin('test-part', self.properties)
#        os.makedirs(plugin.rosdir)

#        # Place a file to be discovered by _finish_build().
#        open(os.path.join(plugin.rosdir, 'foo'), 'w').close()

#        file_mock = mock.mock_open()
#        with mock.patch.object(builtins, 'open', file_mock):
#            # Reading a binary file may throw a UnicodeDecodeError. Make sure
#            # that's handled.
#            file_mock.return_value.read.side_effect = UnicodeDecodeError(
#                'foo', b'bar', 1, 2, 'baz')
#            try:
#                plugin._finish_build()
#            except UnicodeDecodeError:
#                self.fail('Expected _finish_build to handle binary files')

#    @mock.patch.object(catkin.CatkinPlugin, 'run')
#    @mock.patch.object(catkin.CatkinPlugin, 'run_output', return_value='foo')
#    def test_finish_build_cmake_prefix_path(self, run_output_mock, run_mock):
#        plugin = catkin.CatkinPlugin('test-part', self.properties)

#        setup_file = os.path.join(plugin.rosdir, '_setup_util.py')
#        os.makedirs(os.path.dirname(setup_file))

#        with open(setup_file, 'w') as f:
#            f.write("CMAKE_PREFIX_PATH = '{0}/{1};{0}\n".format(
#                plugin.rosdir, plugin.options.rosdistro))

#        plugin._finish_build()

#        expected = 'CMAKE_PREFIX_PATH = []\n'

#        with open(setup_file, 'r') as f:
#            self.assertEqual(
#                f.read(), expected,
#                'The absolute path to python or the CMAKE_PREFIX_PATH '
#                'was not replaced as expected')

#    @mock.patch.object(catkin.CatkinPlugin, 'run_output', return_value='bar')
#    def test_run_environment(self, run_mock):
#        plugin = catkin.CatkinPlugin('test-part', self.properties)

#        python_path = os.path.join(
#            plugin.installdir, 'usr', 'lib', 'python2.7', 'dist-packages')
#        os.makedirs(python_path)

#        environment = plugin.env(plugin.installdir)

#        self.assertTrue(
#            'PYTHONPATH={}:$PYTHONPATH'.format(python_path) in
#            environment, environment)

#        self.assertTrue('ROS_MASTER_URI=http://localhost:11311' in environment)

#        self.assertTrue('ROS_HOME=$SNAP_USER_DATA/ros' in environment)

#        self.assertTrue('_CATKIN_SETUP_DIR={}'.format(os.path.join(
#            plugin.installdir, 'opt', 'ros', self.properties.rosdistro))
#            in environment)

#        self.assertTrue(
#            '. {}'.format(plugin.installdir, 'opt', 'ros', 'setup.sh') in
#            '\n'.join(environment), 'Expected ROS\'s setup.sh to be sourced')

#    @mock.patch.object(catkin.CatkinPlugin, 'run_output', return_value='bar')
#    def test_run_environment_no_python(self, run_mock):
#        plugin = catkin.CatkinPlugin('test-part', self.properties)

#        python_path = os.path.join(
#            plugin.installdir, 'usr', 'lib', 'python2.7', 'dist-packages')

#        environment = plugin.env(plugin.installdir)

#        self.assertFalse(
#            'PYTHONPATH={}'.format(python_path) in environment, environment)


#class FindSystemDependenciesTestCase(tests.TestCase):
#    def setUp(self):
#        super().setUp()

#        patcher = mock.patch('snapcraft.plugins.catkin._Rosdep')
#        self.rosdep_mock = patcher.start()
#        self.addCleanup(patcher.stop)

#    def verify_rosdep_setup(self, rosdistro, package_path, rosdep_path,
#                            sources):
#        self.rosdep_mock.assert_has_calls([
#            mock.call(rosdistro, package_path, rosdep_path, sources),
#            mock.call().setup()])

#    def test_find_system_dependencies_system_only(self):
#        mockInstance = self.rosdep_mock.return_value
#        mockInstance.get_dependencies.return_value = ['bar']
#        mockInstance.resolve_dependency.return_value = 'baz'

#        self.assertEqual(['baz'], catkin._find_system_dependencies(
#            {'foo'}, 'indigo', '/test/path1', '/test/path2', []))

#        # Verify that rosdep was setup as expected
#        self.verify_rosdep_setup('indigo', '/test/path1', '/test/path2', [])

#        mockInstance.get_dependencies.assert_called_once_with('foo')
#        mockInstance.resolve_dependency.assert_called_once_with('bar')

#    def test_find_system_dependencies_local_only(self):
#        mockInstance = self.rosdep_mock.return_value
#        mockInstance.get_dependencies.return_value = ['bar']

#        self.assertEqual([], catkin._find_system_dependencies(
#            {'foo', 'bar'}, 'indigo', '/test/path1', '/test/path2', []))

#        # Verify that rosdep was setup as expected
#        self.verify_rosdep_setup('indigo', '/test/path1', '/test/path2', [])

#        mockInstance.get_dependencies.assert_has_calls([mock.call('foo'),
#                                                        mock.call('bar')],
#                                                       any_order=True)
#        mockInstance.resolve_dependency.assert_not_called()

#    def test_find_system_dependencies_mixed(self):
#        mockInstance = self.rosdep_mock.return_value
#        mockInstance.get_dependencies.return_value = ['bar', 'baz']
#        mockInstance.resolve_dependency.return_value = 'qux'

#        self.assertEqual(['qux'], catkin._find_system_dependencies(
#            {'foo', 'bar'}, 'indigo', '/test/path1', '/test/path2', []))

#        # Verify that rosdep was setup as expected
#        self.verify_rosdep_setup('indigo', '/test/path1', '/test/path2', [])

#        mockInstance.get_dependencies.assert_has_calls([mock.call('foo'),
#                                                        mock.call('bar')],
#                                                       any_order=True)
#        mockInstance.resolve_dependency.assert_called_once_with('baz')

#    def test_find_system_dependencies_missing_local_dependency(self):
#        mockInstance = self.rosdep_mock.return_value

#        # Setup a dependency on a non-existing package, and it doesn't resolve
#        # to a system dependency.'
#        mockInstance.get_dependencies.return_value = ['bar']
#        mockInstance.resolve_dependency.return_value = None

#        with self.assertRaises(RuntimeError) as raised:
#            catkin._find_system_dependencies({'foo'}, 'indigo', '/test/path1',
#                                             '/test/path2', [])

#        self.assertEqual(raised.exception.args[0],
#                         'Package "bar" isn\'t a valid system dependency. Did '
#                         'you forget to add it to catkin-packages? If not, '
#                         'add the Ubuntu package containing it to '
#                         'stage-packages until you can get it into the rosdep '
#                         'database.')

#    def test_find_system_dependencies_roscpp_includes_gplusplus(self):
#        mockInstance = self.rosdep_mock.return_value
#        mockInstance.get_dependencies.return_value = ['roscpp']
#        mockInstance.resolve_dependency.return_value = 'baz'

#        self.assertEqual(_CompareLists(self, ['baz', 'g++']),
#                         catkin._find_system_dependencies({'foo'}, 'indigo',
#                                                          '/test/path1',
#                                                          '/test/path2', []))

#        # Verify that rosdep was setup as expected
#        self.verify_rosdep_setup('indigo', '/test/path1', '/test/path2', [])

#        mockInstance.get_dependencies.assert_called_once_with('foo')
#        mockInstance.resolve_dependency.assert_called_once_with('roscpp')


class DependencyToolTestCase(tests.TestCase):

    def setUp(self):
        super().setUp()

        patcher = mock.patch('snapcraft.repo.Ubuntu')
        self.ubuntu_mock = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch('subprocess.check_output')
        self.check_output_mock = patcher.start()
        self.addCleanup(patcher.stop)

    def test_run(self):
        tool = catkin._DependencyTool(repo.Ubuntu('ubuntu_path'), 'tools_path')
        tool.run(['qux'])

        class check_env():
            def __init__(self, test):
                self.test = test

            def __eq__(self, env):
                expected_variables = [
                    ('PATH', os.path.join(tool.tools_install_path, 'usr',
                                          'bin')),
                    ('PYTHONPATH', os.path.join(tool.tools_install_path, 'usr',
                                               'lib', 'python2.7',
                                               'dist-packages')),
                ]

                for variable in expected_variables:
                    self.test.assertEqual(
                        env[variable[0]], variable[1],
                        'Expected ${}="{}", but it was "{}"'.format(
                            variable[0], variable[1], env[variable[0]]))

                return True

        self.check_output_mock.assert_called_with(mock.ANY,
                                                  env=check_env(self),
                                                  stderr=subprocess.STDOUT)

class RosdepTestCase(DependencyToolTestCase):

    def setUp(self):
        super().setUp()

        self.rosdep = catkin._Rosdep('ros_distro', 'package_path',
                                     repo.Ubuntu('ubuntu_path'),
                                     'tools_path')

    def test_creation(self):
        # Note that the creation took place in the setUp(). Verify that only
        # rosdep was installed as a result (no other .debs)
        self.assertEqual(self.ubuntu_mock.return_value.get.call_count, 1)
        self.assertEqual(self.ubuntu_mock.return_value.unpack.call_count, 1)
        self.ubuntu_mock.assert_has_calls([
            mock.call().get(['python-rosdep']),
            mock.call().unpack(self.rosdep.tools_install_path)])

    def test_setup(self):
        # Return something other than a Mock to ease later assertions
        self.check_output_mock.return_value = b''

        self.rosdep.setup()

        # Verify that rosdep was initialized and updated
        self.assertEqual(self.check_output_mock.call_count, 2)
        self.check_output_mock.assert_has_calls([
            mock.call(['rosdep', 'init'], env=mock.ANY,
                stderr=subprocess.STDOUT),
            mock.call(['rosdep', 'update'], env=mock.ANY,
                stderr=subprocess.STDOUT)
        ])

    def test_setup_can_run_multiple_times(self):
        self.rosdep.setup()

        # Make sure running setup() again doesn't have problems with the old
        # environment
        try:
            self.rosdep.setup()
        except FileExistsError:
            self.fail('Unexpectedly raised an exception when running setup() '
                      'multiple times')

    def test_setup_initialization_failure(self):
        def run(args, **kwargs):
            if args == ['rosdep', 'init']:
                raise subprocess.CalledProcessError(1, 'foo', b'bar')

            return mock.DEFAULT

        self.check_output_mock.side_effect = run

        with self.assertRaises(RuntimeError) as raised:
            self.rosdep.setup()

        self.assertEqual(str(raised.exception),
                         'Error initializing rosdep database:\nbar')

    def test_setup_update_failure(self):
        def run(args, **kwargs):
            if args == ['rosdep', 'update']:
                raise subprocess.CalledProcessError(1, 'foo', b'bar')

            return mock.DEFAULT

        self.check_output_mock.side_effect = run

        with self.assertRaises(RuntimeError) as raised:
            self.rosdep.setup()

        self.assertEqual(str(raised.exception),
                         'Error updating rosdep database:\nbar')

    def test_get_dependencies(self):
        self.check_output_mock.return_value = b'foo\nbar\nbaz'

        self.assertEqual(self.rosdep.get_dependencies('foo'),
                         ['foo', 'bar', 'baz'])

        self.check_output_mock.assert_called_with(['rosdep', 'keys', 'foo'],
                                                  env=mock.ANY,
                                                  stderr=subprocess.STDOUT)

    def test_get_dependencies_no_dependencies(self):
        self.check_output_mock.return_value = b''

        self.assertEqual(self.rosdep.get_dependencies('foo'), [])

    def test_get_dependencies_invalid_package(self):
        self.check_output_mock.side_effect = subprocess.CalledProcessError(
            1, 'foo')

        with self.assertRaises(FileNotFoundError) as raised:
            self.rosdep.get_dependencies('bar')

        self.assertEqual(str(raised.exception),
                         'Unable to find Catkin package "bar"')

    def test_resolve_dependency(self):
        self.check_output_mock.return_value = b'#apt\nmylib-dev'

        self.assertEqual(self.rosdep.resolve_dependency('foo'), ['mylib-dev'])

        self.check_output_mock.assert_called_with(
            ['rosdep', 'resolve', 'foo', '--rosdistro', 'ros_distro', '--os',
             'ubuntu:trusty'], env=mock.ANY, stderr=subprocess.STDOUT)

    def test_resolve_dependency_multiple_packages(self):
        self.check_output_mock.return_value = b'#apt\nmylib1 mylib2'

        self.assertEqual(self.rosdep.resolve_dependency('foo'),
                         ['mylib1', 'mylib2'])

    def test_resolve_invalid_dependency(self):
        self.check_output_mock.side_effect = subprocess.CalledProcessError(
            1, 'foo')

        with self.assertRaises(catkin.SystemDependencyNotFound) as raised:
            self.rosdep.resolve_dependency('bar')

        self.assertEqual(str(raised.exception),
                         '"bar" does not resolve to a system dependency')

    def test_resolve_dependency_no_candidate(self):
        self.check_output_mock.return_value = b'#apt'

        self.assertEqual(self.rosdep.resolve_dependency('foo'), [])

#    def test_install(self):
#        self.rosdep.install(['package'])

#        self.check_output_mock.assert_called_with(
#            ['rosdep', 'install', 'package', '--ignore-src', '--rosdistro',
#             'ros_distro'],
#            env=mock.ANY)

#    def test_install_from_paths(self):
#        self.rosdep.install(['src'], from_paths=True)

#        self.check_output_mock.assert_called_with(
#            ['rosdep', 'install', 'src', '--from-paths', '--ignore-src',
#             '--rosdistro', 'ros_distro'],
#            env=mock.ANY)

    def test_run(self):
        self.rosdep.run(['qux'])

        rosdep_source_path = self.rosdep._rosdep_sources_path
        ros_home = self.rosdep._rosdep_cache_path
        ros_package_path = self.rosdep._ros_package_path

        class check_env():
            def __init__(self, test):
                self.test = test

            def __eq__(self, env):
                expected_variables = [
                    ('ROSDEP_SOURCE_PATH', rosdep_source_path),
                    ('ROS_HOME', ros_home),
                    ('ROS_PACKAGE_PATH', ros_package_path),
                ]

                for variable in expected_variables:
                    self.test.assertEqual(
                        env[variable[0]], variable[1],
                        'Expected ${}="{}", but it was "{}"'.format(
                            variable[0], variable[1], env[variable[0]]))

                return True

        self.check_output_mock.assert_called_with(mock.ANY,
                                                  env=check_env(self),
                                                  stderr=subprocess.STDOUT)


class WstoolTestCase(DependencyToolTestCase):

    def setUp(self):
        super().setUp()

        self.wstool = catkin._Wstool('source_space',
                                     repo.Ubuntu('ubuntu_path'), 'tools_path')

    def test_creation(self):
        # Note that the creation took place in the setUp(). Verify that only
        # wstool was installed as a result (no other .debs)
        self.assertEqual(self.ubuntu_mock.return_value.get.call_count, 1)
        self.assertEqual(self.ubuntu_mock.return_value.unpack.call_count, 1)
        self.ubuntu_mock.assert_has_calls([
            mock.call().get(['python-wstool']),
            mock.call().unpack(self.wstool.tools_install_path)])

    def test_initialize(self):
        self.wstool.initialize()

        self.check_output_mock.assert_called_with(
            ['wstool', 'init', 'source_space'], env=mock.ANY,
            stderr=subprocess.STDOUT)

    def test_merge(self):
        self.wstool.merge('foo.install')

        self.check_output_mock.assert_called_with(
            ['wstool', 'merge', '-k', '-t', 'source_space', 'foo.install'],
            env=mock.ANY, stderr=subprocess.STDOUT)

    def test_update(self):
        self.wstool.update()

        self.check_output_mock.assert_called_with(
            ['wstool', 'update', '-t', 'source_space'], env=mock.ANY,
            stderr=subprocess.STDOUT)


class RosinstallGeneratorTestCase(DependencyToolTestCase):

    def setUp(self):
        super().setUp()

        self.generator = catkin._RosinstallGenerator(
            'ros_distro', repo.Ubuntu('ubuntu_path'), 'tools_path')

    def test_creation(self):
        # Note that the creation took place in the setUp(). Verify that only
        # wstool was installed as a result (no other .debs)
        self.assertEqual(self.ubuntu_mock.return_value.get.call_count, 1)
        self.assertEqual(self.ubuntu_mock.return_value.unpack.call_count, 1)
        self.ubuntu_mock.assert_has_calls([
            mock.call().get(['python-rosinstall-generator']),
            mock.call().unpack(self.generator.tools_install_path)])

    def test_generate(self):
        self.check_output_mock.return_value = b'foo'

        self.generator.generate('package', 'output.install')

        self.check_output_mock.assert_called_with(
            ['rosinstall_generator', 'package', '--rosdistro', 'ros_distro',
             '--deps', '--wet-only', '--tar'], env=mock.ANY,
            stderr=subprocess.STDOUT)

        with open('output.install', 'r') as output_file:
            self.assertEqual(output_file.read(), 'foo')


class RospackTestCase(DependencyToolTestCase):

    def setUp(self):
        super().setUp()

        self.rospack = catkin._Rospack('ros_package_path',
                                       repo.Ubuntu('ubuntu_path'),
                                       'tools_path')

    def test_creation(self):
        # Note that the creation took place in the setUp(). Verify that only
        # rospack was installed as a result (no other .debs)
        self.assertEqual(self.ubuntu_mock.return_value.get.call_count, 1)
        self.assertEqual(self.ubuntu_mock.return_value.unpack.call_count, 1)
        self.ubuntu_mock.assert_has_calls([
            mock.call().get(['rospack-tools']),
            mock.call().unpack(self.rospack.tools_install_path)])

    def test_find(self):
        self.check_output_mock.return_value = b'foo'

        self.assertEqual(self.rospack.find('package'), 'foo')

        self.check_output_mock.assert_called_with(
            ['rospack', 'find', 'package'], env=mock.ANY,
            stderr=subprocess.STDOUT)

    def test_find_no_results(self):
        self.check_output_mock.side_effect = subprocess.CalledProcessError(
            1, 'foo')

        try:
            output = self.rospack.find('package')
        except:
            self.fail('Unexpectedly raised an exception when trying to find '
                      'non-existent package.')

        self.assertEqual(output, None)
