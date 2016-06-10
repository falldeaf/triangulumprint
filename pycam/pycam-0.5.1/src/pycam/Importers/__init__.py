# -*- coding: utf-8 -*-
"""
$Id: __init__.py 1026 2011-03-24 10:13:58Z sumpfralle $

Copyright 2008 Lode Leroy
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

__all__ = ["STLImporter", "DXFImporter", "SVGImporter", "TestModel"]

import pycam.Utils.log
import pycam.Utils
import pycam.Importers.DXFImporter
import pycam.Importers.STLImporter
import pycam.Importers.SVGImporter
import pycam.Importers.PSImporter

import os

log = pycam.Utils.log.get_logger()


def detect_file_type(filename, quiet=False):
    # also accept URI input
    uri = pycam.Utils.URIHandler(filename)
    filename = uri.get_path()
    failure = (None, None)
    # check all listed importers
    # TODO: this should be done by evaluating the header of the file
    if filename.lower().endswith(".stl"):
        return ("stl", pycam.Importers.STLImporter.ImportModel)
    elif filename.lower().endswith(".dxf"):
        return ("dxf", pycam.Importers.DXFImporter.import_model)
    elif filename.lower().endswith(".svg"):
        return ("svg", pycam.Importers.SVGImporter.import_model)
    elif filename.lower().endswith(".eps") \
            or filename.lower().endswith(".ps"):
        return ("ps", pycam.Importers.PSImporter.import_model)
    else:
        if not quiet:
            log.error(("Importers: Failed to detect the model type of '%s'. " \
                    + "Is the file extension (stl/dxf/svg/eps/ps) correct?") \
                    % filename)
        return failure

