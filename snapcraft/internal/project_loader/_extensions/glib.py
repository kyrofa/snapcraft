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

from typing import Any, Dict

from snapcraft.internal import errors
from ._extension import Extension


class GlibExtensionClassicConfinementError(errors.SnapcraftError):
    fmt = "The glib extension doesn't support classic confinement."


class GlibExtension(Extension):
    supported_bases = ("core",)  # type: Tuple[str]

    def __init__(self, yaml_data: Dict[str, Any]) -> None:
        """Create a new GlibExtension.

        Note that this extension does not support classic snaps.

        :param dict yaml_data: Loaded snapcraft.yaml data.
        """

        super().__init__(yaml_data)

        if yaml_data.get("confinement") == "classic":
            raise GlibExtensionClassicConfinementError()

        self.app_snippet = {
            "passthrough": {
                "command-chain": ["snap/command-chain/glib-extension-launch"]
            }
        }

        self.part_snippet = {"after": ["glib-extension"]}

        self.parts = {
            "glib-extension": {
                "plugin": "make",
                "source": "$SNAPCRAFT_EXTENSIONS_DIR/glib",
                "build-packages": ["libglib2.0-dev"],
            }
        }

