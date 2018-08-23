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
import logging
import os
from subprocess import CalledProcessError
from typing import Dict, List

from snapcraft.internal import common, errors


logger = logging.getLogger(__name__)


class BasePlugin:
    @classmethod
    def schema(cls):
        """Return a json-schema for the plugin's properties as a dictionary.
        Of importance to plugin authors is the 'properties' keyword and
        optionally the 'requires' keyword with a list of required
        'properties'.

        By default the properties will be that of a standard VCS,
        override in custom implementations if required.
        """
        return {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "type": "object",
            "additionalProperties": False,
            "properties": {},
            "pull-properties": [],
            "build-properties": [],
            "required": [],
        }

    @classmethod
    def get_pull_properties(cls):
        schema_pull_properties = cls.schema().get("pull-properties", [])
        if schema_pull_properties:
            logger.warning(
                "Use of pull-properties in the schema is deprecated.\n"
                "Plugins should now implement get_pull_properties"
            )
            return schema_pull_properties

        return []

    @classmethod
    def get_build_properties(cls):
        schema_build_properties = cls.schema().get("build-properties", [])
        if schema_build_properties:
            logger.warning(
                "Use of build-properties in the schema is deprecated.\n"
                "Plugins should now implement get_build_properties"
            )
            return schema_build_properties

        return []

    @property
    def PLUGIN_STAGE_SOURCES(self):
        """Define alternative sources.list."""
        return getattr(self, "_PLUGIN_STAGE_SOURCES", [])

    @property
    def stage_packages(self):
        return self._stage_packages

    @stage_packages.setter
    def stage_packages(self, value):
        self._stage_packages = value

    def __init__(self, name, options, project=None):
        self.name = name
        self.build_snaps = []
        self.build_packages = []
        self._stage_packages = []
        self.__dependencies = []

        with contextlib.suppress(AttributeError):
            self._stage_packages = options.stage_packages.copy()
        with contextlib.suppress(AttributeError):
            self.build_packages = options.build_packages.copy()
        with contextlib.suppress(AttributeError):
            self.build_snaps = options.build_snaps.copy()

        self.project = project
        self.options = options

        # The remote parts can have a '/' in them to separate the main project
        # part with the subparts. This is rather unfortunate as it affects the
        # the layout of parts inside the parts directory causing collisions
        # between the main project part and its subparts.
        part_dir = name.replace("/", "\N{BIG SOLIDUS}")
        if project:
            self.partdir = os.path.join(project.parts_dir, part_dir)
        else:
            self.partdir = os.path.join(os.getcwd(), "parts", part_dir)

        self.sourcedir = os.path.join(self.partdir, "src")
        self.installdir = os.path.join(self.partdir, "install")
        self.statedir = os.path.join(self.partdir, "state")
        self.osrepodir = os.path.join(self.partdir, "ubuntu")

        self.build_basedir = os.path.join(self.partdir, "build")
        source_subdir = getattr(self.options, "source_subdir", None)
        if source_subdir:
            self.builddir = os.path.join(self.build_basedir, source_subdir)
        else:
            self.builddir = self.build_basedir

        # By default, snapcraft does an in-source build. Set this property to
        # True if that's not desired.
        self.out_of_source_build = False

        self.__runner_script = None

    def run_pull(self):
        # Set the proper environment for pulling, then pull
        self.__runner_script = _create_runner_script(self, steps.PULL)
        self.pull()

    def run_build(self):
        self.__runner_script = _create_runner_script(self, steps.BUILD)
        self.build()

    # The API
    def pull(self):
        """Pull the source code and/or internal prereqs to build the part."""
        pass

    def clean_pull(self):
        """Clean the pulled source for this part."""
        pass

    def build(self):
        """Build the source code retrieved from the pull phase."""
        pass

    def clean_build(self):
        """Clean the artifacts that resulted from building this part."""
        pass

    def get_manifest(self):
        """Return the information to record after the build of this part.

        :rtype: dict
        """
        pass

    def snap_fileset(self):
        """Return a list of files to include or exclude in the resulting snap

        The staging phase of a plugin's lifecycle may populate many things
        into the staging directory in order to succeed in building a
        project.
        During the stripping phase and in order to have a clean snap, the
        plugin can provide additional logic for stripping build components
        from the final snap and alleviate the part author from doing so for
        repetetive filesets.

        These are the rules to honor when creating such list:

            - includes can be just listed
            - excludes must be preceded by -

        For example::
            (['bin', 'lib', '-include'])
        """
        return []

    def pull_env(self) -> Dict[str, str]:
        """Return a dict of environment variable names and values to use for pulling."""
        return {}

    def build_env(self) -> Dict[str, str]:
        """Return a dict of environment variable names and values to use for building."""
        return {}

    def dependency_env(self) -> Dict[str, str]:
        """Return a dict of environment variable names and values for use by dependents."""
        return {}

    def snap_env(self) -> Dict[str, str]:
        """Return a dict of environment variable names and values for apps in the final snap."""
        return {}

    def pull_command_chain(self) -> List[str]:
        """Return a list of commands to be prepended to the actual commands run when pulling."""
        return []

    def build_command_chain(self) -> List[str]:
        """Return a list of commands to be prepended to the actual commands run when building."""
        return []

    def dependency_command_chain(self) -> List[str]:
        """Return a list of commands to be prepended to the actual commands used by dependents."""
        return []

    def snap_command_chain(self) -> List[str]:
        """Return a list of commands to be prepended to the apps in the final snap."""
        return []

    def enable_cross_compilation(self):
        """Enable cross compilation for the plugin."""
        raise NotImplementedError(
            "The plugin used by {!r} does not support cross-compiling "
            "to a different target architecture".format(self.name)
        )

    @property
    def parallel_build_count(self):
        """Number of CPU's to use for building.

        Number comes from `project.parallel_build_count` unless the part
        has defined `disable-parallel` as `True`.
        """
        if getattr(self.options, "disable_parallel", False):
            return 1
        else:
            return self.project.parallel_build_count

    def add_dependency(self, plugin):
        self.__dependencies.append(plugin)

    def dependencies(self):
        return self.__dependencies.copy()

    # Helpers
    def run(self, cmd: List[str], **kwargs):
        return self._do_run(comm.run), cmd, **kwargs)

    def run_output(self, cmd: List[str], **kwargs):
        return self._do_run(common.run_output, cmd, **kwargs)

    def _do_run(self, runnable, cmd: List[str], cwd: str=None, **kwargs):
        if not cwd:
            cwd = self.builddir
        os.makedirs(cwd, exist_ok=True)
        try:
            return runnable(["/bin/sh"] + cmd, input=self.__runner_script, cwd=cwd, **kwargs)
        except CalledProcessError as process_error:
            raise errors.SnapcraftPluginCommandError(
                command=cmd, part_name=self.name, exit_code=process_error.returncode
            ) from process_error


def _create_runner_script(step: steps.Step, part: BasePlugin) -> str:
    script_lines = []  # type: List[str]

    # First obtain the environment required to use the part's dependencies. Maintain
    # backward compatibility with the deprecated env() function.
    for dependency in part.dependencies():
        try:
            script_lines.extend([
                "export {}".format(e)
                for e in dependency.env(dependency.project.stage_dir)
            ])
        except AttributeError:
            script_lines.extend([
                'export {}="{}"'.format(k, v)
                for k,v in dependency.dependency_env().items()
            ])

    # Now obtain the environment required to run this step from the part. Again,
    # maintain backward compatibility with the deprecated env() function.
    try:
        script_lines.extend([
            "export {}".format(e)
            for e in part.env(part.installdir)
        ])
    except AttributeError:
        script_lines.extend([
            'export {}="{}"'.format(k, v)
            for k,v in getattr(part, "{}_env".format(step.name))().items()
        ])

    command_line = 'exec'
    for command in getattr(part, "{}_command_chain".format(step.name))():
        command_line.append(' "{}"'.format(command))
    command_line.append(' "$@"')
    script_lines.append(command_line)

    return "\n".join(script_lines)