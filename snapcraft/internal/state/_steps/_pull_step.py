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

import sqlalchemy
from typing import Any, Dict, Set

from ._step import Step
from .._metadata import ExtractedMetadata, ScriptletMetadata


class PullStep(Step):
    part = sqlalchemy.orm.relationship("Part", back_populates="pull_step")

    __mapper_args__ = {"polymorphic_identity": "pull"}

    def __init__(
        self,
        *,
        manifest: Dict[str, Any],
        extracted_metadata: ExtractedMetadata,
        scriptlet_metadata: ScriptletMetadata,
        property_names: Set[str]
    ) -> None:
        super().__init__(
            manifest=manifest,
            extracted_metadata=extracted_metadata,
            scriptlet_metadata=scriptlet_metadata,
        )

        self._property_names = property_names

    def _part_property_names(self) -> Set[str]:
        """Return the part property names that concern this step."""

        default_property_names = {
            "override-pull",
            "parse-info",
            "plugin",
            "source",
            "source-commit",
            "source-depth",
            "source-tag",
            "source-type",
            "source-branch",
            "source-subdir",
            "stage-packages",
        }

        return default_property_names | self._property_names

    def _project_option_names(self) -> Set[str]:
        """Return the project option names that concern this step."""
        return {"deb_arch"}
