# -*- coding: utf-8 -*-
"""
$Id: Path.py 975 2011-02-07 13:49:01Z sumpfralle $

Copyright 2010 Lars Kruse <devel@sumpfralle.de>
Copyright 2008 Lode Leroy

This file is part of PyCAM.

PyCAM is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

PyCAM is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with PyCAM.  If not, see <http://www.gnu.org/licenses/>.
"""

""" the points of a path are only used for describing coordinates. Thus we
don't really need complete "Point" instances that consume a lot of memory.
Since python 2.6 the "namedtuple" factory is available.
This reduces the memory consumption of a toolpath down to 1/3.
"""

try:
    # this works for python 2.6 or above (saves memory)
    # TODO: disabled for now - check if we could enable it later ...
    import INVALID_IMPORT
    from collections import namedtuple
    tuple_point = namedtuple("TuplePoint", "x y z")
    get_point_object = lambda point: tuple_point(point.x, point.y, point.z)
except ImportError:
    # dummy for python < v2.6 (consumes more memory)
    get_point_object = lambda point: point


class Path:
    id = 0
    def __init__(self):
        self.id = Path.id
        Path.id += 1
        self.top_join = None
        self.bot_join = None
        self.winding = 0
        self.points = []

    def __repr__(self):
        text = ""
        text += "path %d: " % self.id
        first = True
        for point in self.points:
            if first:
                first = False
            else:
                text += "-"
            text += "%d(%g,%g,%g)" % (point.id, point.x, point.y, point.z)
        return text

    def insert(self, index, point):
        self.points.insert(index, get_point_object(point))

    def append(self, point):
        self.points.append(get_point_object(point))

    def reverse(self):
        self.points.reverse()
