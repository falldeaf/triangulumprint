# -*- coding: utf-8 -*-
"""
$Id: PolygonCutter.py 974 2011-02-07 03:54:47Z sumpfralle $

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

import pycam.PathProcessors
from pycam.Geometry.Path import Path
from pycam.Geometry.PolygonExtractor import PolygonExtractor
from pycam.Toolpath import simplify_toolpath


class PolygonCutter(pycam.PathProcessors.BasePathProcessor):
    def __init__(self, reverse=False):
        super(PolygonCutter, self).__init__()
        self.curr_path = None
        self.scanline = None
        self.poly_extractor = PolygonExtractor(PolygonExtractor.MONOTONE)
        self.reverse = reverse

    def append(self, point):
        self.poly_extractor.append(point)

    def new_direction(self, direction):
        self.poly_extractor.new_direction(direction)

    def end_direction(self):
        self.poly_extractor.end_direction()

    def new_scanline(self):
        self.poly_extractor.new_scanline()

    def end_scanline(self):
        self.poly_extractor.end_scanline()

    def finish(self):
        self.poly_extractor.finish()
        paths = []
        source_paths = []
        if self.poly_extractor.hor_path_list:
            source_paths.extend(self.poly_extractor.hor_path_list)
        if self.poly_extractor.ver_path_list:
            source_paths.extend(self.poly_extractor.ver_path_list)
        for path in source_paths:
            points = path.points
            for i in range(0, (len(points)+1)/2):
                new_path = Path()
                if i % 2 == 0:
                    new_path.append(points[i])
                    new_path.append(points[-i-1])
                else:
                    new_path.append(points[-i-1])
                    new_path.append(points[i])
                paths.append(new_path)
        if paths:
            for path in paths:
                simplify_toolpath(path)
                if self.reverse:
                    path.reverse()
            self.paths.extend(paths)
            self.sort_layered()

