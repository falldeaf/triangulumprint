# -*- coding: utf-8 -*-
"""
$Id: Model.py 1092 2011-06-13 14:40:56Z sumpfralle $

Copyright 2008-2010 Lode Leroy
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

import pycam.Exporters.STLExporter
import pycam.Exporters.SVGExporter
from pycam.Geometry.Triangle import Triangle
from pycam.Geometry.Line import Line
from pycam.Geometry.Plane import Plane
from pycam.Geometry.Polygon import Polygon
from pycam.Geometry.Point import Point
from pycam.Geometry.TriangleKdtree import TriangleKdtree
from pycam.Geometry.Matrix import TRANSFORMATIONS
from pycam.Toolpath import Bounds
from pycam.Geometry.utils import INFINITE, epsilon
from pycam.Geometry import TransformableContainer
from pycam.Utils import ProgressCounter
import pycam.Utils.log
import uuid
import math
# OpenGLTools will be imported later, if necessary
#import pycam.Gui.OpenGLTools


try:
    import OpenGL.GL as GL
    GL_enabled = True
except ImportError:
    GL_enabled = False


log = pycam.Utils.log.get_logger()


class BaseModel(TransformableContainer):
    id = 0

    def __init__(self):
        self.id = BaseModel.id
        BaseModel.id += 1
        self._item_groups = []
        self.name = "model%d" % self.id
        self.minx = None
        self.miny = None
        self.minz = None
        self.maxx = None
        self.maxy = None
        self.maxz = None
        # derived classes should override this
        self._export_function = None
        self._opengl_display_cache = {}

    def __add__(self, other_model):
        """ combine two models """
        result = self.__class__()
        for item in self.next():
            result.append(item)
        for item in other_model.next():
            result.append(item)
        return result

    def __len__(self):
        """ Return the number of available items in the model.
        This is mainly useful for evaluating an empty model as False.
        """
        return sum([len(igroup) for igroup in self._item_groups])

    def next(self):
        for item_group in self._item_groups:
            for item in item_group:
                if isinstance(item, list):
                    for subitem in item:
                        yield subitem
                else:
                    yield item

    def get_children_count(self):
        result = 0
        for item_group in self._item_groups:
            for item in item_group:
                result += 1
                if hasattr(item, "get_children_count"):
                    result += item.get_children_count()
        return result

    def to_OpenGL(self, visible_filter=None, show_directions=False):
        if not GL_enabled:
            return
        if not visible_filter is None:
            for item in self.next():
                # ignore invisble things like the normal of a ContourModel
                if hasattr(item, "to_OpenGL"):
                    do_paint, color = visible_filter(item)
                    if do_paint:
                        item.to_OpenGL(color, show_directions=show_directions)
        elif not show_directions in self._opengl_display_cache:
            # compile an OpenGL display list
            # Rendering a display list takes less than 5% of the time for a
            # complete rebuild.
            list_index = GL.glGenLists(1)
            if list_index > 0:
                self._opengl_display_cache[show_directions] = list_index
                # somehow "GL_COMPILE_AND_EXECUTE" fails - we render it later
                GL.glNewList(list_index, GL.GL_COMPILE)
            for item in self.next():
                # ignore invisble things like the normal of a ContourModel
                if hasattr(item, "to_OpenGL"):
                    item.to_OpenGL(show_directions=show_directions)
            if list_index > 0:
                GL.glEndList()
                GL.glCallList(list_index)
        else:
            # render a previously compiled display list
            GL.glCallList(self._opengl_display_cache[show_directions])

    def is_export_supported(self):
        return not self._export_function is None

    def export(self, **kwargs):
        if self.is_export_supported():
            return self._export_function(self, **kwargs)
        else:
            raise NotImplementedError(("This type of model (%s) does not " \
                    + "support the 'export' function.") % str(type(self)))

    def _update_limits(self, item):
        # Ignore items without limit attributes (e.g. the normal of a
        # ContourModel).
        if hasattr(item, "minx"):
            if self.minx is None:
                self.minx = item.minx
                self.miny = item.miny
                self.minz = item.minz
                self.maxx = item.maxx
                self.maxy = item.maxy
                self.maxz = item.maxz
            else:
                self.minx = min(self.minx, item.minx)
                self.miny = min(self.miny, item.miny)
                self.minz = min(self.minz, item.minz)
                self.maxx = max(self.maxx, item.maxx)
                self.maxy = max(self.maxy, item.maxy)
                self.maxz = max(self.maxz, item.maxz)

    def append(self, item):
        self._update_limits(item)

    def extend(self, items):
        for item in items:
            self.append(item)

    def maxsize(self):
        return max(abs(self.maxx), abs(self.minx), abs(self.maxy),
                abs(self.miny), abs(self.maxz), abs(self.minz))

    def subdivide(self, depth):
        model = self.__class__()
        for item in self.next():
            for s in item.subdivide(depth):
                model.append(s)
        return model

    def reset_cache(self):
        self.minx = None
        self.miny = None
        self.minz = None
        self.maxx = None
        self.maxy = None
        self.maxz = None
        for item in self.next():
            self._update_limits(item)
        self._reset_opengl_display_cache()

    def _reset_opengl_display_cache(self):
        for index in self._opengl_display_cache.values():
            GL.glDeleteLists(index, 1)
        self._opengl_display_cache = {}

    def __del__(self):
        # Somehow remote pycam servers complain about this missing attribute
        # during cleanup.
        if GL_enabled and hasattr(self, "_opengl_display_cache"):
            self._reset_opengl_display_cache()

    def _get_progress_callback(self, update_callback):
        if update_callback:
            return ProgressCounter(self.get_children_count(),
                    update_callback=update_callback).increment
        else:
            return None

    def transform_by_template(self, direction="normal", callback=None):
        if direction in TRANSFORMATIONS.keys():
            self.transform_by_matrix(TRANSFORMATIONS[direction],
                    callback=self._get_progress_callback(callback))

    def shift(self, shift_x, shift_y, shift_z, callback=None):
        matrix = ((1, 0, 0, shift_x), (0, 1, 0, shift_y), (0, 0, 1, shift_z))
        self.transform_by_matrix(matrix,
                callback=self._get_progress_callback(callback))
        
    def scale(self, scale_x, scale_y=None, scale_z=None, callback=None):
        if scale_y is None:
            scale_y = scale_x
        if scale_z is None:
            scale_z = scale_x
        matrix = ((scale_x, 0, 0, 0), (0, scale_y, 0, 0), (0, 0, scale_z, 0))
        self.transform_by_matrix(matrix,
                callback=self._get_progress_callback(callback))

    def get_bounds(self):
        return Bounds(Bounds.TYPE_CUSTOM, (self.minx, self.miny, self.minz),
                (self.maxx, self.maxy, self.maxz))


class Model(BaseModel):

    def __init__(self, use_kdtree=True):
        super(Model, self).__init__()
        self._triangles = []
        self._item_groups.append(self._triangles)
        self._export_function = pycam.Exporters.STLExporter.STLExporter
        # marker for state of kdtree and uuid
        self._dirty = True
        # enable/disable kdtree
        self._use_kdtree = use_kdtree
        self._t_kdtree = None
        self.__flat_groups_cache = {}
        self.__uuid = None
        
    def __len__(self):
        """ Return the number of available items in the model.
        This is mainly useful for evaluating an empty model as False.
        """
        return len(self._triangles)

    @property
    def uuid(self):
        if (self.__uuid is None) or self._dirty:
            self._update_caches()
        return self.__uuid

    def append(self, item):
        super(Model, self).append(item)
        if isinstance(item, Triangle):
            self._triangles.append(item)
            # we assume, that the kdtree needs to be rebuilt again
            self._dirty = True

    def reset_cache(self):
        super(Model, self).reset_cache()
        # the triangle kdtree needs to be reset after transforming the model
        self._update_caches()

    def _update_caches(self):
        if self._use_kdtree:
            self._t_kdtree = TriangleKdtree(self.triangles())
        self.__uuid = str(uuid.uuid4())
        self.__flat_groups_cache = {}
        # the kdtree is up-to-date again
        self._dirty = False

    def triangles(self, minx=-INFINITE, miny=-INFINITE, minz=-INFINITE,
            maxx=+INFINITE, maxy=+INFINITE, maxz=+INFINITE):
        if (minx == miny == minz == -INFINITE) \
                and (maxx == maxy == maxz == +INFINITE):
            return self._triangles
        if self._use_kdtree:
            # update the kdtree, if new triangles were added meanwhile
            if self._dirty:
                self._update_caches()
            return self._t_kdtree.Search(minx, maxx, miny, maxy)
        return self._triangles

    def get_waterline_contour(self, plane):
        collision_lines = []
        for t in self._triangles:
            collision_line = plane.intersect_triangle(t, counter_clockwise=True)
            if not collision_line is None:
                collision_lines.append(collision_line)
        # combine these lines into polygons
        contour = ContourModel(plane=plane)
        for line in collision_lines:
            contour.append(line)
        log.debug("Waterline: %f - %d - %s" % (plane.p.z,
                len(contour.get_polygons()),
                [len(p.get_lines()) for p in contour.get_polygons()]))
        return contour

    def get_flat_areas(self, min_area=None):
        """ Find plane areas (combinations of triangles) bigger than 'min_area'
        and ignore vertical planes. The result is cached.
        """
        if not self.__flat_groups_cache.has_key(min_area):
            def has_shared_edge(t1, t2):
                count = 0
                for p in (t1.p1, t1.p2, t1.p3):
                    if p in (t2.p1, t2.p2, t2.p3):
                        count += 1
                return count >= 2
            groups = []
            for t in self.triangles():
                # Find all groups with the same direction (see 'normal') that
                # share at least one edge with the current triangle.
                touch_groups = []
                if t.normal.z == 0:
                    # ignore vertical triangles
                    continue
                for group_index, group in enumerate(groups):
                    if t.normal == group[0].normal:
                        for group_t in group:
                            if has_shared_edge(t, group_t):
                                touch_groups.append(group_index)
                                break
                if len(touch_groups) > 1:
                    # combine multiple areas with this new triangle
                    touch_groups.reverse()
                    combined = [t]
                    for touch_group_index in touch_groups:
                        combined.extend(groups.pop(touch_group_index))
                    groups.append(combined)
                elif len(touch_groups) == 1:
                    groups[touch_groups[0]].append(t)
                else:
                    groups.append([t])
            # check the size of each area
            if not min_area is None:
                groups = [group for group in groups
                        if sum([t.get_area() for t in group]) >= min_area]
            self.__flat_groups_cache[min_area] = groups
        return self.__flat_groups_cache[min_area]


class ContourModel(BaseModel):

    def __init__(self, plane=None):
        super(ContourModel, self).__init__()
        self.name = "contourmodel%d" % self.id
        if plane is None:
            # the default plane points upwards along the z axis
            plane = Plane(Point(0, 0, 0), Point(0, 0, 1))
        self._plane = plane
        self._line_groups = []
        self._item_groups.append(self._line_groups)
        # there is always just one plane
        self._plane_groups = [self._plane]
        self._item_groups.append(self._plane_groups)
        self._cached_offset_models = {}
        self._export_function = \
                pycam.Exporters.SVGExporter.SVGExporterContourModel

    def __len__(self):
        """ Return the number of available items in the model.
        This is mainly useful for evaluating an empty model as False.
        """
        return len(self._line_groups)

    def reset_cache(self):
        super(ContourModel, self).reset_cache()
        # reset the offset model cache
        self._cached_offset_models = {}

    def _merge_polygon_if_possible(self, other_polygon, allow_reverse=False):
        """ Check if the given 'other_polygon' can be connected to another
        polygon of the the current model. Both polygons are merged if possible.
        This function should be called after any "append" event, if the lines to
        be added are given in a random order (e.g. by the "waterline" function).
        """
        if other_polygon.is_closed:
            return
        connectors = []
        connectors.append(other_polygon.get_points()[0])
        connectors.append(other_polygon.get_points()[-1])
        # filter all polygons that can be combined with 'other_polygon'
        connectables = []
        for lg in self._line_groups:
            if lg is other_polygon:
                continue
            for connector in connectors:
                if lg.is_connectable(connector):
                    connectables.append(lg)
                    break
        # merge 'other_polygon' with all other connectable polygons
        for polygon in connectables:
            # check again, if the polygon is still connectable
            for connector in connectors:
                if polygon.is_connectable(connector):
                    break
            else:
                # skip this polygon
                continue
            if other_polygon.get_points()[-1] == polygon.get_points()[0]:
                for line in polygon.get_lines():
                    if other_polygon.is_closed:
                        return
                    other_polygon.append(line)
                self._line_groups.remove(polygon)
            elif other_polygon.get_points()[0] == polygon.get_points()[-1]:
                lines = polygon.get_lines()
                lines.reverse()
                for line in lines:
                    if other_polygon.is_closed:
                        return
                    other_polygon.append(line)
                self._line_groups.remove(polygon)
            elif allow_reverse:
                if other_polygon.get_points()[-1] == polygon.get_points()[-1]:
                    polygon.reverse_direction()
                    for line in polygon.get_lines():
                        if other_polygon.is_closed:
                            return
                        other_polygon.append(line)
                    self._line_groups.remove(polygon)
                elif other_polygon.get_points()[0] == polygon.get_points()[0]:
                    polygon.reverse_direction()
                    lines = polygon.get_lines()
                    lines.reverse()
                    for line in lines:
                        if other_polygon.is_closed:
                            return
                        other_polygon.append(line)
                    self._line_groups.remove(polygon)
                else:
                    pass
            else:
                pass
            if other_polygon.is_closed:
                # we are finished
                return

    def append(self, item, unify_overlaps=False, allow_reverse=False):
        super(ContourModel, self).append(item)
        if isinstance(item, Line):
            item_list = [item]
            if allow_reverse:
                item_list.append(Line(item.p2, item.p1))
            found = False
            # Going back from the end to start. The last line_group always has
            # the highest chance of being suitable for the next line.
            line_group_indexes = xrange(len(self._line_groups) - 1, -1, -1)
            for line_group_index in line_group_indexes:
                line_group = self._line_groups[line_group_index]
                for candidate in item_list:
                    if line_group.is_connectable(candidate):
                        line_group.append(candidate)
                        self._merge_polygon_if_possible(line_group,
                                allow_reverse=allow_reverse)
                        found = True
                        break
                if found:
                    break
            else:
                # add a single line as part of a new group
                new_line_group = Polygon(plane=self._plane)
                new_line_group.append(item)
                self._line_groups.append(new_line_group)
        elif isinstance(item, Polygon):
            if not unify_overlaps or (len(self._line_groups) == 0):
                self._line_groups.append(item)
                for subitem in item.next():
                    self._update_limits(subitem)
            else:
                # go through all polygons and check if they can be combined
                is_outer = item.is_outer()
                new_queue = [item]
                processed_polygons = []
                queue = self.get_polygons()
                while len(queue) > 0:
                    polygon = queue.pop()
                    if polygon.is_outer() != is_outer:
                        processed_polygons.append(polygon)
                    else:
                        processed = []
                        while len(new_queue) > 0:
                            new = new_queue.pop()
                            if new.is_polygon_inside(polygon):
                                # "polygon" is obsoleted by "new"
                                processed.extend(new_queue)
                                break
                            elif polygon.is_polygon_inside(new):
                                # "new" is obsoleted by "polygon"
                                continue
                            elif not new.is_overlap(polygon):
                                processed.append(new)
                                continue
                            else:
                                union = polygon.union(new)
                                if union:
                                    for p in union:
                                        if p.is_outer() == is_outer:
                                            new_queue.append(p)
                                        else:
                                            processed_polygons.append(p)
                                else:
                                    processed.append(new)
                                break
                        else:
                            processed_polygons.append(polygon)
                        new_queue = processed
                while len(self._line_groups) > 0:
                    self._line_groups.pop()
                print "Processed polygons: %s" % str([len(p.get_lines())
                        for p in processed_polygons])
                print "New queue: %s" % str([len(p.get_lines())
                        for p in new_queue])
                for processed_polygon in processed_polygons + new_queue:
                    self._line_groups.append(processed_polygon)
                # TODO: this is quite expensive - can we do it differently?
                self.reset_cache()
        else:
            # ignore any non-supported items (they are probably handled by a
            # parent class)
            pass

    def get_num_of_lines(self):
        return sum([len(group) for group in self._line_groups])

    def get_polygons(self, z=None, ignore_below=True):
        if z is None:
            return self._line_groups
        elif ignore_below:
            return [group for group in self._line_groups if group.minz == z]
        else:
            return [group for group in self._line_groups if group.minz <= z]

    def revise_directions(self, callback=None):
        """ Go through all open polygons and try to merge them regardless of
        their direction. Afterwards all closed polygons are analyzed regarding
        their inside/outside relationships.
        Beware: never use this function if the direction of lines may not
        change.
        """
        number_of_initial_closed_polygons = len([poly
                for poly in self.get_polygons() if poly.is_closed])
        open_polygons = [poly for poly in self.get_polygons()
                if not poly.is_closed]
        if callback:
            progress_callback = pycam.Utils.ProgressCounter(
                    2 * number_of_initial_closed_polygons + len(open_polygons),
                    callback).increment
        else:
            progress_callback = None
        # try to connect all open polygons
        for poly in open_polygons:
            self._line_groups.remove(poly)
        poly_open_before = len(open_polygons)
        for poly in open_polygons:
            for line in poly.get_lines():
                self.append(line, allow_reverse=True)
            if progress_callback and progress_callback():
                return
        poly_open_after = len([poly for poly in self.get_polygons()
                if not poly.is_closed])
        if poly_open_before != poly_open_after:
            log.info("Reduced the number of open polygons from " + \
                    "%d down to %d" % (poly_open_before, poly_open_after))
        else:
            log.debug("No combineable open polygons found")
        # auto-detect directions of closed polygons: inside and outside
        finished = []
        remaining_polys = [poly for poly in self.get_polygons()
                if poly.is_closed]
        if progress_callback:
            # shift the counter back by the number of new closed polygons
            progress_callback(2 * (number_of_initial_closed_polygons - \
                    len(remaining_polys)))
        remaining_polys.sort(key=lambda poly: abs(poly.get_area()))
        while remaining_polys:
            # pick the largest polygon
            current = remaining_polys.pop()
            # start with the smallest finished polygon
            for comp, is_outer in finished:
                if comp.is_polygon_inside(current):
                    finished.insert(0, (current, not is_outer))
                    break
            else:
                # no enclosing polygon was found
                finished.insert(0, (current, True))
            if progress_callback and progress_callback():
                return
        # Adjust the directions of all polygons according to the result
        # of the previous analysis.
        change_counter = 0
        for polygon, is_outer in finished:
            if polygon.is_outer() != is_outer:
                polygon.reverse_direction()
                change_counter += 1
            if progress_callback and progress_callback():
                self.reset_cache()
                return
        log.info("The winding of %d polygon(s) was fixed." % change_counter)
        self.reset_cache()

    def reverse_directions(self, callback=None):
        if callback:
            progress_callback = pycam.Utils.ProgressCounter(
                    len(self.get_polygons()), callback).increment
        else:
            progress_callback = None
        for polygon in self._line_groups:
            polygon.reverse_direction()
            if progress_callback and progress_callback():
                self.reset_cache()
                return
        self.reset_cache()

    def get_reversed(self):
        result = ContourModel(plane=self._plane)
        for poly in self.get_polygons():
            result.append(poly.get_reversed())
        return result

    def get_cropped_model_by_bounds(self, bounds):
        low, high = bounds.get_absolute_limits()
        return self.get_cropped_model(low[0], high[0], low[1], high[1],
                low[2], high[2])

    def get_cropped_model(self, minx, maxx, miny, maxy, minz, maxz):
        new_line_groups = []
        for group in self._line_groups:
            new_groups = group.get_cropped_polygons(minx, maxx, miny, maxy,
                    minz, maxz)
            if not new_groups is None:
                new_line_groups.extend(new_groups)
        if len(new_line_groups) > 0:
            result = ContourModel(plane=self._plane)
            for group in new_line_groups:
                result.append(group)
            return result
        else:
            return None

    def get_offset_model_simple(self, offset, callback=None):
        """ calculate a contour model that surrounds the current model with
        a given offset.
        This is mainly useful for engravings that should not proceed _on_ the
        lines but besides these.
        @value offset: shifting distance; positive values enlarge the model
        @type offset: float
        @value callback: function to call after finishing a single line.
            It should return True if the user interrupted the operation.
        @type callback: callable
        @returns: the new shifted model
        @rtype: pycam.Geometry.Model.Model
        """
        # use a cached offset model if it exists
        if offset in self._cached_offset_models:
            return self._cached_offset_models[offset]
        result = ContourModel(plane=self._plane)
        for group in self._line_groups:
            new_groups = group.get_offset_polygons(offset)
            if not new_groups is None:
                for new_group in new_groups:
                    result.append(new_group)
            if callback and callback():
                return None
        # cache the result
        self._cached_offset_models[offset] = result
        return result

    def get_offset_model(self, offset, callback=None):
        result = ContourModel(plane=self._plane)
        for group in self.get_polygons():
            new_groups = group.get_offset_polygons(offset, callback=callback)
            result.extend(new_groups)
            if callback and callback():
                return None
        return result

    def get_copy(self):
        result = ContourModel(plane=self._plane)
        for group in self.get_polygons():
            result.append(group)
        return result

    def check_for_collisions(self, callback=None, find_all_collisions=False):
        """ check if lines in different line groups of this model collide

        Returns a pycam.Geometry.Point.Point instance in case of an
        intersection.
        Returns None if the optional "callback" returns True (e.g. the user
        interrupted the operation).
        Otherwise it returns False if no intersections were found.
        """
        def check_bounds_of_groups(g1, g2):
            if (g1.minx <= g2.minx <= g1.maxx) \
                    or (g1.minx <= g2.maxx <= g1.maxx) \
                    or (g2.minx <= g1.minx <= g2.maxx) \
                    or (g2.minx <= g1.maxx <= g2.maxx):
                # the x boundaries overlap
                if (g1.miny <= g2.miny <= g1.maxy) \
                        or (g1.miny <= g2.maxy <= g1.maxy) \
                        or (g2.miny <= g1.miny <= g2.maxy) \
                        or (g2.miny <= g1.maxy <= g2.maxy):
                    # also the y boundaries overlap
                    if (g1.minz <= g2.minz <= g1.maxz) \
                            or (g1.minz <= g2.maxz <= g1.maxz) \
                            or (g2.minz <= g1.minz <= g2.maxz) \
                            or (g2.minz <= g1.maxz <= g2.maxz):
                        # z overlaps as well
                        return True
            return False
        # check each pair of line groups for intersections
        intersections = []
        for index1, group1 in enumerate(self._line_groups[:-1]):
            for index2, group2 in enumerate(self._line_groups):
                if index2 <= index1:
                    # avoid double-checks
                    continue
                # check if both groups overlap - otherwise skip this pair
                if check_bounds_of_groups(group1, group2):
                    # check each pair of lines for intersections
                    for line1 in group1.get_lines():
                        for line2 in group2.get_lines():
                            intersection, factor = line1.get_intersection(line2)
                            if intersection:
                                if find_all_collisions:
                                    intersections.append((index1, index2))
                                else:
                                    # return just the place of intersection
                                    return intersection
            # update the progress visualization and quit if requested
            if callback and callback():
                if find_all_collisions:
                    return intersections
                else:
                    return None
        if find_all_collisions:
            return intersections
        else:
            return False

    def extrude(self, stepping=None, func=None, callback=None):
        """ do a spherical extrusion of a 2D model.
        This is mainly useful for extruding text in a visually pleasent way ...
        """
        outer_polygons = [(poly, []) for poly in self._line_groups
                if poly.is_outer()]
        for poly in self._line_groups:
            # ignore open polygons
            if not poly.is_closed:
                continue
            if poly.is_outer():
                continue
            for outer_poly, children in outer_polygons:
                if outer_poly == poly:
                    break
                if outer_poly.is_polygon_inside(poly):
                    children.append(poly)
                    break
        model = Model()
        for poly, children in outer_polygons:
            if callback and callback():
                return None
            group = PolygonGroup(poly, children, callback=callback)
            new_model = group.extrude(func=func, stepping=stepping)
            if new_model:
                model += new_model
        return model

    def get_flat_projection(self, plane):
        result = ContourModel(plane)
        for polygon in self.get_polygons():
            new_polygon = polygon.get_plane_projection(plane)
            if new_polygon:
                result.append(new_polygon)
        return result or None


class PolygonGroup(object):
    """ A PolygonGroup consists of one outer and maybe multiple inner polygons.
    It is mainly used for 3D extrusion of polygons.
    """

    def __init__(self, outer, inner_list, callback=None):
        self.outer = outer
        self.inner = inner_list
        self.callback = callback
        self.lines = outer.get_lines()
        self.z_level = self.lines[0].p1.z
        for poly in inner_list:
            self.lines.extend(poly.get_lines())

    def extrude(self, func=None, stepping=None):
        if stepping is None:
            stepping = min(self.outer.maxx - self.outer.minx,
                    self.outer.maxy - self.outer.miny) / 80
        grid = []
        for line in self._get_grid_matrix(stepping=stepping):
            line_points = []
            for x, y in line:
                z = self.calculate_point_height(x, y, func)
                line_points.append((x, y, z))
            if self.callback and self.callback():
                return None
            grid.append(line_points)
        # calculate the triangles within the grid
        triangle_optimizer = TriangleOptimizer(callback=self.callback)
        for line in range(len(grid) - 1):
            for row in range(len(grid[0]) - 1):
                coords = []
                coords.append(grid[line][row])
                coords.append(grid[line][row + 1])
                coords.append(grid[line + 1][row + 1])
                coords.append(grid[line + 1][row])
                items = self._fill_grid_positions(coords)
                for item in items:
                    triangle_optimizer.append(item)
                    # create the backside plane
                    backside_points = []
                    for p in item.get_points():
                        backside_points.insert(0, Point(p.x, p.y, self.z_level))
                    triangle_optimizer.append(Triangle(*backside_points))
            if self.callback and self.callback():
                return None
        triangle_optimizer.optimize()
        model = Model()
        for triangle in triangle_optimizer.get_triangles():
            model.append(triangle)
        return model

    def _get_closest_line_collision(self, probe_line):
        min_dist = None
        min_cp = None
        for line in self.lines:
            cp, dist = probe_line.get_intersection(line)
            if cp and ((min_dist is None) or (dist < min_dist)):
                min_dist = dist
                min_cp = cp
        if min_dist > 0:
            return min_cp
        else:
            return None

    def _fill_grid_positions(self, coords):
        """ Try to find suitable alternatives, if any of the corners of this
        square grid is not valid.
        The current strategy: find the points of intersection with the contour
        on all incomplete edges of the square.
        The _good_ strategy would be: crop the square by using all related
        lines of the contour.
        """
        def get_line(i1, i2):
            a = list(coords[i1 % 4])
            b = list(coords[i2 % 4])
            # the contour points of the model will always be at level zero
            a[2] = self.z_level
            b[2] = self.z_level
            return Line(Point(*a), Point(*b))
        valid_indices = [index for index, p in enumerate(coords)
                if not p[2] is None]
        none_indices = [index for index, p in enumerate(coords) if p[2] is None]
        valid_count = len(valid_indices)
        final_points = []
        if valid_count == 0:
            final_points.extend([None, None, None, None])
        elif valid_count == 1:
            fan_points = []
            for index in range(4):
                if index in none_indices:
                    probe_line = get_line(valid_indices[0], index)
                    cp = self._get_closest_line_collision(probe_line)
                    if cp:
                        fan_points.append(cp)
                    final_points.append(cp)
                else:
                    final_points.append(Point(*coords[index]))
            # check if the three fan_points are in line
            if len(fan_points) == 3:
                fan_points.sort()
                if Line(fan_points[0], fan_points[2]).is_point_inside(
                        fan_points[1]):
                    final_points.remove(fan_points[1])
        elif valid_count == 2:
            if sum(valid_indices) % 2 == 0:
                # the points are on opposite corners
                # The strategy below is not really good, but this special case
                # is hardly possible, anyway.
                for index in range(4):
                    if index in valid_indices:
                        final_points.append(Point(*coords[index]))
                    else:
                        probe_line = get_line(index - 1, index)
                        cp = self._get_closest_line_collision(probe_line)
                        final_points.append(cp)
            else:
                for index in range(4):
                    if index in valid_indices:
                        final_points.append(Point(*coords[index]))
                    else:
                        if ((index + 1) % 4) in valid_indices:
                            other_index = index + 1
                        else:
                            other_index = index - 1
                        probe_line = get_line(other_index, index)
                        cp = self._get_closest_line_collision(probe_line)
                        final_points.append(cp)
        elif valid_count == 3:
            for index in range(4):
                if index in valid_indices:
                    final_points.append(Point(*coords[index]))
                else:
                    # add two points
                    for other_index in (index - 1, index + 1):
                        probe_line = get_line(other_index, index)
                        cp = self._get_closest_line_collision(probe_line)
                        final_points.append(cp)
        else:
            final_points.extend([Point(*coord) for coord in coords])
        valid_points = [p for p in final_points if not p is None]
        if len(valid_points) < 3:
            result = []
        elif len(valid_points) == 3:
            result = [Triangle(*valid_points)]
        else:
            # create a simple star-like fan of triangles - not perfect, but ok
            result = []
            start = valid_points.pop(0)
            while len(valid_points) > 1:
                p2, p3 = valid_points[0:2]
                result.append(Triangle(start, p2, p3))
                valid_points.pop(0)
        return result

    def _get_grid_matrix(self, stepping):
        x_dim = self.outer.maxx - self.outer.minx
        y_dim = self.outer.maxy - self.outer.miny
        x_points_num = int(max(4, math.ceil(x_dim / stepping)))
        y_points_num = int(max(4, math.ceil(y_dim / stepping)))
        x_step = x_dim / (x_points_num - 1)
        y_step = y_dim / (y_points_num - 1)
        grid = []
        for x_index in range(x_points_num):
            line = []
            for y_index in range(y_points_num):
                x_value = self.outer.minx + x_index * x_step
                y_value = self.outer.miny + y_index * y_step
                line.append((x_value, y_value))
            grid.append(line)
        return grid

    def calculate_point_height(self, x, y, func):
        point = Point(x, y, self.outer.minz)
        if not self.outer.is_point_inside(point):
            return None
        for poly in self.inner:
            if poly.is_point_inside(point):
                return None
        point = Point(x, y, self.outer.minz)
        line_distances = []
        for line in self.lines:
            cross_product = line.dir.cross(point.sub(line.p1))
            if cross_product.z > 0:
                close_points = []
                close_point = line.closest_point(point)
                if not line.is_point_inside(close_point):
                    close_points.append(line.p1)
                    close_points.append(line.p2)
                else:
                    close_points.append(close_point)
                for p in close_points:
                    direction = point.sub(p)
                    dist = direction.norm
                    line_distances.append(dist)
            elif cross_product.z == 0:
                # the point is on the line
                line_distances.append(0.0)
                # no other line can get closer than this
                break
            else:
                # the point is in the left of this line
                pass
        line_distances.sort()
        return self.z_level + func(line_distances[0])


class TriangleOptimizer(object):

    def __init__(self, callback=None):
        self.groups = {}
        self.callback = callback

    def append(self, triangle):
        # use a simple tuple instead of an object as the dict's key
        normal_coords = triangle.normal.x, triangle.normal.y, triangle.normal.z
        if not normal_coords in self.groups:
            self.groups[normal_coords] = []
        self.groups[normal_coords].append(triangle)

    def optimize(self):
        for group in self.groups.values():
            finished_triangles = []
            rect_pool = []
            triangles = list(group)
            while triangles:
                if self.callback and self.callback():
                    return
                current = triangles.pop(0)
                for t in triangles:
                    combined = Rectangle.combine_triangles(current, t)
                    if combined:
                        triangles.remove(t)
                        rect_pool.append(combined)
                        break
                else:
                    finished_triangles.append(current)
            finished_rectangles = []
            while rect_pool:
                if self.callback and self.callback():
                    return
                current = rect_pool.pop(0)
                for r in rect_pool:
                    combined = Rectangle.combine_rectangles(current, r)
                    if combined:
                        rect_pool.remove(r)
                        rect_pool.append(combined)
                        break
                else:
                    finished_rectangles.append(current)
            while group:
                group.pop()
            for rect in finished_rectangles:
                group.extend(rect.get_triangles())
            group.extend(finished_triangles)

    def get_triangles(self):
        result = []
        for group in self.groups.values():
            result.extend(group)
        return result


class Rectangle(TransformableContainer):

    id = 0

    def __init__(self, p1, p2, p3, p4, normal=None):
        if normal:
            orders = ((p1, p2, p3, p4), (p1, p2, p4, p3), (p1, p3, p2, p4),
                    (p1, p3, p4, p2), (p1, p4, p2, p3), (p1, p4, p3, p2))
            for order in orders:
                if abs(order[0].sub(order[2]).norm - order[1].sub(order[3]).norm) < epsilon:
                    t1 = Triangle(order[0], order[1], order[2])
                    t2 = Triangle(order[2], order[3], order[0])
                    if t1.normal == t2.normal == normal:
                        self.p1, self.p2, self.p3, self.p4 = order
                        break
            else:
                raise ValueError("Invalid vertices for given normal: " + \
                        "%s, %s, %s, %s, %s" % (p1, p2, p3, p4, normal))
        else:
            self.p1 = p1
            self.p2 = p2
            self.p3 = p3
            self.p4 = p4
        self.id = Rectangle.id
        Rectangle.id += 1
        self.reset_cache()

    def reset_cache(self):
        self.maxx = max([p.x for p in self.get_points()])
        self.minx = max([p.x for p in self.get_points()])
        self.maxy = max([p.y for p in self.get_points()])
        self.miny = max([p.y for p in self.get_points()])
        self.maxz = max([p.z for p in self.get_points()])
        self.minz = max([p.z for p in self.get_points()])
        self.normal = Triangle(self.p1, self.p2, self.p3).normal.normalized()

    def get_points(self):
        return (self.p1, self.p2, self.p3, self.p4)

    def next(self):
        yield self.p1
        yield self.p2
        yield self.p3
        yield self.p4

    def __repr__(self):
        return "Rectangle%d<%s,%s,%s,%s>" % (self.id, self.p1, self.p2,
                self.p3, self.p4)

    def get_triangles(self):
        return (Triangle(self.p1, self.p2, self.p3),
                Triangle(self.p3, self.p4, self.p1))

    @staticmethod
    def combine_triangles(t1, t2):
        unique_vertices = []
        shared_vertices = []
        for point in t1.get_points():
            for point2 in t2.get_points():
                if point == point2:
                    shared_vertices.append(point)
                    break
            else:
                unique_vertices.append(point)
        if len(shared_vertices) != 2:
            return None
        for point in t2.get_points():
            for point2 in shared_vertices:
                if point == point2:
                    break
            else:
                unique_vertices.append(point)
        if len(unique_vertices) != 2:
            log.error("Invalid number of vertices: %s" % unique_vertices)
            return None
        if abs(unique_vertices[0].sub(unique_vertices[1]).norm - \
                shared_vertices[0].sub(shared_vertices[1]).norm) < epsilon:
            try:
                return Rectangle(unique_vertices[0], unique_vertices[1],
                        shared_vertices[0], shared_vertices[1],
                        normal=t1.normal)
            except ValueError:
                log.warn("Triangles not combined: %s, %s" % (unique_vertices,
                        shared_vertices))
                return None
        else:
            return None

    @staticmethod
    def combine_rectangles(r1, r2):
        shared_vertices = []
        shared_vertices2 = []
        for point in r1.get_points():
            for point2 in r2.get_points():
                if point == point2:
                    shared_vertices.append(point)
                    shared_vertices2.append(point2)
                    break
        if len(shared_vertices) != 2:
            return None
        # check if the two points form an edge (and not a diagonal line)
        corners = []
        for rectangle, vertices in ((r1, shared_vertices),
                (r2, shared_vertices2)):
            # turn the tuple into a list (".index" was introduced in Python 2.6)
            i1 = list(rectangle.get_points()).index(vertices[0])
            i2 = list(rectangle.get_points()).index(vertices[1])
            if i1 + i2 % 2 == 0:
                # shared vertices are at opposite corners
                return None
            # collect all non-shared vertices
            corners.extend([p for p in rectangle.get_points()
                    if not p in vertices])
        if len(corners) != 4:
            log.error("Unexpected corner count: %s / %s / %s" % (r1, r2, corners))
            return None
        try:
            return Rectangle(corners[0], corners[1], corners[2], corners[3],
                    normal=r1.normal)
        except ValueError:
            log.error("No valid rectangle found: %s" % corners)
            return None

