# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2015, 2016 Canonical Ltd
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

"""The catkin plugin is useful for building ROS parts.

This plugin uses the common plugin keywords as well as those for "sources".
For more information check the 'plugins' topic for the former and the
'sources' topic for the latter.

Additionally, this plugin uses the following plugin-specific keywords:

    - catkin-packages:
      (list of strings)
      List of catkin packages to build.
    - source-space:
      (string)
      The source space containing Catkin packages. By default this is 'src'.
"""

import os
import tempfile
import logging
import shutil
import re
import subprocess

import snapcraft
from snapcraft import (
    common,
    repo,
)

logger = logging.getLogger(__name__)


class CatkinPlugin(snapcraft.BasePlugin):

    @classmethod
    def schema(cls):
        schema = super().schema()
        schema['properties']['rosdistro'] = {
            'type': 'string',
            'default': 'indigo'
        }
        schema['properties']['catkin-packages'] = {
            'type': 'array',
            'minitems': 1,
            'uniqueItems': True,
            'items': {
                'type': 'string'
            },
            'default': [],
        }
        schema['properties']['source-space'] = {
            'type': 'string',
            'default': 'src',
        }

        schema['required'].append('catkin-packages')

        return schema

    def __init__(self, name, options):
        super().__init__(name, options)

        # Get a unique set of packages
        self.catkin_packages = set(options.catkin_packages)

        # The path created via the `source` key (or a combination of `source`
        # and `source-subdir` keys) needs to point to a valid Catkin workspace
        # containing another subdirectory called the "source space." By
        # default, this is a directory named "src," but it can be remapped via
        # the `source-space` key. It's important that the source space is not
        # the root of the Catkin workspace, since Catkin won't work that way
        # and it'll create a circular link that causes rosdep to hang.
        if self.options.source_subdir:
            self._ros_package_path = os.path.join(self.sourcedir,
                                                  self.options.source_subdir,
                                                  self.options.source_space)
        else:
            self._ros_package_path = os.path.join(self.sourcedir,
                                                  self.options.source_space)

        if os.path.abspath(self.sourcedir) == os.path.abspath(
                self._ros_package_path):
            raise RuntimeError(
                'source-space cannot be the root of the Catkin workspace')

        self._ros_source_path = os.path.join(self.partdir, 'ros', 'src')
        self.options.include_roscore = True

    def env(self, root):
        """Runtime environment for ROS binaries and services."""

        env = [
            # This environment variable tells ROS nodes where to find ROS
            # master. It does not affect ROS master, however-- this is just the
            # default URI.
            'ROS_MASTER_URI=http://localhost:11311',

            # Various ROS tools (e.g. rospack, roscore) keep a cache or a log,
            # and use $ROS_HOME to determine where to put them.
            'ROS_HOME=$SNAP_USER_DATA/ros',

            # This environment variable points to where the setup.sh and
            # _setup_util.py files are located. This is required at both build-
            # and run-time.
            '_CATKIN_SETUP_DIR={}'.format(os.path.join(
                root, 'opt', 'ros', self.options.rosdistro)),

            # FIXME: Nasty hack to source ROS's setup.sh (since each of these
            # lines is prepended with "export"). There's got to be a better way
            # to do this.
            'echo FOO=BAR\nif `test -e {0}` ; then\n. {0} ;\nfi\n'.format(
                os.path.join(
                    root, 'opt', 'ros', self.options.rosdistro, 'setup.sh'))
        ]

        # There's a chicken and egg problem here, everything run get's an
        # env built, even package installation, so the first runs for these
        # will likely fail.
        try:
            # The ROS packaging system tools (e.g. rospkg, etc.) don't go
            # into the ROS install path (/opt/ros/$distro), so we need the
            # PYTHONPATH to include the dist-packages in /usr/lib as well.
            env.append('PYTHONPATH={0}:$PYTHONPATH'.format(
                common.get_python2_path(root)))
        except EnvironmentError as e:
            logger.debug(e)

        return env

    def pull(self):
        """Copy source into build directory and fetch dependencies.

        Catkin packages can specify their system dependencies in their
        package.xml. In order to support that, the Catkin packages are
        interrogated for their dependencies here. Since `stage-packages` are
        already installed by the time this function is run, the dependencies
        from the package.xml are pulled down explicitly.
        """

        super().pull()

        # Make sure the package path exists before continuing
        if not os.path.exists(self._ros_package_path):
            raise FileNotFoundError(
                'Unable to find package path: "{}"'.format(
                    self._ros_package_path))

        ubuntu_repo = repo.Ubuntu(os.path.join(self.partdir, 'ubuntu'))
        ros_tools_path = os.path.join(self.partdir, 'ros_tools')
        rosdep = _Rosdep(self.options.rosdistro, self._ros_package_path,
                         ubuntu_repo, ros_tools_path)
        rosdep.setup()

        # Parse the Catkin packages for extra dependencies
        ros_dependencies = _find_extra_dependencies(rosdep,
                                                    self.catkin_packages)

        if self.options.include_roscore:
            ros_dependencies.add('ros_core')

        os.makedirs(self._ros_source_path, exist_ok=True)
        # Fetch the source for any dependencies that have it available
        wstool = _Wstool(self._ros_source_path, ubuntu_repo, ros_tools_path)
        rosinstall_generator = _RosinstallGenerator(
            self.options.rosdistro, ubuntu_repo, ros_tools_path)
        unpulled_dependencies = _pull_ros_dependency_sources(
            rosinstall_generator, wstool, ros_dependencies,
            self._ros_source_path)

        logger.info('Determining system dependencies for ROS sources...')
        source_system_dependencies = rosdep.get_dependencies(
            self._ros_source_path, from_paths=True)

        # Any non-source dependencies must be system dependencies, so let's
        # try to resolve those into actual Ubuntu packages.
        rospack = _Rospack(self._ros_source_path, ubuntu_repo, ros_tools_path)
        logger.info('Attempting to resolve the non-source dependencies as '
                    'system dependencies...')
        system_dependencies = _resolve_system_dependencies(
            rosdep, rospack, self.catkin_packages,
            unpulled_dependencies.union(source_system_dependencies))

        # Pull down and unpack any system dependencies that were discovered
        # as if they were stage-packages.
        if system_dependencies:
            logger.info('Fetching system dependencies: {}'.format(
                ', '.join(system_dependencies)))
            try:
                ubuntu_repo.get(system_dependencies)
            except PackageNotFoundError as e:
                raise RuntimeError(
                    'Failed to fetch system dependencies: {}'.format(
                        e.message()))

            logger.info('Unpacking system dependencies...')
            ubuntu_repo.unpack(self.installdir)

    @property
    def gcc_version(self):
        return self.run_output(['gcc', '-dumpversion'])

    @property
    def rosdir(self):
        return os.path.join(self.installdir, 'opt', 'ros',
                            self.options.rosdistro)

    def _run_in_bash(self, commandlist, cwd=None):
        with tempfile.NamedTemporaryFile(mode='w') as f:
            f.write('set -ex\n')
            f.write('exec {}\n'.format(' '.join(commandlist)))
            f.flush()

            self.run(['/bin/bash', f.name], cwd=cwd)

    def build(self):
        """Build Catkin packages.

        This function runs some pre-build steps to prepare the sources for
        building in the Snapcraft environment, builds the packages via
        catkin_make_isolated, and finally runs some post-build clean steps
        to prepare the newly-minted install to be packaged as a .snap.
        """

        super().build()

        logger.info('Preparing to build Catkin packages...')
        self._prepare_build()

        logger.info('Building dependencies...')
        self._build_ros_source()

        logger.info('Building Catkin packages...')
        self._build_catkin_packages()

        logger.info('Cleaning up newly installed Catkin packages...')
        self._finish_build()

    def _prepare_build(self):
        # Each Catkin package distributes .cmake files so they can be found via
        # find_package(). However, the Ubuntu packages pulled down as
        # dependencies contain .cmake files pointing to system paths (e.g.
        # /usr/lib, /usr/include, etc.). They need to be rewritten to point to
        # the install directory.
        def rewrite_paths(match):
            paths = match.group(1).strip().split(';')
            for i, path in enumerate(paths):
                # Rewrite this path if it's an absolute path and not already
                # within the install directory.
                if (os.path.isabs(path) and
                        not path.startswith(self.installdir)):
                    paths[i] = self.installdir + path

            return '"' + ';'.join(paths) + '"'

        # Looking for any path-like string
        common.replace_in_file(self.installdir,
                               re.compile(r'.*[Cc]onfig.cmake$'),
                               re.compile(r'"(.*?/.*?)"'),
                               rewrite_paths)

    def _finish_build(self):
        # Fix all shebangs to use the in-snap python.
        common.replace_in_file(self.rosdir, re.compile(r''),
                               re.compile(r'#!.*python'),
                               r'#!/usr/bin/env python')

        # Replace the CMAKE_PREFIX_PATH in _setup_util.sh
        setup_util_file = os.path.join(self.rosdir, '_setup_util.py')
        if os.path.isfile(setup_util_file):
            with open(setup_util_file, 'r+') as f:
                pattern = re.compile(r"CMAKE_PREFIX_PATH = '{}.*".format(
                    self.rosdir))
                replaced = pattern.sub('CMAKE_PREFIX_PATH = []', f.read())
                f.seek(0)
                f.truncate()
                f.write(replaced)

        # Also replace the python usage in 10.ros.sh to use the in-snap python.
        ros10_file = os.path.join(self.rosdir,
                                  'etc/catkin/profile.d/10.ros.sh')
        if os.path.isfile(ros10_file):
            with open(ros10_file, 'r+') as f:
                pattern = re.compile(re.escape(self.installdir) + '/usr/bin/python')
                replaced = pattern.sub(r'python', f.read())
                f.seek(0)
                f.truncate()
                f.write(replaced)

    def _build_ros_source(self):
        if not os.path.exists(self._ros_source_path):
            return

        command = [os.path.join(self._ros_source_path, 'catkin', 'bin',
                                'catkin_make_isolated')]

        # Install the packages
        command.append('--install')

        # Specify the install location so it'll be placed into the .snap
        command.extend(['--install-space', self.rosdir])

        self._add_catkin_cmake_args(command)

        self._run_in_bash(command, cwd=os.path.join(self._ros_source_path,
                                                    '..'))

    def _build_catkin_packages(self):
        # Nothing to do if no packages were specified
        if not self.catkin_packages:
            return

        catkincmd = [os.path.join(self._ros_source_path, 'catkin', 'bin',
                                  'catkin_make_isolated')]

        # Install the package
        catkincmd.append('--install')

        # Specify the packages to be built
        catkincmd.append('--pkg')
        catkincmd.extend(self.catkin_packages)

        # Don't clutter the real ROS workspace-- use the Snapcraft build
        # directory
        catkincmd.extend(['--directory', self.builddir])

        # Account for a non-default source space by always specifying it
        catkincmd.extend(['--source-space', os.path.join(
            self.builddir, self.options.source_space)])

        # Specify that the package should be installed along with the rest of
        # the ROS distro.
        catkincmd.extend(['--install-space', self.rosdir])

        self._add_catkin_cmake_args(catkincmd)

        # This command must run in bash due to a bug in Catkin that causes it
        # to explode if there are spaces in the cmake args (which there are).
        # This has been fixed in Catkin Tools... perhaps we should be using
        # that instead.
        self._run_in_bash(catkincmd)

    def _add_catkin_cmake_args(self, command):
        # All the arguments that follow are meant for CMake
        command.append('--cmake-args')

        # Make sure we're using the compilers included in this .snap
        command.extend([
            '-DCMAKE_BUILD_TYPE=Release',
            '-DCMAKE_C_FLAGS="$CFLAGS"',
            '-DCMAKE_CXX_FLAGS="$CPPFLAGS -I{} -I{}"'.format(
                os.path.join(self.installdir, 'usr', 'include', 'c++',
                             self.gcc_version),
                os.path.join(self.installdir, 'usr', 'include',
                             common.get_arch_triplet(), 'c++',
                             self.gcc_version)),
            '-DCMAKE_LD_FLAGS="$LDFLAGS"',
            '-DCMAKE_C_COMPILER={}'.format(
                os.path.join(self.installdir, 'usr', 'bin', 'gcc')),
            '-DCMAKE_CXX_COMPILER={}'.format(
                os.path.join(self.installdir, 'usr', 'bin', 'g++'))
        ])

def _find_extra_dependencies(rosdep, catkin_packages):
    dependencies = set()
    for package in catkin_packages:
        rosdep_dependencies = rosdep.get_dependencies(package)

        for dependency in rosdep_dependencies:
            if dependency in catkin_packages:
                continue

            dependencies.add(dependency)

    return dependencies


def _pull_ros_dependency_sources(rosinstall_generator, wstool, dependencies,
                                 ros_workspace):
    # Initialize workspace (essentially creates an empty rosinstall file).
    wstool.initialize()

    unpulled_dependencies = set()
    for dependency in dependencies:
        try:
            rosinstall_file = os.path.join(ros_workspace,
                                           '{}.install'.format(dependency))

            logger.info('Generating rosinstall file for "{}"...'.format(
                dependency))

            # Generate the rosinstall file for this dependency and all of its
            # dependencies.
            rosinstall_generator.generate(dependency, rosinstall_file)

            # Include the contents of this rosinstall file in our workspace
            # (this doesn't pull code, yet).
            wstool.merge(rosinstall_file)

        except PackageNotReleased:
            # This dependency's source wasn't available-- perhaps it's a system
            # dependency?
            unpulled_dependencies.add(dependency)

    logger.info('Fetching source for dependencies...')
    # Finally, pull down all the dependencies.
    wstool.update()

    return unpulled_dependencies

def _resolve_system_dependencies(rosdep, rospack, catkin_packages,
                                 dependencies):
    """Resolve a set of ROS dependencies into system dependencies (if
    possible)."""

    system_dependencies = {}
    for dependency in dependencies:
        if dependency in catkin_packages or rospack.find(dependency):
            continue

        # In this situation, the package depends on something that we
        # weren't instructed to build. It's probably a system dependency,
        # but the developer could have also forgotten to tell us to build
        # it.
        try:
            system_dependency = rosdep.resolve_dependency(dependency)
        except SystemDependencyNotFound:
            raise RuntimeError(
                'Package "{}" isn\'t a valid system dependency. '
                'Did you forget to add it to catkin-packages? If '
                'not, add the Ubuntu package containing it to '
                'stage-packages until you can get it into the '
                'rosdep database.'.format(dependency))

        # It's possible for rosdep to return nothing, which isn't an error--
        # it means that there's no package to install.
        if system_dependency:
            system_dependencies[dependency] = system_dependency

            # TODO: Not sure why this isn't pulled in by roscpp. Can it be
            # compiled by clang, etc.? If so, perhaps this should be left up to
            # the developer.
            if dependency == 'roscpp':
                system_dependencies['g++'] = 'g++'

    # Finally, return a flat list of all system dependencies
    return set([item for sublist in system_dependencies.values()
                for item in sublist])

#def _find_system_dependencies(catkin_packages, ros_distro, ros_package_path,
#                              rosdep_path, ubuntu_sources):
#    """Find system dependencies for a given set of Catkin packages."""

#    rosdep = _Rosdep(ros_distro, ros_package_path, rosdep_path, ubuntu_sources)
#    rosdep.setup()

#    system_dependencies = {}

#    logger.info('Determining system dependencies for Catkin packages...')
#    for package in catkin_packages:
#        # Query rosdep for the list of dependencies for this package
#        dependencies = rosdep.get_dependencies(package)

#        for dependency in dependencies:
#            # No need to resolve this dependency if we know it's local, or if
#            # we've already resolved it into a system dependency
#            if (dependency in catkin_packages or
#                    dependency in system_dependencies):
#                continue

#            # In this situation, the package depends on something that we
#            # weren't instructed to build. It's probably a system dependency,
#            # but the developer could have also forgotten to tell us to build
#            # it.
#            system_dependency = rosdep.resolve_dependency(dependency)

#            if not system_dependency:
#                raise RuntimeError(
#                    'Package "{}" isn\'t a valid system dependency. '
#                    'Did you forget to add it to catkin-packages? If '
#                    'not, add the Ubuntu package containing it to '
#                    'stage-packages until you can get it into the '
#                    'rosdep database.'.format(dependency))

#            system_dependencies[dependency] = system_dependency

#            # TODO: Not sure why this isn't pulled in by roscpp. Can it
#            # be compiled by clang, etc.? If so, perhaps this should be
#            # left up to the developer.
#            if dependency == 'roscpp':
#                system_dependencies['g++'] = 'g++'

#    # Finally, return a list of all system dependencies
#    return list(system_dependencies.values())


class _DependencyTool:
    def __init__(self, ubuntu_repo, tools_path):
        self.tools_path = tools_path
        self.tools_install_path = os.path.join(tools_path, 'install')
        self.tools_data_path = os.path.join(tools_path, 'data')

        # Make sure we have a directory to unpack into
        os.makedirs(self.tools_install_path, exist_ok=True)

        tools = self.ubuntu_packages()
        if tools:
            logger.info('Fetching dependency tool(s): {}'.format(
                ' '.join(tools)))
            ubuntu_repo.get(tools)

            logger.info('Unpacking dependency tool(s): {}'.format(
                ' '.join(tools)))
            ubuntu_repo.unpack(self.tools_install_path)

    def ubuntu_packages(self):
        return []

    def run(self, command, env=None):
        if not env:
            env = os.environ.copy()

        env['PATH'] = os.path.join(self.tools_install_path, 'usr', 'bin')
        env['PYTHONPATH'] = os.path.join(self.tools_install_path, 'usr', 'lib',
                                         'python2.7', 'dist-packages')

        return subprocess.check_output(
            command, env=env, stderr=subprocess.STDOUT).decode('utf8').strip()


class SystemDependencyNotFound(Exception):
    pass


class _Rosdep(_DependencyTool):
    def __init__(self, ros_distro, ros_package_path, ubuntu_repo, tools_path):
        super().__init__(ubuntu_repo, tools_path)

        self._ros_distro = ros_distro
        self._ros_package_path = ros_package_path
        self._rosdep_sources_path = os.path.join(self.tools_data_path,
                                                 'sources.list.d')
        self._rosdep_cache_path = os.path.join(self.tools_data_path,
                                               'cache')

    def ubuntu_packages(self):
        return super().ubuntu_packages() + ['python-rosdep']

    def setup(self):
        # Make sure we can run multiple times without error, while leaving the
        # capability to re-initialize, by making sure we clear the sources.
        if os.path.exists(self._rosdep_sources_path):
            shutil.rmtree(self._rosdep_sources_path)

        os.makedirs(self._rosdep_sources_path)
        os.makedirs(self._rosdep_cache_path, exist_ok=True)

        logger.info('Initializing rosdep database...')
        try:
            self.run(['init'])
        except subprocess.CalledProcessError as e:
            output = e.output.decode('utf8').strip()
            raise RuntimeError(
                'Error initializing rosdep database:\n{}'.format(output))

        logger.info('Updating rosdep database...')
        try:
            self.run(['update'])
        except subprocess.CalledProcessError as e:
            output = e.output.decode('utf8').strip()
            raise RuntimeError(
                'Error updating rosdep database:\n{}'.format(output))

    def get_dependencies(self, package_name, from_paths=False):
        command = ['keys', package_name]
        if from_paths:
            command.append('--from-paths')

        try:
            output = self.run(command)
            if output:
                return output.split('\n')
            else:
                return []
        except subprocess.CalledProcessError:
            raise FileNotFoundError(
                'Unable to find Catkin package "{}"'.format(package_name))

    def resolve_dependency(self, dependency_name):
        try:
            # rosdep needs three pieces of information here:
            #
            # 1) The dependency we're trying to lookup.
            # 2) The rosdistro being used.
            # 3) The version of Ubuntu being used. We're currently using only
            #    the Trusty ROS sources, so we're telling rosdep to resolve
            #    dependencies using Trusty (even if we're running on something
            #    else).
            output = self.run(['resolve', dependency_name, '--rosdistro',
                                self._ros_distro, '--os', 'ubuntu:trusty'])
        except subprocess.CalledProcessError:
            raise SystemDependencyNotFound(
                '"{}" does not resolve to a system dependency'.format(
                    dependency_name))

        # `rosdep resolve` returns output like:
        # #apt
        # ros-indigo-package
        #
        # Everything that isn't a package name is prepended with the pound
        # sign, so we'll ignore everything with that.
        delimiters = re.compile(r'\n|\s')
        lines = delimiters.split(output)
        return [line for line in lines if not line.startswith('#')]

#    def install(self, items, from_paths=False):
#        command = ['install'] + items

#        if from_paths:
#            command.append('--from-paths')

#        self.run(command + ['--ignore-src', '--rosdistro', self._ros_distro])

    def run(self, arguments):
        env = os.environ.copy()

        # By default, rosdep uses /etc/ros/rosdep to hold its sources list. We
        # don't want that here since we don't want to touch the host machine
        # (not to mention it would require sudo), so we can redirect it via
        # this environment variable
        env['ROSDEP_SOURCE_PATH'] = self._rosdep_sources_path

        # By default, rosdep saves its cache in $HOME/.ros, which we shouldn't
        # access here, so we'll redirect it with this environment variable.
        env['ROS_HOME'] = self._rosdep_cache_path

        # This environment variable tells rosdep which directory to recursively
        # search for packages.
        env['ROS_PACKAGE_PATH'] = self._ros_package_path

        return super().run(['rosdep'] + arguments, env=env)


class _Wstool(_DependencyTool):

    def __init__(self, source_path, ubuntu_repo, tools_path):
        super().__init__(ubuntu_repo, tools_path)

        self._source_path = source_path

    def ubuntu_packages(self):
        return super().ubuntu_packages() + ['python-wstool']

    def initialize(self):
        try:
            self.run(['wstool', 'init', self._source_path])
        except subprocess.CalledProcessError as e:
            output = e.output.decode('utf8').strip()
            raise RuntimeError(
                'Error initializing workspace:\n{}'.format(output))

    def merge(self, rosinstall_file):
        try:
            self.run(['wstool', 'merge', '-k', '-t', self._source_path,
                      rosinstall_file])
        except subprocess.CalledProcessError as e:
            output = e.output.decode('utf8').strip()
            raise RuntimeError(
                'Error merging rosinstall file:\n{}'.format(output))

    def update(self):
        try:
            self.run(['wstool', 'update', '-t', self._source_path])
        except subprocess.CalledProcessError as e:
            output = e.output.decode('utf8').strip()
            raise RuntimeError(
                'Error updating workspace:\n{}'.format(output))

class PackageNotReleased(Exception):
    pass

class _RosinstallGenerator(_DependencyTool):

    def __init__(self, ros_distro, ubuntu_repo, tools_path):
        super().__init__(ubuntu_repo, tools_path)

        self._ros_distro = ros_distro

    def ubuntu_packages(self):
        return super().ubuntu_packages() + ['python-rosinstall-generator']

    def generate(self, ros_package, output_rosinstall_file):
        try:
            output = self.run(['rosinstall_generator', ros_package,
                               '--rosdistro', self._ros_distro, '--deps',
                               '--wet-only', '--tar'])
        except subprocess.CalledProcessError as e:
            output = e.output.decode('utf8').strip()
            raise PackageNotReleased(
                'Unable to generate rosinstall file:\n{}'.format(output))

        with open(output_rosinstall_file, 'w') as output_file:
            output_file.write(output)


class _Rospack(_DependencyTool):

    def __init__(self, ros_package_path, ubuntu_repo, tools_path):
        super().__init__(ubuntu_repo, tools_path)

        self._ros_package_path = ros_package_path

    def ubuntu_packages(self):
        return (super().ubuntu_packages() + ['rospack-tools'])

    def find(self, ros_package):
        try:
            return self.run(['find', ros_package])
        except subprocess.CalledProcessError as e:
            return None

    def run(self, arguments):
        env = os.environ.copy()

        # This environment variable tells rospack the directory in which to
        # recursively search for packages.
        env['ROS_PACKAGE_PATH'] = self._ros_package_path

        env['LD_LIBRARY_PATH'] = os.path.join(
            self.tools_install_path, 'usr', 'lib', common.get_arch_triplet())

        return super().run(['rospack'] + arguments, env=env)
