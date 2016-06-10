#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id: setup.py 1093 2011-06-13 17:00:28Z sumpfralle $

Copyright 2010 Lars Kruse <devel@sumpfralle.de>
Copyright 2010 Arthur Magill

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

from distutils.core import setup
import distutils.sysconfig
import glob
import os.path
import sys
import shutil
# add the local pycam source directory to the PYTHONPATH
BASE_DIR = os.path.realpath(os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "src"))
from pycam import VERSION

WINDOWS_START_SCRIPT = "pycam-loader.py"
DEFAULT_START_SCRIPT = "pycam"

# we don't want to include the windows postinstall script in other installers
is_windows_installer = "bdist_wininst" in sys.argv or "bdist_msi" in sys.argv

if is_windows_installer:
    shutil.copy2(os.path.join(BASE_DIR, DEFAULT_START_SCRIPT),
            os.path.join(BASE_DIR, WINDOWS_START_SCRIPT))
    PLATFORM_SCRIPTS = [WINDOWS_START_SCRIPT, "pycam_win32_postinstall.py"]
else:
    PLATFORM_SCRIPTS = [DEFAULT_START_SCRIPT]


setup(
    name="pycam",
    version=VERSION,
    license="GPL v3",
    description="Open Source CAM - Toolpath Generation for 3-Axis CNC machining",
    author="Lars Kruse",
    author_email="devel@sumpfralle.de",
    provides=["pycam"],
    requires=["ode", "gtk", "gtk.gtkgl", "OpenGL"],
    url="http://sourceforge.net/projects/pycam",
    download_url="http://sourceforge.net/projects/pycam/files",
    keywords=["3-axis", "cnc", "cam", "toolpath", "machining", "g-code"],
    long_description="""IMPORTANT NOTE: Please read the list of requirements:
http://sourceforge.net/apps/mediawiki/pycam/index.php?title=Requirements
Basically you will need Python, GTK and OpenGL.

Windows: select Python 2.5 in the following dialog.
""",
    # full list of classifiers at:
    #   http://pypi.python.org/pypi?:action=list_classifiers
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Topic :: Scientific/Engineering",
        "Environment :: Win32 (MS Windows)",
        "Environment :: X11 Applications :: GTK",
        "Intended Audience :: Manufacturing",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX",
    ],
    package_dir={'': 'src'},
    packages=[
        "pycam",
        "pycam.Cutters",
        "pycam.Exporters",
        "pycam.Geometry",
        "pycam.Gui",
        "pycam.Importers",
        "pycam.PathGenerators",
        "pycam.PathProcessors",
        "pycam.Physics",
        "pycam.Simulation",
        "pycam.Toolpath",
        "pycam.Utils",
    ],
    scripts = PLATFORM_SCRIPTS,
    data_files=[("share/pycam/doc", [
            "COPYING.TXT",
            "INSTALL.TXT",
            "LICENSE.TXT",
            "README.TXT",
            "Changelog",
            "release_info.txt"]),
        ("share/pycam/ui", glob.glob(os.path.join("share", "ui", "*"))),
        ("share/pycam/fonts", glob.glob(os.path.join("share", "fonts", "*"))),
        ("share/pycam", [os.path.join("share", "pycam.ico"), os.path.join("share", "misc", "DXF.gpl")]),
        ("share/pycam/samples", glob.glob(os.path.join("samples", "*"))),
    ],
)

if is_windows_installer:
    os.remove(os.path.join(BASE_DIR, WINDOWS_START_SCRIPT))

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
