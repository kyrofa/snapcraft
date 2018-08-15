# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
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

import contextlib

from snapcraft.internal import state


class ProjectState:
    def __init__(self, *, database_path) -> None:
        self._db_session_factory = state.get_database_session_factory(database_path)

    @contextlib.contextmanager
    def _database_session(self):
        """Provide a transactional scope around database operations."""

        session = self._db_session_factory()

        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def load_part_state(self, part_name: str) -> state.Part:
        with self._database_session() as session:
            return session.query(state.Part).filter_by(name=part_name).one()

    def save_part_state(self, part_state: state.Part) -> None:
        with self._database_session() as session:
            session.add(part_state)
