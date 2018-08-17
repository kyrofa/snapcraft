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
from typing import Any, Dict, List, Set, Union

from .._base import Base


@enum.unique
class MetadataSource(enum.Enum):
    EXTRACTED = 1
    SCRIPTLET = 2


class Metadata(Base):
    __tablename__ = "metadata"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    step_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("steps.id"))
    source = sqlalchemy.Column(sqlalchemy.Enum(MetadataSource))
    common_id = sqlalchemy.Column(sqlalchemy.String)
    summary = sqlalchemy.Column(sqlalchemy.String)
    description = sqlalchemy.Column(sqlalchemy.String)
    version = sqlalchemy.Column(sqlalchemy.String)
    grade = sqlalchemy.Column(sqlalchemy.String)
    icon = sqlalchemy.Column(sqlalchemy.String)
    desktop_file_paths = sqlalchemy.Column(sqlalchemy.PickleType)
    files = sqlalchemy.Column(sqlalchemy.PickleType)

    __mapper_args__ = {"polymorphic_on": source, "polymorphic_identity": "metadata"}

    def __init__(
        self,
        *,
        common_id: str = "",
        summary: str = "",
        description: str = "",
        version: str = "",
        grade: str = "",
        icon: str = "",
        desktop_file_paths: List[str] = None,
        files: List[str] = None,
    ) -> None:
        """Create a new Metadata instance.

        :param str: common_id: The common identifier across multiple packaging
            formats
        :param str summary: Extracted summary
        :param str description: Extracted description
        :param str version: Extracted version
        :param str grade: Extracted grade
        :param str icon: Extracted icon
        :param list desktop_file_paths: Extracted desktop file paths
        :param list files: Files from which metadata was extracted
        """

        self.common_id = common_id
        self.summary = summary
        self.description = description
        self.version = version
        self.grade = grade
        self.icon = icon

        if desktop_file_paths:
            self.desktop_file_paths = desktop_file_paths
        else:
            self.desktop_file_paths = []

        if files:
            self.files = files
        else:
            self.files = []

        instance = sqlalchemy.inspect(self)
        self._attributes = [a.key for a in instance.mapper.column_attrs]

    def update(self, other: "Metadata") -> None:
        """Update this metadata with other metadata.

        Note that the other metadata will take precedence, and may overwrite
        data contained here.

        :param Metadata other: Metadata from which to update
        """
        for attribute in self._attributes:
            other_value = getattr(other, attribute)
            if other_value:
                setattr(self, attribute, other_value)

    def to_dict(self) -> Dict[str, Union[str, List[str]]]:
        """Return all extracted metadata.

        :returns: All extracted metadata in dict form.
        :rtype: dict
        """
        metadata = dict()  # type: Dict[str, Union[str, List[str]]]
        for key in self._attributes:
            value = getattr(self, key)
            if value:
                metadata[key] = value

        return metadata

    def overlap(self, other: "Metadata") -> Set[str]:
        """Return all overlapping keys between this and other.

        :returns: All overlapping keys between this and other
        :rtype: set
        """
        return set(self.to_dict().keys() & other.to_dict().keys())

    def __eq__(self, other: Any) -> bool:
        if type(other) is type(self):
            for attribute in self._attributes:
                if getattr(self, attribute) != getattr(other, attribute):
                    return False
            return True

        return False

    def __len__(self) -> int:
        return self.to_dict().__len__()
