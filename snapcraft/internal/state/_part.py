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
from typing import Any, Dict

from ._base import Base


class Part(Base):
    __tablename__ = "parts"
    name = sqlalchemy.Column(sqlalchemy.String, primary_key=True)
    project_id = sqlalchemy.Column(
        sqlalchemy.Integer, sqlalchemy.ForeignKey("projects.id")
    )
    properties = sqlalchemy.Column(sqlalchemy.PickleType)

    project = sqlalchemy.orm.relationship("Project", back_populates="parts")
    pull_step = sqlalchemy.orm.relationship(
        "PullStep", uselist=False, back_populates="part", cascade="all, delete-orphan"
    )
    build_step = sqlalchemy.orm.relationship(
        "BuildStep", uselist=False, back_populates="part", cascade="all, delete-orphan"
    )
    stage_step = sqlalchemy.orm.relationship(
        "StageStep", uselist=False, back_populates="part", cascade="all, delete-orphan"
    )
    prime_step = sqlalchemy.orm.relationship(
        "PrimeStep", uselist=False, back_populates="part", cascade="all, delete-orphan"
    )

    def __init__(self, *, name: str, properties: Dict[str, Any]) -> None:
        self.name = name
        if properties:
            self.properties = properties
        else:
            self.properties = {}
