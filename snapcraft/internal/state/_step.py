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
from typing import List

from ._base import Base
from ._step_file import StepFile
from ._step_directory import StepDirectory


class Step(Base):
    __tablename__ = "steps"
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    part_name = sqlalchemy.Column(
        sqlalchemy.String, sqlalchemy.ForeignKey("parts.name")
    )
    name = sqlalchemy.Column(sqlalchemy.String)

    files = sqlalchemy.orm.relationship("StepFile", back_populates="step", cascade="all, delete-orphan")
    directories = sqlalchemy.orm.relationship("StepDirectory", back_populates="step", cascade="all, delete-orphan")

    __mapper_args__ = {"polymorphic_on": name, "polymorphic_identity": "step"}

    def __init__(self, files: List[StepFile], directories: List[StepDirectory]) -> None:
        self.files = files
        self.directories = directories
