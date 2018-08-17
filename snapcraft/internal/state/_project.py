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

from snapcraft import project
from ._base import Base


class Project(Base):
    __tablename__ = "projects"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    options = sqlalchemy.Column(sqlalchemy.PickleType)
    parts = sqlalchemy.orm.relationship(
        "Part", back_populates="project", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __init__(self, project: project.Project) -> None:
        self.options = {
            "use_geoip": project.use_geoip,
            "parallel_builds": project.parallel_builds,
            "parallel_build_count": project.parallel_build_count,
            "is_cross_compiling": project.is_cross_compiling,
            "target_arch": project.target_arch,
            "additional_build_packages": project.additional_build_packages,
            "arch_triplet": project.arch_triplet,
            "deb_arch": project.deb_arch,
            "kernel_arch": project.kernel_arch,
            "local_plugins_dir": project.local_plugins_dir,
            "parts_dir": project.parts_dir,
            "stage_dir": project.stage_dir,
            "prime_dir": project.prime_dir,
            "debug": project.debug,
        }
