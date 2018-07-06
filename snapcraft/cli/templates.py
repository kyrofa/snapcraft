# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2017-2018 Canonical Ltd
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

import click
import yaml
import sys

from ._options import get_project
from snapcraft.internal import project_loader


@click.group()
def templatecli(**kwargs):
    pass

@templatecli.command()
def explode(**kwargs):
    """Display snapcraft.yaml with all templates applied."""

    project = get_project(**kwargs)
    yaml_with_templates = project_loader.apply_templates(
        project.info.get_raw_snapcraft())

    # Loading the config applied all the templates, so just dump it back out
    yaml.safe_dump(
        yaml_with_templates, stream=sys.stdout, default_flow_style=False)
