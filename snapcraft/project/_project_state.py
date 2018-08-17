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


class ProjectState:
    def __init__(self, *, project, database_path: str) -> None:
        from snapcraft.internal import state

        self._db_session = state.get_database_session_factory(database_path)()

        # Load project from database, or initialize one (there should only ever be one)
        self.project = self._db_session.query(state.Project).first()
        if not self.project:
            self.project = state.Project(project)
            self._db_session.add(self.project)

    @contextlib.contextmanager
    def _database_session(self):
        """Provide a transactional scope around database operations."""

        try:
            yield self._db_session
            self._db_session.commit()
        except Exception:
            self._db_session.rollback()
            raise
        finally:
            self._db_session.refresh(self.project)

    def save(self) -> None:
        with self._database_session() as session:
            session.add(self.project)
