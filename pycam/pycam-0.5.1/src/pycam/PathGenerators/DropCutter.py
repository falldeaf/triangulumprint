# -*- coding: utf-8 -*-
"""
$Id: DropCutter.py 998 2011-03-08 11:34:44Z sumpfralle $

Copyright 2010-2011 Lars Kruse <devel@sumpfralle.de>
Copyright 2008-2009 Lode Leroy

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

from pycam.PathGenerators import get_max_height_dynamic
from pycam.Utils import ProgressCounter
from pycam.Utils.threading import run_in_parallel
import pycam.Utils.log

log = pycam.Utils.log.get_logger()


# We need to use a global function here - otherwise it does not work with
# the multiprocessing Pool.
def _process_one_grid_line((positions, minz, maxz, model, cutter, physics)):
    """ This function assumes, that the positions are next to each other.
    Otherwise the dynamic over-sampling (in get_max_height_dynamic) is
    pointless.
    """
    return get_max_height_dynamic(model, cutter, positions, minz, maxz, physics)


class Dimension:
    def __init__(self, start, end):
        self.start = float(start)
        self.end = float(end)
        self.min = float(min(start, end))
        self.max = float(max(start, end))
        self.downward = start > end
        self.value = 0.0

    def check_bounds(self, value=None, tolerance=None):
        if value is None:
            value = self.value
        if tolerance is None:
            return (value >= self.min) and (value <= self.max)
        else:
            return (value > self.min - tolerance) \
                    and (value < self.max + tolerance)

    def shift(self, distance):
        if self.downward:
            self.value -= distance
        else:
            self.value += distance

    def set(self, value):
        self.value = float(value)

    def get(self):
        return self.value


class DropCutter:

    def __init__(self, cutter, models, path_processor, physics=None):
        self.cutter = cutter
        # combine the models (if there is more than one)
        self.model = models[0]
        for model in models[1:]:
            self.model += model
        self.pa = path_processor
        self.physics = physics
        # remember if we already reported an invalid boundary

    def GenerateToolPath(self, motion_grid, minz, maxz, draw_callback=None):
        quit_requested = False

        # Transfer the grid (a generator) into a list of lists and count the
        # items.
        lines = []
        # usually there is only one layer - but an xy-grid consists of two
        for layer in motion_grid:
            for line in layer:
                lines.append(line)

        num_of_lines = len(lines)
        progress_counter = ProgressCounter(len(lines), draw_callback)
        current_line = 0

        self.pa.new_direction(0)

        args = []
        for one_grid_line in lines:
            # simplify the data (useful for remote processing)
            xy_coords = [(pos.x, pos.y) for pos in one_grid_line]
            args.append((xy_coords, minz, maxz, self.model, self.cutter,
                    self.physics))
        for points in run_in_parallel(_process_one_grid_line, args,
                callback=progress_counter.update):
            self.pa.new_scanline()
            if draw_callback and draw_callback(text="DropCutter: processing " \
                        + "line %d/%d" % (current_line + 1, num_of_lines)):
                # cancel requested
                quit_requested = True
                break
            for point in points:
                if point is None:
                    # exceeded maxz - the cutter has to skip this point
                    self.pa.end_scanline()
                    self.pa.new_scanline()
                    continue
                self.pa.append(point)
                # "draw_callback" returns true, if the user requested to quit
                # via the GUI.
                # The progress counter may return True, if cancel was requested.
                if draw_callback and draw_callback(tool_position=point,
                        toolpath=self.pa.paths):
                    quit_requested = True
                    break
            progress_counter.increment()
            self.pa.end_scanline()
            # update progress
            current_line += 1
            if quit_requested:
                break
        self.pa.end_direction()
        self.pa.finish()
        return self.pa.paths

