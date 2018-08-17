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

import enum
import sqlalchemy

from .._base import Base


@enum.unique
class ArtifactType(enum.Enum):
    FILE = 1
    DIRECTORY = 2
    DEPENDENCY = 3


class StepArtifact(Base):
    __tablename__ = "step_artifacts"
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    step_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("steps.id"))
    path = sqlalchemy.Column(sqlalchemy.String)
    type = sqlalchemy.Column(sqlalchemy.Enum(ArtifactType))

    __mapper_args__ = {"polymorphic_on": type, "polymorphic_identity": "step_artifact"}
