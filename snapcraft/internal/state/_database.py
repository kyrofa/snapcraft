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

import alembic
import alembic.config
import logging
import os
import sqlalchemy

from snapcraft.internal import common

from ._base import Base

logger = logging.getLogger(__name__)


def get_database_session_factory(database_path: str):
    """Create the state database and run any pending migrations (if any).

    :param str database_path: Where to load/save database.
    """

    os.makedirs(os.path.dirname(database_path), exist_ok=True)

    database_url = "sqlite:///" + database_path
    _run_migrations(database_url)
    engine = sqlalchemy.create_engine(database_url)

    # Bind the engine to the metadata of the Base class so that the
    # declaratives can be accessed through a session instance
    Base.metadata.bind = engine

    return sqlalchemy.orm.scoped_session(sqlalchemy.orm.sessionmaker(bind=engine))


def _run_migrations(database_url):
    # Alembic is a little too noisy when running the migrations
    logging.getLogger("alembic").setLevel(logging.WARN)

    alembic_cfg = alembic.config.Config()
    alembic_cfg.set_main_option(
        "script_location", os.path.join(common.get_databasedir(), "migrations")
    )
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)

    logger.debug("Running state database migrations (if any)")
    alembic.command.upgrade(alembic_cfg, "head")
