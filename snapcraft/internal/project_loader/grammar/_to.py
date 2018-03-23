# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2017 Canonical Ltd
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

import re

from .errors import (
    ToStatementSyntaxError,
    UnsatisfiedStatementError,
)

_SELECTOR_PATTERN = re.compile(r'\Ato\s+([^,\s](?:,?[^,]+)*)\Z')
_WHITESPACE_PATTERN = re.compile(r'\A.*\s.*\Z')


class ToStatement:
    """Process a 'to' statement in the grammar.

    For example:
    >>> import tempfile
    >>> from snapcraft import ProjectOptions
    >>> from snapcraft.internal.project_loader import grammar
    >>> def checker(primitive):
    ...     return True
    >>> options = ProjectOptions(target_deb_arch='i386')
    >>> processor = grammar.GrammarProcessor(None, options, checker)
    >>> clause = ToStatement(to='to armhf', body=['foo'], processor=processor)
    >>> clause.add_else(['bar'])
    >>> clause.process()
    {'bar'}
    """

    def __init__(self, *, to, body, processor):
        """Create an _ToStatement instance.

        :param str to: The 'to <selectors>' part of the clause.
        :param list body: The body of the 'to' clause.
        :param project_options: Instance of ProjectOptions to use to process
                                clause.
        :type project_options: snapcraft.ProjectOptions
        :param checker: callable accepting a single primitive, returning
                        true if it is valid
        :type checker: callable
        """

        self.selectors = _extract_to_clause_selectors(to)
        self._body = body
        self._processor = processor
        self._else_bodies = []

    def add_else(self, else_body):
        """Add an 'else' clause to the statement.

        :param list else_body: The body of an 'else' clause.

        The 'else' clauses will be processed in the order they are added.
        """

        self._else_bodies.append(else_body)

    def check(self):
        target_arch = self._processor.project_options.deb_arch

        # The only selector currently supported is the target arch. Since
        # selectors are matched with an AND, not OR, there should only be one
        # selector.
        return (len(self.selectors) == 1) and (target_arch in self.selectors)

    def process_body(self):
        """Process the clause.

        :return: Primitives as determined by evaluating the statement.
        :rtype: list
        """

        return self._processor.process(grammar=self._body)

    def process_else(self):
        primitives = set()

        for else_body in self._else_bodies:
            if not else_body:
                # Handle the 'else fail' case.
                raise UnsatisfiedStatementError(self)

            primitives = self._processor.process(grammar=else_body)
            if primitives:
                break

        return primitives


    def __eq__(self, other):
        return self.selectors == other.selectors

    def __repr__(self):
        return "'to {}'".format(','.join(sorted(self.selectors)))


def _extract_to_clause_selectors(to):
    """Extract the list of selectors within a to clause.

    :param str to: The 'to <selector>' part of the 'to' clause.

    :return: Selectors found within the 'to' clause.
    :rtype: set

    For example:
    >>> _extract_to_clause_selectors('to amd64,i386') == {'amd64', 'i386'}
    True
    """

    match = _SELECTOR_PATTERN.match(to)

    try:
        selector_group = match.group(1)
    except AttributeError:
        raise ToStatementSyntaxError(to, message='selectors are missing')
    except IndexError:
        raise ToStatementSyntaxError(to)

    # This could be part of the _SELECTOR_PATTERN, but that would require us
    # to provide a very generic error when we can try to be more helpful.
    if _WHITESPACE_PATTERN.match(selector_group):
        raise ToStatementSyntaxError(
            to, message='spaces are not allowed in the selectors')

    return {selector.strip() for selector in selector_group.split(',')}
