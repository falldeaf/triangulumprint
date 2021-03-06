# -*- coding: utf-8 -*-
"""
$Id: PointKdtree.py 629 2010-08-23 16:53:06Z sumpfralle $

Copyright 2009 Lode Leroy

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

from pycam.Geometry.utils import epsilon
from pycam.Geometry.Point import Point
from pycam.Geometry.kdtree import Node, kdtree


class PointKdtree(kdtree):
    def __init__(self, points=None, cutoff=5, cutoff_distance=0.5,
            tolerance=epsilon):
        if points is None:
            points = []
        self._n = None
        self.tolerance = tolerance
        nodes = []
        for p in points:
            n = Node()
            n.point = p
            n.bound = []
            n.bound.append(p.x)
            n.bound.append(p.y)
            n.bound.append(p.z)
            nodes.append(n)
        kdtree.__init__(self, nodes, cutoff, cutoff_distance)

    def dist(self, n1, n2):
        dx = n1.bound[0]-n2.bound[0]
        dy = n1.bound[1]-n2.bound[1]
        dz = n1.bound[2]-n2.bound[2]
        return dx*dx+dy*dy+dz*dz

    def Point(self, x, y, z):
        #return Point(x,y,z)
        if self._n:
            n = self._n
        else:
            n = Node()
        n.bound = []
        n.bound.append(x)
        n.bound.append(y)
        n.bound.append(z)
        (nn, dist) = self.nearest_neighbor(n, self.dist)
        if nn and (dist < self.tolerance):
            self._n = n
            return nn.p
        else:
            n.p = Point(x, y, z)
            self._n = None
            self.insert(n)
            return n.p

