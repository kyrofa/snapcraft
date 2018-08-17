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
from typing import List, Set

from ._step import Step
from .._metadata import ScriptletMetadata


class PrimeStep(Step):
    part = sqlalchemy.orm.relationship("Part", back_populates="prime_step")

    __mapper_args__ = {"polymorphic_identity": "prime"}

    def __init__(
        self,
        *,
        scriptlet_metadata: ScriptletMetadata,
        files: List[str],
        directories: List[str],
        dependencies: List[str]
    ) -> None:
        super().__init__(
            scriptlet_metadata=scriptlet_metadata,
            files=files,
            directories=directories,
            dependencies=dependencies,
        )

    def _part_property_names(self) -> Set[str]:
        """Return the part property names that concern this step."""

        return {"override-prime", "prime"}

    def _project_option_names(self) -> Set[str]:
        """Return the project option names that concern this step."""
        return set()
