# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2016 Canonical Ltd
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

import textwrap

# To call a function with no args, use:
#     echo "function-name" > {call_fifo}
#     read status < {feedback_fifo}
#
# To call a function with an arg, it's always json, e.g.:
#
#     echo "function-name '{{\\"key\\": \\"$1\\"}}'" > {call_fifo}
#     read status < {feedback_fifo}


_TEMPLATE = textwrap.dedent("""\
    snapcraft_build()
    {{
        echo "build" > {call_fifo}
        read status < {feedback_fifo}
    }}
""")


def functions(*, call_fifo, feedback_fifo):
    return _TEMPLATE.format(call_fifo=call_fifo, feedback_fifo=feedback_fifo)
