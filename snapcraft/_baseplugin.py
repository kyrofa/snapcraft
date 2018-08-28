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
import functools
import itertools
import logging
import os
import shlex
from subprocess import CalledProcessError
from typing import Dict, List, Tuple

from snapcraft.internal import common, errors, steps


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

        self.__current_step = None  # type: steps.Step

    def run_pull(self):
        # Track the current step
        self.__current_step = steps.PULL
        try:
            self.pull()
        finally:
            self.__current_step = None

    def run_build(self):
        # Track the current step
        self.__current_step = steps.BUILD
        try:
            self.build()
        finally:
            self.__current_step = None

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

    def get_dependencies(self):
        return self.__dependencies.copy()

    # Helpers
    def run(self, cmd: List[str], **kwargs):
        return self._do_run(common.run, cmd, **kwargs)

    def run_output(self, cmd: List[str], **kwargs):
        return self._do_run(common.run_output, cmd, **kwargs)

    def _do_run(self, runnable, cmd: List[str], cwd: str = None, **kwargs):
        if not cwd:
            cwd = self.builddir
        os.makedirs(cwd, exist_ok=True)
        try:
            return runnable(
                ["/bin/sh"],
                input=_runner_script(self, self.__current_step, cmd),
                cwd=cwd,
                **kwargs
            )
        except CalledProcessError as process_error:
            raise errors.SnapcraftPluginCommandError(
                command=cmd, part_name=self.name, exit_code=process_error.returncode
            ) from process_error


def _runner_script(part, step: steps.Step, cmd: List[str]) -> str:
    env, chain = _env_and_command_chain(part, step)
    command_line = "exec"
    if chain:
        command_line += " {}".format(chain)
    command_line += ' "{}" "$@"'.format(" ".join([shlex.quote(c) for c in cmd]))

    return "{}\n{}".format(env, command_line)


# Don't load the same environment multiple times. This is limited by the number of
# parts, so no need to limit the cache size.
@functools.lru_cache(maxsize=0)
def _env_and_command_chain(part: BasePlugin, step: steps.Step) -> Tuple[str, str]:
    env_lines = _lines_from_dependency_envs(part.get_dependencies())

    # Now obtain the environment required to run this step from the part.
    # Maintain backward compatibility with the deprecated env() function.
    try:
        env = part.env(part.installdir)  # type: ignore
        env_lines.extend(["export {}".format(e) for e in env])
    except AttributeError:
        env_lines.extend(
            [
                'export {}="{}"'.format(k, v)
                for k, v in getattr(part, "{}_env".format(step.name))().items()
            ]
        )

    command_chain = itertools.chain(
        _command_chain_from_dependencies(part.get_dependencies()),
        getattr(part, "{}_command_chain".format(step.name))(),
    )

    return ("\n".join(env_lines), " ".join(['"{}"'.format(c) for c in command_chain]))


def _lines_from_dependency_envs(dependencies: List[BasePlugin]) -> List[str]:
    script_lines = []  # type: List[str]
    for dependency in dependencies:
        # Maintain backward compatibility with the deprecated env() function.
        try:
            env = dependency.env(dependency.project.stage_dir)  # type: ignore
            script_lines.extend(["export {}".format(e) for e in env])
        except AttributeError:
            script_lines.extend(
                [
                    'export {}="{}"'.format(k, v)
                    for k, v in dependency.dependency_env().items()
                ]
            )

    return script_lines


def _command_chain_from_dependencies(dependencies: List[BasePlugin]) -> List[str]:
    chain = []  # type: List[str]
    for dependency in dependencies:
        chain.extend(dependency.dependency_command_chain())

    return chain


def build_env_for_part(self, part, root_part=True) -> List[str]:
    """Return a build env of all the part's dependencies."""

    env = []  # type: List[str]
    stagedir = self._project.stage_dir
    is_host_compat = self._project.is_host_compatible_with_base(self._base)

    if root_part:
        # this has to come before any {}/usr/bin
        env += part.env(part.plugin.installdir)
        env += runtime_env(part.plugin.installdir, self._project.arch_triplet)
        env += runtime_env(stagedir, self._project.arch_triplet)
        env += build_env(
            part.plugin.installdir, self._snap_name, self._project.arch_triplet
        )
        env += build_env_for_stage(
            stagedir, self._snap_name, self._project.arch_triplet
        )
        # Only set the paths to the base snap if we are building on the
        # same host. Failing to do so will cause Segmentation Faults.
        if self._confinement == "classic" and is_host_compat:
            env += env_for_classic(self._base, self._project.arch_triplet)

        global_env = snapcraft_global_environment(self._project)
        part_env = snapcraft_part_environment(part)
        for variable, value in ChainMap(part_env, global_env).items():
            env.append('{}="{}"'.format(variable, value))
    else:
        env += part.env(stagedir)
        env += runtime_env(stagedir, self._project.arch_triplet)

    for dep_part in part.get_dependencies():
        env += dep_part.env(stagedir)
        env += self.build_env_for_part(dep_part, root_part=False)

    # LP: #1767625
    # Remove duplicates from using the same plugin in dependent parts.
    seen = set()  # type: Set[str]
    deduped_env = list()  # type: List[str]
    for e in env:
        if e not in seen:
            deduped_env.append(e)
            seen.add(e)

    return deduped_env


def env_for_classic(base: str, arch_triplet: str) -> List[str]:
    """Set the required environment variables for a classic confined build."""
    env = []

    core_path = common.get_core_path(base)
    paths = common.get_library_paths(core_path, arch_triplet, existing_only=False)
    env.append(
        formatting_utils.format_path_variable(
            "LD_LIBRARY_PATH", paths, prepend="", separator=":"
        )
    )

    return env


def runtime_env(root: str, arch_triplet: str) -> List[str]:
    """Set the environment variables required for running binaries."""
    env = []

    env.append(
        'PATH="'
        + ":".join(
            ["{0}/usr/sbin", "{0}/usr/bin", "{0}/sbin", "{0}/bin", "$PATH"]
        ).format(root)
        + '"'
    )

    # Add the default LD_LIBRARY_PATH
    paths = common.get_library_paths(root, arch_triplet)
    # Add more specific LD_LIBRARY_PATH from staged packages if necessary
    paths += elf.determine_ld_library_path(root)

    if paths:
        env.append(
            formatting_utils.format_path_variable(
                "LD_LIBRARY_PATH", paths, prepend="", separator=":"
            )
        )

    return env


def build_env(root: str, snap_name: str, arch_triplet: str) -> List[str]:
    """Set the environment variables required for building.

    This is required for the current parts installdir due to stage-packages
    and also to setup the stagedir.
    """
    env = []

    paths = common.get_include_paths(root, arch_triplet)
    if paths:
        for envvar in ["CPPFLAGS", "CFLAGS", "CXXFLAGS"]:
            env.append(
                formatting_utils.format_path_variable(
                    envvar, paths, prepend="-I", separator=" "
                )
            )

    paths = common.get_library_paths(root, arch_triplet)
    if paths:
        env.append(
            formatting_utils.format_path_variable(
                "LDFLAGS", paths, prepend="-L", separator=" "
            )
        )

    paths = common.get_pkg_config_paths(root, arch_triplet)
    if paths:
        env.append(
            formatting_utils.format_path_variable(
                "PKG_CONFIG_PATH", paths, prepend="", separator=":"
            )
        )

    return env


def build_env_for_stage(stagedir: str, snap_name: str, arch_triplet: str) -> List[str]:
    env = build_env(stagedir, snap_name, arch_triplet)
    env.append('PERL5LIB="{0}/usr/share/perl5/"'.format(stagedir))

    return env


def snapcraft_part_environment(part: pluginhandler.PluginHandler) -> Dict[str, str]:
    return {
        "SNAPCRAFT_PART_SRC": part.plugin.sourcedir,
        "SNAPCRAFT_PART_BUILD": part.plugin.builddir,
        "SNAPCRAFT_PART_INSTALL": part.plugin.installdir,
    }
