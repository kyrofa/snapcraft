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

from ._base import Base


class Part(Base):
    __tablename__ = "parts"
    name = sqlalchemy.Column(sqlalchemy.String, primary_key=True)
    pull_step = sqlalchemy.orm.relationship("PullStep", uselist=False, back_populates="part", cascade="all, delete-orphan")
    build_step = sqlalchemy.orm.relationship("BuildStep", uselist=False, back_populates="part", cascade="all, delete-orphan")
    stage_step = sqlalchemy.orm.relationship("StageStep", uselist=False, back_populates="part", cascade="all, delete-orphan")
    prime_step = sqlalchemy.orm.relationship("PrimeStep", uselist=False, back_populates="part", cascade="all, delete-orphan")
