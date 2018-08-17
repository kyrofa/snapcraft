# -*- Mode:Python; indent-tabs-buildnil; tab-width:4 -*-
#
# Copyright (C) 2018 Canonical Ltd
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

import datetime
import sqlalchemy
from typing import Any, Dict, List, Set

from snapcraft.internal import steps
from .._base import Base
from .._step_artifacts import StepFile, StepDirectory, StepDependency  # noqa: F401
from .._metadata import ExtractedMetadata, ScriptletMetadata


class Step(Base):
    __tablename__ = "steps"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    part_name = sqlalchemy.Column(
        sqlalchemy.String, sqlalchemy.ForeignKey("parts.name")
    )
    name = sqlalchemy.Column(sqlalchemy.Enum(steps.STEPS))
    manifest = sqlalchemy.Column(sqlalchemy.PickleType)

    files = sqlalchemy.orm.relationship(
        "StepFile", back_populates="step", cascade="all, delete-orphan"
    )
    directories = sqlalchemy.orm.relationship(
        "StepDirectory", back_populates="step", cascade="all, delete-orphan"
    )
    dependencies = sqlalchemy.orm.relationship(
        "StepDependency", back_populates="step", cascade="all, delete-orphan"
    )

    extracted_metadata = sqlalchemy.orm.relationship(
        "ExtractedMetadata",
        uselist=False,
        back_populates="step",
        cascade="all, delete-orphan",
    )
    scriptlet_metadata = sqlalchemy.orm.relationship(
        "ScriptletMetadata",
        uselist=False,
        back_populates="step",
        cascade="all, delete-orphan",
    )

    created_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)
    updated_at = sqlalchemy.Column(
        sqlalchemy.DateTime,
        default=datetime.datetime.now,
        onupdate=datetime.datetime.now,
    )

    __mapper_args__ = {"polymorphic_on": name, "polymorphic_identity": "step"}

    def __init__(
        self,
        *,
        manifest: Dict[str, Any] = None,
        extracted_metadata: ExtractedMetadata = None,
        scriptlet_metadata: ScriptletMetadata = None,
        files: List[str] = None,
        directories: List[str] = None,
        dependencies: List[str] = None
    ) -> None:
        self.manifest = manifest
        self.extracted_metadata = extracted_metadata
        self.scriptlet_metadata = scriptlet_metadata

        if files:
            self.files = files
        else:
            self.files = []

        if directories:
            self.directories = directories
        else:
            self.directories = []

        if dependencies:
            self.dependencies = dependencies
        else:
            self.dependencies = []

    def _part_property_names(self) -> Set[str]:
        """Return the part property names that concern this step.

        Note that these options come from the YAML for a given part.
        """
        raise NotImplementedError

    def _project_option_names(self) -> Set[str]:
        """Return the project option names that concern this step."""
        raise NotImplementedError

    def diff_part_properties_of_interest(self, other_properties):
        """Return set of part property names that differ."""

        saved_properties_of_interest = {
            k: v
            for k, v in self.part.properties.items()
            if k in self._part_property_names()
        }

        new_properties_of_interest = {
            k: v
            for k, v in other_properties.items()
            if k in self._part_property_names()
        }

        return _get_differing_keys(
            saved_properties_of_interest, new_properties_of_interest
        )

    def diff_project_options_of_interest(self, other_project):
        """Return set of project options that differ."""

        saved_options_of_interest = {
            k: v
            for k, v in self.part.project.options.items()
            if k in self._project_option_names()
        }

        new_options_of_interest = {
            k: v
            for k, v in other_project.options.items()
            if k in self._project_option_names()
        }

        return _get_differing_keys(saved_options_of_interest, new_options_of_interest)


def _get_differing_keys(dict1, dict2):
    differing_keys = set()
    for key, dict1_value in dict1.items():
        dict2_value = dict2.get(key)
        if dict1_value != dict2_value:
            differing_keys.add(key)

    for key, dict2_value in dict2.items():
        dict1_value = dict1.get(key)
        if dict1_value != dict2_value:
            differing_keys.add(key)

    return differing_keys
