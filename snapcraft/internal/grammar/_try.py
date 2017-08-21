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

from . import process_grammar


class TryStatement:
    """Process a 'try' statement in the stage packages grammar.

    For example:
    >>> import tempfile
    >>> from snapcraft import ProjectOptions
    >>> def checker(primitive):
    ...     return 'invalid' not in primitive
    >>> with tempfile.TemporaryDirectory() as cache_dir:
    ...     options = ProjectOptions(target_deb_arch='i386')
    ...     clause = TryStatement(body=['invalid'], project_options=options,
    ...                           checker=checker)
    ...     clause.add_else(['valid'])
    ...     clause.process()
    {'valid'}
    """

    def __init__(self, *, body, project_options, checker):
        """Create an _OnStatement instance.

        :param list body: The body of the 'try' clause.
        :param project_options: Instance of ProjectOptions to use to process
                                clause.
        :type project_options: snapcraft.ProjectOptions
        :param checker: callable accepting a single primitive, returning
                        true if it is valid
        :type checker: callable
        """

        self._body = body
        self._project_options = project_options
        self._checker = checker
        self._else_bodies = []

    def add_else(self, else_body):
        """Add an 'else' clause to the statement.

        :param list else_body: The body of an 'else' clause.

        The 'else' clauses will be processed in the order they are added.
        """

        self._else_bodies.append(else_body)

    def process(self):
        """Process the clause.

        :return: Stage packages as determined by evaluating the statement.
        :rtype: list
        """

        packages = process_grammar(
            self._body, self._project_options, self._checker)

        # If some of the packages in the 'try' were invalid, then we need to
        # process the 'else' clauses.
        if not _all_packages_valid(packages, self._checker):
            if not self._else_bodies:
                # If there are no 'else' statements, the 'try' was considered
                # optional and it failed, which means it doesn't resolve to
                # any packages.
                return set()

            for else_body in self._else_bodies:
                if not else_body:
                    continue

                packages = process_grammar(
                    else_body, self._project_options, self._checker)

                # Stop once an 'else' clause gives us valid packages
                if _all_packages_valid(packages, self._checker):
                    break

        return packages

    def __repr__(self):
        return "'try'"


def _all_packages_valid(packages, checker):
    """Ensure that all packages are valid.

    :param packages: Iterable container of package names.
    :param checker: callable accepting a single primitive, returning
                    true if it is valid
    :type checker: callable

    For example:
    >>> import tempfile
    >>> from snapcraft import ProjectOptions
    >>> def checker(primitive):
    ...     return 'invalid' not in primitive
    >>> with tempfile.TemporaryDirectory() as cache_dir:
    ...     _all_packages_valid(['valid'], checker)
    ...     _all_packages_valid(['valid', 'invalid'], checker)
    True
    False
    """

    for package in packages:
        if not checker(package):
            return False
    return True
