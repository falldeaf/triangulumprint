# -*- coding: utf-8 -*-
"""
$Id: ZigZagCutter.py 974 2011-02-07 03:54:47Z sumpfralle $

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
from pycam.Toolpath import simplify_toolpath

class ZigZagCutter(pycam.PathProcessors.BasePathProcessor):
    def __init__(self, reverse=False):
        super(ZigZagCutter, self).__init__()
        self.curr_path = None
        self.scanline = None
        self.curr_scanline = None
        self.reverse = reverse

    def append(self, point):
        curr_path = None
        if self.curr_path == None:
            curr_path = Path()
            self.curr_path = curr_path
        else:
            curr_path = self.curr_path
            self.curr_path = None

        curr_path.append(point)

        if self.curr_path == None:
            if (self.scanline % 2) == 0:
                self.curr_scanline.append(curr_path)
            else:
                curr_path.reverse()
                self.curr_scanline.insert(0, curr_path)

    def new_direction(self, direction):
        self.scanline = 0

    def new_scanline(self):
        self.scanline += 1
        self.curr_scanline = []

    def end_scanline(self):
        for path in self.curr_scanline:
            simplify_toolpath(path)
            if self.reverse:
                path.reverse()
            self.paths.append(path)
        self.curr_scanline = None

