#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id: STLExporter.py 990 2011-02-14 01:11:36Z sumpfralle $

Copyright 2010 Lars Kruse <devel@sumpfralle.de>

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

from pycam import VERSION
import datetime
import os

class STLExporter:

    def __init__(self, model, name="model", created_by="pycam", linesep=None,
            **kwargs):
        self.model = model
        self.name = name
        self.created_by = created_by
        if linesep is None:
            self.linesep = os.linesep
        else:
            self.linesep = linesep

    def __str__(self):
        return self.linesep.join(self.get_output_lines)

    def write(self, stream):
        for line in self.get_output_lines():
            stream.write(line)
            stream.write(self.linesep)

    def get_output_lines(self):
        date = datetime.date.today().isoformat()
        yield """solid "%s"; Produced by %s (v%s), %s""" \
                % (self.name, self.created_by, VERSION, date)
        for triangle in self.model.triangles():
            norm = triangle.normal.normalized()
            yield "facet normal %f %f %f" % (norm.x, norm.y, norm.z)
            yield "  outer loop"
            # Triangle vertices are stored in clockwise order - thus we need
            # to reverse the order (STL expects counter-clockwise orientation).
            for point in (triangle.p1, triangle.p3, triangle.p2):
                yield "    vertex %f %f %f" % (point.x, point.y, point.z)
            yield "  endloop"
            yield "endfacet"
        yield "endsolid"

