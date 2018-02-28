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

from . import process_grammar
from .errors import (
    UnsatisfiedStatementError,
)


class CompoundStatement:
    """Multiple statements that need to be treated as a group."""

    def __init__(self, *, statements, body, project_options, checker):
        """Create a CompoundStatement instance.

        :param list statements: List of statements in the group
        :param list body: The body of the compound statement.
        :param project_options: Instance of ProjectOptions to use to process
                                statements.
        :type project_options: snapcraft.ProjectOptions
        :param callable checker: callable accepting a single primitive,
                                 returning true if it is valid
        :type checker: callable
        """

        self._statements = statements
        self._body = body
        self._project_options = project_options
        self._checker = checker
        self._else_bodies = []

    def add_else(self, else_body):
        """Add an 'else' clause to the compound statement.

        :param list else_body: The body of an 'else' clause.

        The 'else' clauses will be processed in the order they are added.
        """

        self._else_bodies.append(else_body)

    def process(self):
        """Process the compound statement.

        :return: Primitives as determined by evaluating the compound statement.
        :rtype: list
        """

        primitives = set()
        if self.matches():
            primitives = process_grammar(
                self._body, self._project_options, self._checker)
        else:
            for else_body in self._else_bodies:
                if not else_body:
                    # Handle the 'else fail' case.
                    raise UnsatisfiedStatementError(self)

                primitives = process_grammar(
                    else_body, self._project_options, self._checker)
                if primitives:
                    break

        return primitives

    def matches(self) -> bool:
        """See if each statement matches, in order."""

        for statement in self._statements:
            if not statement.matches():
                return False

        return True

    def __eq__(self, other):
        return self._statements == other._statements

    def __str__(self):
        representation = ''
        for statement in self._statements:
            representation += '{} '.format(statement)

        return representation.strip()

    def __repr__(self):
        return '{!r}'.format(self.__str__())
