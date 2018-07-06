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

import copy
import functools
import logging
import os
from typing import Any, Dict, List
import yaml

from snapcraft.internal import common
from . import errors

logger = logging.getLogger(__name__)


def apply_templates(yaml_data: Dict[str, Any]) -> Dict[str, Any]:
    # Don't modify the dict passed in
    yaml_data = copy.deepcopy(yaml_data)

    global_template_names = yaml_data.get('templates', [])
    for app_name, app_definition in yaml_data.get('apps', dict()).items():
        template_names = app_definition.get('templates')

        # Make sure global templates are assigned to any app without templates
        if template_names is None:
            template_names = global_template_names

        for template_name in template_names:
            template_data = _find_template(template_name)
            _apply_app_template(
                yaml_data, app_name, template_name, template_data)

    return yaml_data


# Don't load the same template multiple times
@functools.lru_cache()
def _find_template(template_name: str) -> Dict[str, Any]:
    template_yaml_path = os.path.join(
        common.get_templatesdir(), template_name, 'template.yaml')

    if not os.path.isdir(os.path.dirname(template_yaml_path)):
        raise errors.TemplateNotFoundError(template_name)

    with open(template_yaml_path, 'r') as f:
        template_data = yaml.safe_load(f)

    return template_data


def _apply_app_template(yaml_data: Dict[str, Any], app_name: str,
                        template_name: str, template_data: Dict[str, Any]):
    parts = yaml_data['parts']
    # Add any parts specified in the template
    for part_name, part_definition in template_data.get('parts', {}).items():
        if part_name in parts:
            logger.warn(
                '{!r} part already specified, not including that part from '
                '{!r} template'.format(part_name, template_name))
        else:
            parts[part_name] = part_definition

    # Now apply the app-specific components
    app_definition = yaml_data['apps'][app_name]
    for property_name, property_value in template_data.get('apps', {}).items():
        app_definition[property_name] = _apply_template_property(
            property_name, app_definition.get(property_name), property_value)

    # Now that templates have been applied, no need to continue specifying them
    del yaml_data['apps'][app_name]['templates']


def _apply_template_property(property_name: str, existing_property: Any,
                             template_property: Any):
    if existing_property:
        # There are a few properties we need to merge instead of ignore
        if property_name == 'plugs' or property_name == 'command-chain':
            return _merge_lists(existing_property, template_property)
        return existing_property

    return template_property

def _merge_lists(list1: List[str], list2: List[str]) -> List[str]:
    """Merge two lists while maintaining order and removing duplicates."""
    seen = set()
    return [x for x in list1+list2 if not (x in seen or seen.add(x))]
