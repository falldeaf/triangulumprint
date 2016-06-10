#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id: Project.py 1092 2011-06-13 14:40:56Z sumpfralle $

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


from pycam.Exporters.GCodeExporter import PATH_MODES, GCodeGenerator
import pycam.Exporters.EMCToolExporter
import pycam.Gui.Settings
import pycam.Cutters
import pycam.Toolpath.Generator
import pycam.Toolpath
import pycam.Importers.CXFImporter
import pycam.Importers.TestModel
import pycam.Importers
from pycam.Geometry.Point import Point, Vector
from pycam.Geometry.Plane import Plane
import pycam.Geometry.Path
import pycam.Utils.log
import pycam.Utils
from pycam.Geometry.utils import sqrt
from pycam.Gui.OpenGLTools import ModelViewWindowGL
from pycam.Geometry.Letters import TEXT_ALIGN_LEFT, TEXT_ALIGN_CENTER, \
        TEXT_ALIGN_RIGHT
import pycam.Geometry.Model
from pycam.Toolpath import Bounds
import pycam.Utils.FontCache
from pycam import VERSION
import pycam.Physics.ode_physics
# this requires ODE - we import it later, if necessary
#import pycam.Simulation.ODEBlocks
import gtk
import gobject
import webbrowser
import ConfigParser
import string
import StringIO
import pickle
import time
import logging
import datetime
import traceback
import random
import math
import re
import os
import sys

DATA_DIR_ENVIRON_KEY = "PYCAM_DATA_DIR"
FONT_DIR_ENVIRON_KEY = "PYCAM_FONT_DIR"
DATA_BASE_DIRS = [os.path.realpath(os.path.join(os.path.dirname(__file__),
            os.pardir, os.pardir, os.pardir, "share")),
        os.path.join(sys.prefix, "local", "share", "pycam"),
        os.path.join(sys.prefix, "share", "pycam")]
UI_SUBDIR = "ui"
FONTS_SUBDIR = "fonts"
# necessary for "pyinstaller"
if "_MEIPASS2" in os.environ:
    DATA_BASE_DIRS.insert(0, os.path.join(os.path.normpath(os.environ["_MEIPASS2"]), "share"))
# respect an override via an environment setting
if DATA_DIR_ENVIRON_KEY in os.environ:
    DATA_BASE_DIRS.insert(0, os.path.normpath(os.environ[DATA_DIR_ENVIRON_KEY]))
if FONT_DIR_ENVIRON_KEY in os.environ:
    FONT_DIR_OVERRIDE = os.path.normpath(os.environ[FONT_DIR_ENVIRON_KEY])
else:
    FONT_DIR_OVERRIDE = None
FONT_DIR_FALLBACKS = ["/usr/share/librecad/fonts", "/usr/share/qcad/fonts"]

GTKBUILD_FILE = os.path.join(UI_SUBDIR, "pycam-project.ui")
GTKMENU_FILE = os.path.join(UI_SUBDIR, "menubar.xml")
GTKRC_FILE_WINDOWS = os.path.join(UI_SUBDIR, "gtkrc_windows")

WINDOW_ICON_FILENAMES = ["logo_%dpx.png" % pixels for pixels in (16, 32, 48, 64, 128)]

HELP_WIKI_URL = "http://sourceforge.net/apps/mediawiki/pycam/index.php?title=%s"

FILTER_GCODE = (("GCode files", ("*.ngc", "*.nc", "*.gc", "*.gcode")),)
FILTER_MODEL = (("All supported model filetypes",
                ("*.stl", "*.dxf", "*.svg", "*.eps", "*.ps")),
        ("STL models", "*.stl"), ("DXF contours", "*.dxf"),
        ("SVG contours", "*.svg"), ("PS contours", ("*.eps", "*.ps")))
FILTER_CONFIG = (("Config files", "*.conf"),)
FILTER_EMC_TOOL = (("EMC tool files", "*.tbl"),)

CLIPBOARD_TARGETS = {
        "dxf": ("image/vnd.dxf", ),
        "ps": ("application/postscript", ),
        "stl": ("application/sla", ),
        "svg": ("image/x-inkscape-svg", "image/svg+xml"),
        "filename_drag": ("text/uri-list", "text-plain"),
}

EXTRUSION_TYPES = (("radius_up", "Radius (bulge)", "ExtrusionRadiusUpIcon"),
        ("radius_down", "Radius (valley)", "ExtrusionRadiusDownIcon"),
        ("skewed", "Chamfer", "ExtrusionChamferIcon"),
        ("sine", "Sine", "ExtrusionSineIcon"),
        ("sigmoid", "Sigmoid", "ExtrusionSigmoidIcon"),
)

PREFERENCES_DEFAULTS = {
        "enable_ode": False,
        "boundary_mode": -1,
        "unit": "mm",
        "default_task_settings_file": "",
        "show_model": True,
        "show_support_grid": True,
        "show_axes": True,
        "show_dimensions": True,
        "show_bounding_box": True,
        "show_toolpath": True,
        "show_drill": False,
        "show_directions": False,
        "color_background": (0.0, 0.0, 0.0, 1.0),
        "color_model": (0.5, 0.5, 1.0, 1.0),
        "color_support_grid": (0.8, 0.8, 0.3, 1.0),
        "color_bounding_box": (0.3, 0.3, 0.3, 1.0),
        "color_cutter": (1.0, 0.2, 0.2, 1.0),
        "color_toolpath_cut": (1.0, 0.5, 0.5, 1.0),
        "color_toolpath_return": (0.9, 1.0, 0.1, 0.4),
        "color_material": (1.0, 0.5, 0.0, 1.0),
        "view_light": True,
        "view_shadow": True,
        "view_polygon": True,
        "view_perspective": True,
        "simulation_details_level": 3,
        "drill_progress_max_fps": 2,
        "gcode_safety_height": 25.0,
        "gcode_minimum_step_x": 0.0001,
        "gcode_minimum_step_y": 0.0001,
        "gcode_minimum_step_z": 0.0001,
        "gcode_path_mode": 0,
        "gcode_motion_tolerance": 0,
        "gcode_naive_tolerance": 0,
        "gcode_start_stop_spindle": True,
        "gcode_filename_extension": "",
        "gcode_spindle_delay": 3,
        "external_program_inkscape": "",
        "external_program_pstoedit": "",
        "server_auth_key": "",
        "server_port_local": pycam.Utils.threading.DEFAULT_PORT,
        "server_port_remote": pycam.Utils.threading.DEFAULT_PORT,
        "server_hostname": "",
        "touch_off_on_startup": False,
        "touch_off_on_tool_change": False,
        "touch_off_position_type": "absolute",
        "touch_off_position_x": 0.0,
        "touch_off_position_y": 0.0,
        "touch_off_position_z": 0.0,
        "touch_off_rapid_move": 0.0,
        "touch_off_slow_move": 1.0,
        "touch_off_slow_feedrate": 20,
        "touch_off_height": 0.0,
        "touch_off_pause_execution": False,
}
""" the listed items will be loaded/saved via the preferences file in the
user's home directory on startup/shutdown"""

GRID_TYPES = {"none": 0, "grid": 1, "automatic_edge": 2, "automatic_corner": 3}
POCKETING_TYPES = ["none", "holes", "enclosed"]
MAX_UNDO_STATES = 10

# floating point color values are only available since gtk 2.16
GTK_COLOR_MAX = 65535.0

log = pycam.Utils.log.get_logger()

def get_data_file_location(filename, silent=False):
    for base_dir in DATA_BASE_DIRS:
        test_path = os.path.join(base_dir, filename)
        if os.path.exists(test_path):
            return test_path
    else:
        if not silent:
            lines = []
            lines.append("Failed to locate a resource file (%s) in %s!" \
                    % (filename, DATA_BASE_DIRS))
            lines.append("You can extend the search path by setting the " \
                    + "environment variable '%s'." % str(DATA_DIR_ENVIRON_KEY))
            log.error(os.linesep.join(lines))
        return None

def report_exception():
    log.error("An unexpected exception occoured: please send the " \
            + "text below to the developers of PyCAM. Thanks a lot!" \
            + os.linesep + traceback.format_exc())

def get_filters_from_list(filter_list):
    result = []
    for one_filter in filter_list:
        current_filter = gtk.FileFilter()
        current_filter.set_name(one_filter[0])
        file_extensions = one_filter[1]
        if not isinstance(file_extensions, (list, tuple)):
            file_extensions = [file_extensions]
        for ext in file_extensions:
            current_filter.add_pattern(ext)
        result.append(current_filter)
    return result

def get_icons_pixbuffers():
    result = []
    for icon_filename in WINDOW_ICON_FILENAMES:
        icon_subdir_filename = os.path.join(UI_SUBDIR, icon_filename)
        abs_filename = get_data_file_location(icon_subdir_filename, silent=True)
        if abs_filename:
            try:
                result.append(gtk.gdk.pixbuf_new_from_file(abs_filename))
            except gobject.GError, err_msg:
                # ignore icons that are not found
                log.debug("Failed to process window icon (%s): %s" \
                        % (abs_filename, err_msg))
        else:
            log.debug("Failed to locate window icon: %s" % icon_filename)
    return result

def get_font_dir():
    if FONT_DIR_OVERRIDE:
        if os.path.isdir(FONT_DIR_OVERRIDE):
            return FONT_DIR_OVERRIDE
        else:
            log.warn(("You specified a font dir that does not exist (%s). " \
                    + "I will ignore it.") % FONT_DIR_OVERRIDE)
    font_dir = get_data_file_location(FONTS_SUBDIR, silent=True)
    if not font_dir is None:
        return font_dir
    else:
        log.warn(("Failed to locate the fonts directory '%s' below '%s'. " + \
                "Falling back to '%s'.") % \
                (FONTS_SUBDIR, DATA_BASE_DIRS, ", ".join(FONT_DIR_FALLBACKS)))
        for font_dir_fallback in FONT_DIR_FALLBACKS:
            if os.path.isdir(font_dir_fallback):
                return font_dir_fallback
        else:
            log.warn(("None of the fallback font directories (%s) exists. " + \
                    "No fonts will be available. Please install " + \
                    "'qcad-data' or 'librecad-data' if you need fonts." ) % \
                    ", ".join(FONT_DIR_FALLBACKS))
            return None


class ProjectGui:

    BOUNDARY_MODES = {
            "inside": -1,
            "along": 0,
            "around": 1}
    # mapping of boundary types and GUI control elements
    BOUNDARY_TYPES = {
            Bounds.TYPE_RELATIVE_MARGIN: "BoundsTypeRelativeMargin",
            Bounds.TYPE_FIXED_MARGIN: "BoundsTypeFixedMargin",
            Bounds.TYPE_CUSTOM: "BoundsTypeCustom"}

    META_DATA_PREFIX = "PYCAM-META-DATA:"

    def __init__(self, no_dialog=False):
        self.settings = pycam.Gui.Settings.Settings()
        self.gui_is_active = False
        self.view3d = None
        # during initialization any dialog (e.g. "Unit change") is not allowed
        # we set the final value later
        self.no_dialog = True
        self._batch_queue = []
        self._progress_running = False
        self._progress_cancel_requested = False
        self._last_gtk_events_time = None
        self._undo_states = []
        self._fonts_cache = pycam.Utils.FontCache.FontCache(get_font_dir(),
                callback=self.update_progress_bar)
        self.gui = gtk.Builder()
        gtk_build_file = get_data_file_location(GTKBUILD_FILE)
        if gtk_build_file is None:
            gtk.main_quit()
        self.gui.add_from_file(gtk_build_file)
        if pycam.Utils.get_platform() == pycam.Utils.PLATFORM_WINDOWS:
            gtkrc_file = get_data_file_location(GTKRC_FILE_WINDOWS)
            if gtkrc_file:
                print "GTKRC: %s" % str(gtkrc_file)
                gtk.rc_add_default_file(gtkrc_file)
                gtk.rc_reparse_all_for_settings(gtk.settings_get_default(), True)
        self.window = self.gui.get_object("ProjectWindow")
        # show stock items on buttons
        # increase the initial width of the window (due to hidden elements)
        self.window.set_default_size(400, -1)
        # initialize the RecentManager (TODO: check for Windows)
        if False and pycam.Utils.get_platform() == pycam.Utils.PLATFORM_WINDOWS:
            # The pyinstaller binary for Windows fails mysteriously when trying
            # to display the stock item.
            # Error message: Gtk:ERROR:gtkrecentmanager.c:1942:get_icon_fallback: assertion failed: (retval != NULL)
            self.recent_manager = None
        else:
            try:
                self.recent_manager = gtk.recent_manager_get_default()
            except AttributeError:
                # GTK 2.12.1 seems to have problems with "RecentManager" on
                # Windows. Sadly this is the version, that is shipped with the
                # "appunti" GTK packages for Windows (April 2010).
                # see http://www.daa.com.au/pipermail/pygtk/2009-May/017052.html
                self.recent_manager = None
        # file loading
        self.last_dirname = None
        self.last_task_settings_uri = None
        self.last_model_uri = None
        self.last_toolpath_file = None
        # define callbacks and accelerator keys for the menu actions
        for objname, callback, data, accel_key in (
                ("LoadTaskSettings", self.load_task_settings_file, None, "<Control>t"),
                ("SaveTaskSettings", self.save_task_settings_file, lambda: self.last_task_settings_uri, None),
                ("SaveAsTaskSettings", self.save_task_settings_file, None, None),
                ("OpenModel", self.load_model_file, None, "<Control>o"),
                ("SaveModel", self.save_model, lambda: self.last_model_uri, "<Control>s"),
                ("SaveAsModel", self.save_model, None, "<Control><Shift>s"),
                ("ExportGCodeAll", self.save_toolpath, False, "<Control><Shift>e"),
                ("ExportGCodeVisible", self.save_toolpath, True, None),
                ("ExportEMCToolDefinition", self.export_emc_tools, None, None),
                ("Quit", self.destroy, None, "<Control>q"),
                ("GeneralSettings", self.toggle_preferences_window, None, "<Control>p"),
                ("Toggle3DView", self.toggle_3d_view, None, "<Control><Shift>v"),
                ("ToggleLogWindow", self.toggle_log_window, None, "<Control>l"),
                ("ToggleProcessPoolWindow", self.toggle_process_pool_window, None, None),
                ("ShowFontDialog", self.toggle_font_dialog_window, None, "<Control><Shift>t"),
                ("UndoButton", self._restore_undo_state, None, "<Control>z"),
                ("CopyModelToClipboard", self.copy_model_to_clipboard, None, "<Control>c"),
                ("PasteModelFromClipboard", self.paste_model_from_clipboard, None, "<Control>v"),
                ("HelpUserManual", self.show_help, "User_Manual", "F1"),
                ("HelpIntroduction", self.show_help, "Introduction", None),
                ("HelpSupportedFormats", self.show_help, "SupportedFormats", None),
                ("HelpModelTransformations", self.show_help, "ModelTransformations", None),
                ("HelpToolTypes", self.show_help, "ToolTypes", None),
                ("HelpProcessSettings", self.show_help, "ProcessSettings", None),
                ("HelpBoundsSettings", self.show_help, "BoundsSettings", None),
                ("HelpTaskSetup", self.show_help, "TaskSetup", None),
                ("HelpGCodeExport", self.show_help, "GCodeExport", None),
                ("HelpTouchOff", self.show_help, "TouchOff", None),
                ("HelpSimulation", self.show_help, "Simulation", None),
                ("Help3DView", self.show_help, "3D_View", None),
                ("HelpServerMode", self.show_help, "ServerMode", None),
                ("HelpCommandLine", self.show_help, "CommandlineExamples", None),
                ("HelpHotkeys", self.show_help, "KeyboardShortcuts", None),
                ("ProjectWebsite", self.show_help, "http://pycam.sourceforge.net", None),
                ("DevelopmentBlog", self.show_help, "http://fab.senselab.org/pycam", None),
                ("Forum", self.show_help, "http://sourceforge.net/projects/pycam/forums", None),
                ("BugTracker", self.show_help, "http://sourceforge.net/tracker/?group_id=237831&atid=1104176", None),
                ("FeatureRequest", self.show_help, "http://sourceforge.net/tracker/?group_id=237831&atid=1104179", None)):
            item = self.gui.get_object(objname)
            if objname in ("Toggle3DView", "ToggleLogWindow",
                    "ToggleProcessPoolWindow"):
                action = "toggled"
            else:
                action = "activate"
            if data is None:
                item.connect(action, callback)
            else:
                item.connect(action, callback, data)
            if accel_key:
                key, mod = gtk.accelerator_parse(accel_key)
                accel_path = "<pycam>/%s" % objname
                item.set_accel_path(accel_path)
                gtk.accel_map_change_entry(accel_path, key, mod, True)
        # LinkButton does not work on Windows: https://bugzilla.gnome.org/show_bug.cgi?id=617874
        if pycam.Utils.get_platform() == pycam.Utils.PLATFORM_WINDOWS:
            def open_url(widget, data=None):
                webbrowser.open(widget.get_uri())
            gtk.link_button_set_uri_hook(open_url)
        # no undo is allowed at the beginning
        self.gui.get_object("UndoButton").set_sensitive(False)
        # configure drag-n-drop for config files and models
        self.configure_drag_and_drop(self.window)
        self.clipboard = gtk.clipboard_get()
        self.clipboard.connect("owner-change", self.update_clipboard_state)
        # other events
        self.window.connect("destroy", self.destroy)
        # the settings window
        self.gui.get_object("CloseSettingsWindow").connect("clicked", self.toggle_preferences_window, False)
        self.gui.get_object("ResetPreferencesButton").connect("clicked", self.reset_preferences)
        self.preferences_window = self.gui.get_object("GeneralSettingsWindow")
        self.preferences_window.connect("delete-event", self.toggle_preferences_window, False)
        self._preferences_window_position = None
        self._preferences_window_visible = False
        self._log_window_position = None
        # "about" window
        self.about_window = self.gui.get_object("AboutWindow")
        self.about_window.set_version(VERSION)
        self.gui.get_object("About").connect("activate", self.toggle_about_window, True)
        # "unit change" window
        self.unit_change_window = self.gui.get_object("UnitChangeDialog")
        self.gui.get_object("UnitChangeApply").connect("clicked", self.change_unit_apply)
        self.unit_change_window.connect("delete_event", self.change_unit_apply, False)
        # we assume, that the last child of the window is the "close" button
        # TODO: fix this ugly hack!
        self.gui.get_object("AboutWindowButtons").get_children()[-1].connect("clicked", self.toggle_about_window, False)
        self.about_window.connect("delete-event", self.toggle_about_window, False)
        # "log" window
        self.log_window = self.gui.get_object("LogWindow")
        self.log_window.set_default_size(500, 400)
        self.log_window.connect("delete-event", self.toggle_log_window, False)
        self.log_window.connect("destroy", self.toggle_log_window, False)
        self.gui.get_object("LogWindowClose").connect("clicked", self.toggle_log_window, False)
        self.gui.get_object("LogWindowClear").connect("clicked", self.clear_log_window)
        self.gui.get_object("LogWindowCopyToClipboard").connect("clicked",
                self.copy_log_to_clipboard)
        self.log_model = self.gui.get_object("LogWindowList")
        # "process pool" window
        self.process_pool_window = self.gui.get_object("ProcessPoolWindow")
        self.process_pool_window.set_default_size(500, 400)
        self.process_pool_window.connect("delete-event", self.toggle_process_pool_window, False)
        self.process_pool_window.connect("destroy", self.toggle_process_pool_window, False)
        self.gui.get_object("ProcessPoolWindowClose").connect("clicked", self.toggle_process_pool_window, False)
        self.gui.get_object("ProcessPoolRefreshInterval").set_value(3)
        self.process_pool_model = self.gui.get_object("ProcessPoolStatisticsModel")
        # extrusion dialog
        self._extrusion_dialog_position = None
        self._extrusion_dialog_visible = False
        self.extrusion_dialog_window = self.gui.get_object("ExtrusionDialog")
        self.extrusion_dialog_window.connect("delete-event",
                self.toggle_extrusion_dialog, False)
        self.gui.get_object("ExtrusionCancel").connect("clicked",
                self.toggle_extrusion_dialog, False)
        self.gui.get_object("ExtrusionSubmit").connect("clicked",
                self.extrude_model)
        self.gui.get_object("ExtrusionHeight").set_value(1)
        self.gui.get_object("ExtrusionWidth").set_value(1)
        self.gui.get_object("ExtrusionGrid").set_value(0.5)
        extrusion_model = self.gui.get_object("ExtrusionTypeModel")
        for row in EXTRUSION_TYPES:
            extrusion_model.append((row[0], row[1],
                    self.gui.get_object(row[2]).get_pixbuf()))
        self.gui.get_object("ExtrusionTypeSelector").set_active(0)
        # "font dialog" window
        self.font_dialog_window = self.gui.get_object("FontDialog")
        self.font_dialog_window.connect("delete-event",
                self.toggle_font_dialog_window, False)
        self.font_dialog_window.connect("destroy",
                self.toggle_font_dialog_window, False)
        self.gui.get_object("FontDialogCancel").connect("clicked",
                self.toggle_font_dialog_window, False)
        self.gui.get_object("FontDialogApply").connect("clicked",
                self.import_from_font_dialog)
        self.gui.get_object("FontDialogSave").connect("clicked",
                self.export_from_font_dialog)
        self.gui.get_object("FontDialogCopy").connect("clicked",
                self.copy_font_dialog_to_clipboard)
        self.gui.get_object("FontDialogInputBuffer").connect("changed",
                self.update_font_dialog_preview)
        self.gui.get_object("FontDialogPreview").connect("configure_event",
                self.update_font_dialog_preview)
        self.gui.get_object("FontDialogPreview").connect("expose_event",
                self.update_font_dialog_preview)
        for objname in ("FontSideSkewValue", "FontCharacterSpacingValue",
                "FontLineSpacingValue"):
            obj = self.gui.get_object(objname)
            # set default value before connecting the change-handler
            if objname != "FontSideSkewValue":
                obj.set_value(1.0)
            obj.connect("value-changed",
                    self.update_font_dialog_preview)
        for objname in ("FontTextAlignLeft", "FontTextAlignCenter",
                "FontTextAlignRight"):
            self.gui.get_object(objname).connect("toggled",
                    self.update_font_dialog_preview)
        self._font_dialog_window_visible = False
        self._font_dialog_window_position = None
        # set defaults
        # fallback - in case of a failure when opening a model file
        self.model = pycam.Importers.TestModel.get_test_model()
        self.toolpath = pycam.Toolpath.ToolpathList()
        self.cutter = None
        self.tool_list = []
        self.process_list = []
        self.bounds_list = []
        self.task_list = []
        self.grid_adjustments_x = []
        self.grid_adjustments_y = []
        self.font_selector = None
        self._last_unit = None
        self._toolpath_for_grid_data = {}
        # add some dummies - to be implemented later ...
        self.settings.add_item("model", lambda: self.model)
        self.settings.add_item("toolpath", lambda: self.toolpath)
        self.settings.add_item("cutter", lambda: self.cutter)
        # unit control (mm/inch)
        unit_field = self.gui.get_object("unit_control")
        unit_field.connect("changed", self.change_unit_init)
        def set_unit(text):
            unit_field.set_active(0 if text == "mm" else 1)
            self._last_unit = text
        self.settings.add_item("unit", unit_field.get_active_text, set_unit)
        self.gui.get_object("UnitChangeSelectAll").connect("clicked",
                self.change_unit_set_selection, True)
        self.gui.get_object("UnitChangeSelectNone").connect("clicked",
                self.change_unit_set_selection, False)
        # autoload task settings file on startup
        autoload_enable = self.gui.get_object("AutoLoadTaskFile")
        autoload_box = self.gui.get_object("StartupTaskFileBox")
        autoload_source = self.gui.get_object("StartupTaskFile")
        for one_filter in get_filters_from_list(FILTER_CONFIG):
            autoload_source.add_filter(one_filter)
            autoload_source.set_filter(one_filter)
        def get_autoload_task_file(autoload_source=autoload_source):
            if autoload_enable.get_active():
                return autoload_source.get_filename()
            else:
                return ""
        def set_autoload_task_file(filename):
            if filename:
                autoload_enable.set_active(True)
                autoload_box.show()
                autoload_source.set_filename(filename)
            else:
                autoload_enable.set_active(False)
                autoload_box.hide()
                autoload_source.unselect_all()
        def autoload_enable_switched(widget, box):
            if not widget.get_active():
                set_autoload_task_file(None)
            else:
                autoload_box.show()
        autoload_enable.connect("toggled", autoload_enable_switched,
                autoload_box)
        self.settings.add_item("default_task_settings_file",
                get_autoload_task_file, set_autoload_task_file)
        # boundary mode (move inside/along/around the boundaries)
        boundary_mode_control = self.gui.get_object("BoundaryModeControl")
        def set_boundary_mode(value):
            # we assume, that the items in the list are (-1, 0, +1)
            boundary_mode_control.set_active(value + 1)
        def get_boundary_mode():
            return boundary_mode_control.get_active() - 1
        self.settings.add_item("boundary_mode", get_boundary_mode,
                set_boundary_mode)
        # Trigger a re-calculation of the bounds values after changing its type.
        for objname in ("BoundsTypeRelativeMargin", "BoundsTypeFixedMargin",
                "BoundsTypeCustom"):
            self.gui.get_object(objname).connect("toggled",
                    self.switch_bounds_type)
        # Calculate the "minx, ..." settings based on a (potentially) selected
        # bounds setting.
        def get_absolute_limit(key):
            if not self.model:
                # avoid problems if no model is loaded
                return 0
            bounds = self.settings.get("current_bounds")
            if bounds is None:
                return getattr(self.model, key)
            low, high = bounds.get_absolute_limits(reference=self.model.get_bounds())
            index = "xyz".index(key[-1])
            if key.startswith("min"):
                return low[index]
            else:
                return high[index]
        for key in ("minx", "maxx", "miny", "maxy", "minz", "maxz"):
            # create a new variable "key" to avoid re-using the same object "key"
            # (due to the lambda name scope)
            self.settings.add_item(key, lambda key=key: get_absolute_limit(key))
        # Transformations
        self.gui.get_object("Rotate").connect("clicked", self.transform_model)
        self.gui.get_object("Flip").connect("clicked", self.transform_model)
        self.gui.get_object("Swap").connect("clicked", self.transform_model)
        shift_model_button = self.gui.get_object("Shift Model")
        shift_model_button.connect("clicked", self.shift_model, True)
        # Make the "shift" button the default while one of the x/y/z values is
        # active.
        for objname in ("shift_x", "shift_y", "shift_z"):
            self.gui.get_object(objname).connect("focus-in-event",
                    lambda widget, data: shift_model_button.grab_default())
            self.gui.get_object(objname).connect("focus-out-event",
                    lambda widget, data: self.window.set_default(None))
        self.gui.get_object("Shift To Origin").connect("clicked",
                self.shift_model, False)
        # scale model
        scale_percent = self.gui.get_object("ScalePercent")
        scale_button = self.gui.get_object("ScaleModelButton")
        scale_percent.set_value(100)
        scale_percent.connect("focus-in-event",
                lambda widget, data: scale_button.grab_default())
        scale_percent.connect("focus-out-event",
                lambda widget, data: self.window.set_default(None))
        scale_button.connect("clicked", self.scale_model)
        # scale model to an axis dimension
        self.gui.get_object("ScaleDimensionAxis").connect("changed",
                self.update_model_dimensions)
        scale_dimension_button = self.gui.get_object("ScaleDimensionButton")
        scale_dimension_button.connect("clicked", self.scale_model_axis_fit)
        scale_dimension_control = self.gui.get_object("ScaleDimensionControl")
        scale_dimension_control.connect("focus-in-event",
                lambda widget, data: scale_dimension_button.grab_default())
        scale_dimension_control.connect("focus-out-event",
                lambda widget, data: self.window.set_default(None))
        self.gui.get_object("ToggleModelDirectionButton").connect("clicked",
                self.reverse_model_direction)
        self.gui.get_object("DirectionsGuessButton").connect("clicked",
                self.guess_model_directions)
        self.gui.get_object("ScaleInchMM").connect("clicked", self.scale_model,
                100 * 25.4, False)
        self.gui.get_object("ScaleMMInch").connect("clicked", self.scale_model,
                100 / 25.4, False)
        self.gui.get_object("Projection2D").connect("clicked",
                self.projection_2d)
        self.gui.get_object("ExtrudeButton").connect("clicked",
                self.toggle_extrusion_dialog, True)
        # support grid
        support_grid_type_control = self.gui.get_object(
                "SupportGridTypesControl")
        support_grid_type_control.connect("changed",
                self.update_support_controls)
        self.settings.add_item("support_grid_type",
                support_grid_type_control.get_active,
                support_grid_type_control.set_active)
        self.settings.set("support_grid_type", GRID_TYPES["none"])
        grid_distance_x = self.gui.get_object("SupportGridDistanceX")
        grid_distance_x.connect("value-changed", self.update_support_controls)
        self.settings.add_item("support_grid_distance_x",
                grid_distance_x.get_value, grid_distance_x.set_value)
        grid_distance_square = self.gui.get_object("SupportGridDistanceSquare")
        grid_distance_square.connect("clicked", self.update_support_controls)
        grid_distance_y = self.gui.get_object("SupportGridDistanceY")
        grid_distance_y.connect("value-changed", self.update_support_controls)
        def get_support_grid_distance_y():
            if grid_distance_square.get_active():
                return self.settings.get("support_grid_distance_x")
            else:
                return grid_distance_y.get_value()
        self.settings.add_item("support_grid_distance_y",
                get_support_grid_distance_y, grid_distance_y.set_value)
        grid_thickness = self.gui.get_object("SupportGridThickness")
        grid_thickness.connect("value-changed", self.update_support_model)
        self.settings.add_item("support_grid_thickness",
                grid_thickness.get_value, grid_thickness.set_value)
        grid_height = self.gui.get_object("SupportGridHeight")
        grid_height.connect("value-changed", self.update_support_model)
        self.settings.add_item("support_grid_height",
                grid_height.get_value, grid_height.set_value)
        grid_length = self.gui.get_object("SupportGridLength")
        grid_length.connect("value-changed", self.update_support_model)
        self.settings.add_item("support_grid_length",
                grid_length.get_value, grid_length.set_value)
        grid_offset_x = self.gui.get_object("SupportGridOffsetX")
        grid_offset_x.connect("value-changed", self.update_support_model)
        self.settings.add_item("support_grid_offset_x",
                grid_offset_x.get_value, grid_offset_x.set_value)
        grid_offset_y = self.gui.get_object("SupportGridOffsetY")
        grid_offset_y.connect("value-changed", self.update_support_model)
        self.settings.add_item("support_grid_offset_y",
                grid_offset_y.get_value, grid_offset_y.set_value)
        grid_average_distance = self.gui.get_object("GridAverageDistance")
        grid_average_distance.connect("value-changed",
                self.update_support_model)
        self.settings.add_item("support_grid_average_distance",
                grid_average_distance.get_value,
                grid_average_distance.set_value)
        grid_minimum_bridges = self.gui.get_object("GridMinBridgesPerPolygon")
        grid_minimum_bridges.connect("value-changed", self.update_support_model)
        self.settings.add_item("support_grid_minimum_bridges",
                grid_minimum_bridges.get_value, grid_minimum_bridges.set_value)
        # manual grid adjustments
        self.grid_adjustment_axis_x = self.gui.get_object("SupportGridPositionManualAxisX")
        self.grid_adjustment_axis_x.connect("toggled",
                self.switch_support_grid_manual_selector)
        self.gui.get_object("SupportGridPositionManualResetOne").connect(
                "clicked", self.reset_support_grid_manual, False)
        self.gui.get_object("SupportGridPositionManualResetAll").connect(
                "clicked", self.reset_support_grid_manual, True)
        self.grid_adjustment_model = self.gui.get_object(
                "SupportGridPositionManualList")
        self.grid_adjustment_selector = self.gui.get_object(
                "SupportGridPositionManualSelector")
        self.grid_adjustment_selector.connect("changed",
                self.switch_support_grid_manual_selector)
        self.grid_adjustment_value = self.gui.get_object(
                "SupportGridPositionManualAdjustment")
        self.grid_adjustment_value_control = self.gui.get_object(
                "SupportGridPositionManualShiftControl")
        self.grid_adjustment_value_control.connect("move-slider",
                self.update_support_grid_manual_adjust)
        self.grid_adjustment_value_control.connect("value-changed",
                self.update_support_grid_manual_adjust)
        self.gui.get_object("SupportGridPositionManualShiftControl2").connect(
                "value-changed", self.update_support_grid_manual_adjust)
        def get_set_grid_adjustment_value(value=None):
            if self.grid_adjustment_axis_x.get_active():
                adjustments = self.grid_adjustments_x
            else:
                adjustments = self.grid_adjustments_y
            index = self.grid_adjustment_selector.get_active()
            if value is None:
                if 0 <= index < len(adjustments):
                    return adjustments[index]
                else:
                    return 0
            else:
                while len(adjustments) <= index:
                    adjustments.append(0)
                adjustments[index] = value
        self.settings.add_item("support_grid_adjustment_value",
                get_set_grid_adjustment_value, get_set_grid_adjustment_value)
        # support grid defaults
        grid_distance_square.set_active(True)
        self.settings.set("support_grid_distance_x", 10.0)
        self.settings.set("support_grid_thickness", 0.5)
        self.settings.set("support_grid_height", 0.5)
        self.settings.set("support_grid_average_distance", 30)
        self.settings.set("support_grid_minimum_bridges", 2)
        self.settings.set("support_grid_length", 5)
        self.grid_adjustment_axis_x_last = True
        # toolpath grid pattern
        for objname in ("GridYCount", "GridXCount", "GridYDistance",
                "GridXDistance"):
            self.gui.get_object(objname).connect("value-changed",
                    self.update_toolpath_grid_window)
        # visual and general settings
        for name, objname in (("show_model", "ShowModelCheckBox"),
                ("show_support_grid", "ShowSupportGridCheckBox"),
                ("show_axes", "ShowAxesCheckBox"),
                ("show_dimensions", "ShowDimensionsCheckBox"),
                ("show_bounding_box", "ShowBoundingCheckBox"),
                ("show_toolpath", "ShowToolPathCheckBox"),
                ("show_drill", "ShowDrillCheckBox"),
                ("show_directions", "ShowDirectionsCheckBox")):
            obj = self.gui.get_object(objname)
            self.settings.add_item(name, obj.get_active, obj.set_active)
            # all of the objects above should trigger redraw
            obj.connect("toggled", self.update_view)
        self.show_progress_button = self.gui.get_object("ShowToolpathProgressButton")
        self.settings.add_item("show_drill_progress",
                self.show_progress_button.get_active,
                self.show_progress_button.set_active)
        for name, objname in (
                ("view_light", "OpenGLLight"),
                ("view_shadow", "OpenGLShadow"),
                ("view_polygon", "OpenGLPolygon"),
                ("view_perspective", "OpenGLPerspective")):
            obj = self.gui.get_object(objname)
            self.settings.add_item(name, obj.get_active, obj.set_active)
            # send "True" to trigger a re-setup of GL settings
            obj.connect("toggled", self.update_view, True)
        # color selectors
        def get_color_wrapper(obj):
            def gtk_color_to_float():
                gtk_color = obj.get_color()
                alpha = obj.get_alpha()
                return (gtk_color.red / GTK_COLOR_MAX,
                        gtk_color.green / GTK_COLOR_MAX,
                        gtk_color.blue / GTK_COLOR_MAX,
                        alpha / GTK_COLOR_MAX)
            return gtk_color_to_float
        def set_color_wrapper(obj):
            def set_gtk_color_by_float(components):
                # use alpha if it was given
                if len(components) == 3:
                    alpha = 1.0
                else:
                    alpha = components[3]
                red, green, blue = components[:3]
                obj.set_color(gtk.gdk.Color(int(red * GTK_COLOR_MAX),
                        int(green * GTK_COLOR_MAX), int(blue * GTK_COLOR_MAX)))
                obj.set_alpha(int(alpha * GTK_COLOR_MAX))
            return set_gtk_color_by_float
        for name, objname in (("color_background", "ColorBackground"),
                ("color_model", "ColorModel"),
                ("color_support_grid", "ColorSupportGrid"),
                ("color_bounding_box", "ColorBoundingBox"),
                ("color_cutter", "ColorDrill"),
                ("color_toolpath_cut", "ColorToolpathCut"),
                ("color_toolpath_return", "ColorToolpathReturn"),
                ("color_material", "ColorMaterial")):
            obj = self.gui.get_object(objname)
            self.settings.add_item(name, get_color_wrapper(obj), set_color_wrapper(obj))
            # repaint the 3d view after a color change
            obj.connect("color-set", self.update_view)
        # set the availability of ODE
        self.enable_ode_control = self.gui.get_object("SettingEnableODE")
        self.settings.add_item("enable_ode", self.enable_ode_control.get_active,
                self.enable_ode_control.set_active)
        skip_obj = self.gui.get_object("DrillProgressFrameSkipControl")
        self.settings.add_item("drill_progress_max_fps", skip_obj.get_value, skip_obj.set_value)
        sim_detail_obj = self.gui.get_object("SimulationDetailsValue")
        self.settings.add_item("simulation_details_level", sim_detail_obj.get_value, sim_detail_obj.set_value)
        # drill settings
        for objname in ("ToolDiameterControl", "TorusDiameterControl",
                "FeedrateControl", "SpindleSpeedControl"):
            self.gui.get_object(objname).connect("value-changed", self.handle_tool_settings_change)
        for name in ("SphericalCutter", "CylindricalCutter", "ToroidalCutter"):
            self.gui.get_object(name).connect("clicked", self.handle_tool_settings_change)
        self.gui.get_object("ToolName").connect("changed", self.handle_tool_settings_change)
        # connect the "consistency check" and the update-handler with all toolpath settings
        for objname in ("PushRemoveStrategy", "ContourPolygonStrategy",
                "ContourFollowStrategy", "SurfaceStrategy",
                "EngraveStrategy", "GridDirectionX", "GridDirectionY",
                "GridDirectionXY", "MillingStyleConventional",
                "MillingStyleClimb", "MillingStyleIgnore"):
            self.gui.get_object(objname).connect("toggled",
                    self.update_process_controls)
            self.gui.get_object(objname).connect("toggled",
                    self.handle_process_settings_change)
        for objname in ("OverlapPercentControl", "MaterialAllowanceControl",
                "MaxStepDownControl", "EngraveOffsetControl"):
            self.gui.get_object(objname).connect("value-changed",
                    self.handle_process_settings_change)
        self.gui.get_object("ProcessSettingName").connect("changed",
                self.handle_process_settings_change)
        pocketing_selector = self.gui.get_object("PocketingControl")
        self.settings.add_item("pocketing_type", pocketing_selector.get_active,
                pocketing_selector.set_active)
        pocketing_selector.connect("changed",
                self.handle_process_settings_change)
        # get/set functions for the current tool/process/bounds/task
        def get_current_item(table, item_list):
            index = self._treeview_get_active_index(table, item_list)
            if index is None:
                return None
            else:
                return item_list[index]
        def set_current_item(table, item_list, item):
            old_index = self._treeview_get_active_index(table, item_list)
            try:
                new_index = item_list.index(item)
            except ValueError:
                return
            if old_index == new_index:
                return
            else:
                self._treeview_set_active_index(table, new_index)
                # update all controls related the (possibly changed) item
                if item_list is self.tool_list:
                    self.append_to_queue(self.switch_tool_table_selection)
                elif item_list is self.process_list:
                    self.append_to_queue(self.switch_process_table_selection)
                elif item_list is self.task_list:
                    self.append_to_queue(self.switch_tasklist_table_selection)
        # the boundary manager
        self.settings.add_item("current_bounds",
                lambda: get_current_item(self.bounds_editor_table, self.bounds_list),
                lambda bounds: set_current_item(self.bounds_editor_table, self.bounds_list, bounds))
        self.bounds_editor_table = self.gui.get_object("BoundsEditorTable")
        self.bounds_editor_table.get_selection().connect("changed", self.switch_bounds_table_selection)
        self.gui.get_object("BoundsListMoveUp").connect("clicked", self.handle_bounds_table_event, "move_up")
        self.gui.get_object("BoundsListMoveDown").connect("clicked", self.handle_bounds_table_event, "move_down")
        self.gui.get_object("BoundsListAdd").connect("clicked", self.handle_bounds_table_event, "add")
        self.gui.get_object("BoundsListDelete").connect("clicked", self.handle_bounds_table_event, "delete")
        self.gui.get_object("BoundsMarginIncreaseX").connect("clicked", self.adjust_bounds, "x", "+")
        self.gui.get_object("BoundsMarginIncreaseY").connect("clicked", self.adjust_bounds, "y", "+")
        self.gui.get_object("BoundsMarginIncreaseZ").connect("clicked", self.adjust_bounds, "z", "+")
        self.gui.get_object("BoundsMarginDecreaseX").connect("clicked", self.adjust_bounds, "x", "-")
        self.gui.get_object("BoundsMarginDecreaseY").connect("clicked", self.adjust_bounds, "y", "-")
        self.gui.get_object("BoundsMarginDecreaseZ").connect("clicked", self.adjust_bounds, "z", "-")
        self.gui.get_object("BoundsMarginResetX").connect("clicked", self.adjust_bounds, "x", "0")
        self.gui.get_object("BoundsMarginResetY").connect("clicked", self.adjust_bounds, "y", "0")
        self.gui.get_object("BoundsMarginResetZ").connect("clicked", self.adjust_bounds, "z", "0")
        # connect change handler for boundary settings
        self.gui.get_object("BoundsName").connect("changed",
                self.handle_bounds_settings_change)
        for objname in ("boundary_x_low", "boundary_x_high", "boundary_y_low",
                "boundary_y_high", "boundary_z_low", "boundary_z_high"):
            self.gui.get_object(objname).connect("value-changed",
                    self.handle_bounds_settings_change)
        # the process manager
        self.settings.add_item("current_process",
                lambda: get_current_item(self.process_editor_table, self.process_list),
                lambda process: set_current_item(self.process_editor_table, self.process_list, process))
        self.process_editor_table = self.gui.get_object("ProcessEditorTable")
        self.process_editor_table.get_selection().connect("changed", self.switch_process_table_selection)
        self.gui.get_object("ProcessListMoveUp").connect("clicked", self.handle_process_table_event, "move_up")
        self.gui.get_object("ProcessListMoveDown").connect("clicked", self.handle_process_table_event, "move_down")
        self.gui.get_object("ProcessListAdd").connect("clicked", self.handle_process_table_event, "add")
        self.gui.get_object("ProcessListDelete").connect("clicked", self.handle_process_table_event, "delete")
        # progress bar and task pane
        self.progress_bar = self.gui.get_object("ProgressBar")
        self.progress_widget = self.gui.get_object("ProgressWidget")
        self.task_pane = self.gui.get_object("MainTabs")
        self.progress_cancel_button = self.gui.get_object("ProgressCancelButton")
        self.progress_cancel_button.connect("clicked", self.cancel_progress)
        # make sure that the toolpath settings are consistent
        self.toolpath_table = self.gui.get_object("ToolPathTable")
        self.toolpath_table.get_selection().connect("changed", self.toolpath_table_event, "update_buttons")
        self.gui.get_object("toolpath_visible").connect("toggled", self.toolpath_table_event, "toggle_visibility")
        self.gui.get_object("toolpath_up").connect("clicked", self.toolpath_table_event, "move_up")
        self.gui.get_object("toolpath_down").connect("clicked", self.toolpath_table_event, "move_down")
        self.gui.get_object("toolpath_delete").connect("clicked", self.toolpath_table_event, "delete")
        self.gui.get_object("toolpath_simulate").connect("clicked", self.toolpath_table_event, "simulate")
        self.gui.get_object("toolpath_crop").connect("clicked", self.toolpath_table_event, "crop")
        self.gui.get_object("ToolpathGrid").connect("clicked", self.toolpath_table_event, "grid")
        self.gui.get_object("ExitSimulationButton").connect("clicked", self.finish_toolpath_simulation)
        self.gui.get_object("ExportAllToolpathsButton").connect("clicked",
                self.save_toolpath, False)
        self.gui.get_object("ExportVisibleToolpathsButton").connect("clicked",
                self.save_toolpath, True)
        speed_factor_widget = self.gui.get_object("SimulationSpeedFactor")
        self.settings.add_item("simulation_speed_factor",
                lambda: pow(10, speed_factor_widget.get_value()),
                lambda value: speed_factor_widget.set_value(math.log10(max(0.001, value))))
        simulation_progress = self.gui.get_object("SimulationProgressTimelineValue")
        def update_simulation_progress(widget):
            if widget.get_value() == 100:
                # a negative value indicates, that the simulation is finished
                self.settings.set("simulation_current_distance", -1)
            else:
                complete = self.settings.get("simulation_complete_distance")
                partial = widget.get_value() / 100.0 * complete
                self.settings.set("simulation_current_distance", partial)
        simulation_progress.connect("value-changed", update_simulation_progress)
        # update the speed factor label
        speed_factor_widget.connect("value-changed",
                lambda widget: self.gui.get_object("SimulationSpeedFactorValueLabel").set_label(
                        "%.2f" % self.settings.get("simulation_speed_factor")))
        self.simulation_window = self.gui.get_object("SimulationDialog")
        self.simulation_window.connect("delete-event", self.finish_toolpath_simulation)
        # store the original content (for adding the number of current toolpaths in "update_toolpath_table")
        self._original_toolpath_tab_label = self.gui.get_object("ToolPathTabLabel").get_text()
        # tool editor
        self.settings.add_item("current_tool",
                lambda: get_current_item(self.tool_editor_table, self.tool_list),
                lambda tool: set_current_item(self.tool_editor_table, self.tool_list, tool))
        self.tool_editor_table = self.gui.get_object("ToolEditorTable")
        self.tool_editor_table.get_selection().connect("changed", self.switch_tool_table_selection)
        self.gui.get_object("ToolListMoveUp").connect("clicked", self._tool_editor_button_event, "move_up")
        self.gui.get_object("ToolListMoveDown").connect("clicked", self._tool_editor_button_event, "move_down")
        self.gui.get_object("ToolListAdd").connect("clicked", self._tool_editor_button_event, "add")
        self.gui.get_object("ToolListDelete").connect("clicked", self._tool_editor_button_event, "delete")
        # the task list manager
        self.settings.add_item("current_task",
                lambda: get_current_item(self.tasklist_table, self.task_list),
                lambda task: set_current_item(self.tasklist_table, self.task_list, task))
        self.tasklist_table = self.gui.get_object("TaskListTable")
        self.tasklist_table.get_selection().connect("changed", self.switch_tasklist_table_selection)
        self.gui.get_object("tasklist_enabled").connect("toggled", self._handle_tasklist_button_event, "toggle_enabled")
        self.gui.get_object("TaskListMoveUp").connect("clicked", self._handle_tasklist_button_event, "move_up")
        self.gui.get_object("TaskListMoveDown").connect("clicked", self._handle_tasklist_button_event, "move_down")
        self.gui.get_object("TaskListAdd").connect("clicked", self._handle_tasklist_button_event, "add")
        self.gui.get_object("TaskListDelete").connect("clicked", self._handle_tasklist_button_event, "delete")
        self.gui.get_object("GenerateToolPathButton").connect("clicked", self._handle_tasklist_button_event, "generate_one_toolpath")
        self.gui.get_object("GenerateAllToolPathsButton").connect("clicked", self._handle_tasklist_button_event, "generate_all_toolpaths")
        # We need to collect the signal handles to block them during
        # programmatical changes. The "self._task_property_signals" list allows
        # us to track all handlers that need to be blocked.
        self._task_property_signals = []
        for objname in ("TaskNameControl", "TaskToolSelector",
                "TaskProcessSelector", "TaskBoundsSelector"):
            obj = self.gui.get_object(objname)
            self._task_property_signals.append((obj,
                    obj.connect("changed", self._handle_task_setting_change)))
        # gcode settings
        gcode_minimum_step_x = self.gui.get_object("GCodeMinimumStep_x")
        self.settings.add_item("gcode_minimum_step_x",
                gcode_minimum_step_x.get_value, gcode_minimum_step_x.set_value)
        gcode_minimum_step_y = self.gui.get_object("GCodeMinimumStep_y")
        self.settings.add_item("gcode_minimum_step_y",
                gcode_minimum_step_y.get_value, gcode_minimum_step_y.set_value)
        gcode_minimum_step_z = self.gui.get_object("GCodeMinimumStep_z")
        self.settings.add_item("gcode_minimum_step_z",
                gcode_minimum_step_z.get_value, gcode_minimum_step_z.set_value)
        gcode_safety_height = self.gui.get_object("SafetyHeightControl")
        self.settings.add_item("gcode_safety_height",
                gcode_safety_height.get_value, gcode_safety_height.set_value)
        gcode_spindle_delay = self.gui.get_object("GCodeSpindleDelay")
        self.settings.add_item("gcode_spindle_delay",
                gcode_spindle_delay.get_value, gcode_spindle_delay.set_value)
        for objname, setting in (
                ("GCodeTouchOffOnStartup", "touch_off_on_startup"),
                ("GCodeTouchOffOnToolChange", "touch_off_on_tool_change")):
            obj = self.gui.get_object(objname)
            obj.connect("toggled", self.update_gcode_controls)
            self.settings.add_item(setting, obj.get_active, obj.set_active)
        touch_off_pos_selector = self.gui.get_object("TouchOffLocationSelector")
        def get_touch_off_position_type():
            index = touch_off_pos_selector.get_active()
            if index < 0:
                return PREFERENCES_DEFAULTS["touch_off_position_type"]
            else:
                return touch_off_pos_selector.get_model()[index][0]
        def set_touch_off_position_type(new_key):
            model = touch_off_pos_selector.get_model()
            for index, (key, value) in enumerate(model):
                if key == new_key:
                    touch_off_pos_selector.set_active(index)
                    break
            else:
                touch_off_pos_selector.set_active(-1)
        touch_off_pos_selector.connect("changed", self.update_gcode_controls)
        self.settings.add_item("touch_off_position_type",
                get_touch_off_position_type, set_touch_off_position_type)
        for axis in "XYZ":
            obj = self.gui.get_object("ToolChangePos%s" % axis.upper())
            self.settings.add_item("touch_off_position_%s" % axis.lower(),
                    obj.get_value, obj.set_value)
        for objname, setting in (
                ("ToolChangeRapidMoveDown", "touch_off_rapid_move"),
                ("ToolChangeSlowMoveDown", "touch_off_slow_move"),
                ("ToolChangeSlowMoveSpeed", "touch_off_slow_feedrate"),
                ("TouchOffHeight", "touch_off_height")):
            obj = self.gui.get_object(objname)
            self.settings.add_item(setting, obj.get_value, obj.set_value)
        touch_off_pause = self.gui.get_object("TouchOffPauseExecution")
        self.settings.add_item("touch_off_pause_execution",
                touch_off_pause.get_active, touch_off_pause.set_active)
        # redraw the toolpath if safety height changed
        gcode_safety_height.connect("value-changed", self.update_view)
        gcode_path_mode = self.gui.get_object("GCodeCornerStyleControl")
        self.settings.add_item("gcode_path_mode", gcode_path_mode.get_active,
                gcode_path_mode.set_active)
        gcode_path_mode.connect("changed", self.update_gcode_controls)
        gcode_motion_tolerance = self.gui.get_object(
                "GCodeCornerStyleMotionTolerance")
        self.settings.add_item("gcode_motion_tolerance",
                gcode_motion_tolerance.get_value,
                gcode_motion_tolerance.set_value)
        gcode_naive_tolerance = self.gui.get_object(
                "GCodeCornerStyleCAMTolerance")
        self.settings.add_item("gcode_naive_tolerance",
                gcode_naive_tolerance.get_value,
                gcode_naive_tolerance.set_value)
        gcode_start_stop_spindle = self.gui.get_object("GCodeStartStopSpindle")
        self.settings.add_item("gcode_start_stop_spindle",
                gcode_start_stop_spindle.get_active,
                gcode_start_stop_spindle.set_active)
        gcode_start_stop_spindle.connect("toggled", self.update_gcode_controls)
        gcode_filename_extension = self.gui.get_object("GCodeFilenameExtension")
        self.settings.add_item("gcode_filename_extension",
                gcode_filename_extension.get_text,
                gcode_filename_extension.set_text)
        # configure locations of external programs
        for auto_control_name, location_control_name, browse_button, key in (
                ("ExternalProgramInkscapeAuto",
                "ExternalProgramInkscapeControl",
                "ExternalProgramInkscapeBrowse", "inkscape"),
                ("ExternalProgramPstoeditAuto",
                "ExternalProgramPstoeditControl",
                "ExternalProgramPstoeditBrowse", "pstoedit")):
            self.gui.get_object(auto_control_name).connect("clicked",
                    self._locate_external_program, key)
            location_control = self.gui.get_object(location_control_name)
            self.settings.add_item("external_program_%s" % key,
                    location_control.get_text, location_control.set_text)
            self.gui.get_object(browse_button).connect("clicked",
                    self._browse_external_program_location, key)
        # parallel processing settings
        self.enable_parallel_processes = self.gui.get_object(
                "EnableParallelProcesses")
        if pycam.Utils.threading.is_multiprocessing_available():
            self.gui.get_object("ParallelProcessingDisabledLabel").hide()
            if pycam.Utils.threading.is_server_mode_available():
                self.gui.get_object("ServerModeDisabledLabel").hide()
            else:
                self.gui.get_object("ServerModeSettingsFrame").hide()
        else:
            self.gui.get_object("ParallelProcessSettingsBox").hide()
            self.gui.get_object("EnableParallelProcesses").hide()
        self.enable_parallel_processes.set_active(
                pycam.Utils.threading.is_multiprocessing_enabled())
        self.enable_parallel_processes.connect("toggled",
                self.handle_parallel_processes_settings)
        self.number_of_processes = self.gui.get_object(
                "NumberOfProcesses")
        self.number_of_processes.set_value(
                pycam.Utils.threading.get_number_of_processes())
        server_port_local_obj = self.gui.get_object("ServerPortLocal")
        self.settings.add_item("server_port_local",
                server_port_local_obj.get_value,
                server_port_local_obj.set_value)
        server_port_remote_obj = self.gui.get_object("RemoteServerPort")
        self.settings.add_item("server_port_remote",
                server_port_remote_obj.get_value,
                server_port_remote_obj.set_value)
        self.number_of_processes.connect("value-changed",
                self.handle_parallel_processes_settings)
        self.gui.get_object("EnableServerMode").connect("toggled",
                self.initialize_multiprocessing)
        self.gui.get_object("ServerPasswordGenerate").connect("clicked",
                self.generate_random_server_password)
        self.gui.get_object("ServerPasswordShow").connect("toggled",
                self.update_parallel_processes_settings)
        auth_key_obj = self.gui.get_object("ServerPassword")
        self.settings.add_item("server_auth_key", auth_key_obj.get_text,
                auth_key_obj.set_text)
        server_hostname = self.gui.get_object("RemoteServerHostname")
        self.settings.add_item("server_hostname",
                server_hostname.get_text,
                server_hostname.set_text)
        cpu_cores = pycam.Utils.threading.get_number_of_cores()
        if cpu_cores is None:
            cpu_cores = "unknown"
        self.gui.get_object("AvailableCores").set_label(str(cpu_cores))
        # status bar
        self.status_bar = self.gui.get_object("StatusBar")
        self.gui.get_object("StatusBarEventBox").connect("button-press-event",
                self.toggle_log_window)
        # menu bar
        uimanager = gtk.UIManager()
        self._accel_group = uimanager.get_accel_group()
        for window in (self.window, self.about_window, self.preferences_window,
                self.log_window, self.process_pool_window,
                self.font_dialog_window):
            window.add_accel_group(self._accel_group)
        # set the icons (in different sizes) for all windows
        gtk.window_set_default_icon_list(*get_icons_pixbuffers())
        # load menu data
        gtk_menu_file = get_data_file_location(GTKMENU_FILE)
        if gtk_menu_file is None:
            gtk.main_quit()
        uimanager.add_ui_from_file(gtk_menu_file)
        # make the actions defined in the GTKBUILD file available in the menu
        actiongroup = gtk.ActionGroup("menubar")
        for action in [action for action in self.gui.get_objects()
                if isinstance(action, gtk.Action)]:
            actiongroup.add_action(action)
        # the "pos" parameter is optional since 2.12 - we can remove it later
        uimanager.insert_action_group(actiongroup, pos=-1)
        # the "recent files" sub-menu
        if not self.recent_manager is None:
            recent_files_menu = gtk.RecentChooserMenu(self.recent_manager)
            recent_files_menu.set_name("RecentFilesMenu")
            recent_menu_filter = gtk.RecentFilter()
            for filter_name, filter_patterns in FILTER_MODEL:
                if not isinstance(filter_patterns, (list, set, tuple)):
                    filter_patterns = [filter_patterns]
                for pattern in filter_patterns:
                    recent_menu_filter.add_pattern(pattern)
            recent_files_menu.add_filter(recent_menu_filter)
            recent_files_menu.set_show_numbers(True)
            # non-local files (without "file://") are not supported. yet
            recent_files_menu.set_local_only(False)
            # most recent files to the top
            recent_files_menu.set_sort_type(gtk.RECENT_SORT_MRU)
            # show only ten files
            recent_files_menu.set_limit(10)
            uimanager.get_widget("/MenuBar/FileMenu/OpenRecentModelMenu").set_submenu(recent_files_menu)
            recent_files_menu.connect("item-activated",
                    self.load_recent_model_file)
        else:
            self.gui.get_object("OpenRecentModel").set_visible(False)
        # load the menubar and connect functions to its items
        self.menubar = uimanager.get_widget("/MenuBar")
        window_box = self.gui.get_object("WindowBox")
        window_box.pack_start(self.menubar, False)
        window_box.reorder_child(self.menubar, 0)
        # some more initialization
        self.reset_preferences()
        self.load_preferences()
        self.load_task_settings()
        # Without this "gkt.main_iteration" loop the task settings file
        # control would not be updated in time.
        while gtk.events_pending():
            gtk.main_iteration()
        autoload_task_filename = self.settings.get("default_task_settings_file")
        if autoload_task_filename:
            self.open_task_settings_file(autoload_task_filename)
        self.update_all_controls()
        self.no_dialog = no_dialog
        if not self.no_dialog:
            # register a logging handler for displaying error messages
            pycam.Utils.log.add_gtk_gui(self.window, logging.ERROR)
            # register a callback for the log window
            pycam.Utils.log.add_hook(self.add_log_message)
            self.window.show()

    def update_all_controls(self):
        self.update_toolpath_table()
        self.update_tool_table()
        self.update_process_controls()
        self.update_process_table()
        self.update_bounds_table()
        self.update_tasklist_table()
        self.update_save_actions()
        self.update_unit_labels()
        self.update_support_controls()
        self.update_model_dimensions()
        self.update_gcode_controls()
        self.update_ode_settings()
        self.update_parallel_processes_settings()
        self.update_model_type_related_controls()
        self.update_toolpath_related_controls()
        self.update_clipboard_state()

    def update_gcode_controls(self, widget=None):
        # path mode
        path_mode = self.settings.get("gcode_path_mode")
        self.gui.get_object("GCodeToleranceTable").set_sensitive(path_mode == 3)
        # spindle delay
        sensitive = self.settings.get("gcode_start_stop_spindle")
        self.gui.get_object("GCodeSpindleDelayLabel").set_sensitive(sensitive)
        self.gui.get_object("GCodeSpindleDelay").set_sensitive(sensitive)
        # tool change controls
        pos_control = self.gui.get_object("TouchOffLocationSelector")
        tool_change_pos_model = pos_control.get_model()
        active_pos_index = pos_control.get_active()
        if active_pos_index < 0:
            pos_key = None
        else:
            pos_key = tool_change_pos_model[active_pos_index][0]
        # show or hide the vbox containing the absolute tool change location
        absolute_pos_box = self.gui.get_object("AbsoluteToolChangePositionBox")
        if pos_key == "absolute":
            absolute_pos_box.show()
        else:
            absolute_pos_box.hide()
        # disable/enable the touch off position controls
        position_controls_table = self.gui.get_object("TouchOffLocationTable")
        touch_off_enabled = any([self.gui.get_object(objname).get_active()
                for objname in ("GCodeTouchOffOnStartup",
                    "GCodeTouchOffOnToolChange")])
        position_controls_table.set_sensitive(touch_off_enabled)
        # disable/enable touch probe height
        if self.gui.get_object("GCodeTouchOffOnStartup").get_active():
            update_func = "show"
        else:
            update_func = "hide"
        for objname in ("TouchOffHeight", "TouchOffHeightLabel",
                "LengthUnitTouchOffHeight"):
            getattr(self.gui.get_object(objname), update_func)()

    def update_model_type_related_controls(self):
        is_reversible = self.model and hasattr(self.model, "reverse_directions")
        controls_2d = ("ToggleModelDirectionButton", "DirectionsGuessButton")
        for control in controls_2d:
            if is_reversible:
                self.gui.get_object(control).show()
            else:
                self.gui.get_object(control).hide()
        is_extrudable = self.model and hasattr(self.model, "extrude")
        extrude_button = self.gui.get_object("ExtrudeButton")
        if is_extrudable:
            extrude_button.show()
        else:
            extrude_button.hide()
        is_projectable = self.model and (self.model.minz != self.model.maxz)
        if is_projectable:
            self.gui.get_object("Projection2D").show()
        else:
            self.gui.get_object("Projection2D").hide()
        # disable the lower boundary for contour models
        is_contour = isinstance(self.model, pycam.Geometry.Model.ContourModel)
        margin_type = self._load_bounds_settings_from_gui().get_type()
        z_low_control = self.gui.get_object("boundary_z_low")
        if is_contour and (margin_type != Bounds.TYPE_CUSTOM):
            z_low_control.set_sensitive(False)
        else:
            z_low_control.set_sensitive(True)
        # copy button
        self.gui.get_object("CopyModelToClipboard").set_sensitive(
                bool(self.model and self.model.is_export_supported()))

    def update_ode_settings(self, widget=None):
        if pycam.Utils.threading.is_multiprocessing_enabled() \
                or not pycam.Physics.ode_physics.is_ode_available():
            self.enable_ode_control.set_sensitive(False)
            self.enable_ode_control.set_active(False)
        else:
            self.enable_ode_control.set_sensitive(True)

    def progress_activity_guard(func):
        def progress_activity_guard_wrapper(self, *args, **kwargs):
            if self._progress_running:
                return
            self._progress_running = True
            self._progress_cancel_requested = False
            self.toggle_progress_bar(True)
            result = func(self, *args, **kwargs)
            self.toggle_progress_bar(False)
            self._progress_running = False
            return result
        return progress_activity_guard_wrapper

    def gui_activity_guard(func):
        def gui_activity_guard_wrapper(self, *args, **kwargs):
            if self.gui_is_active:
                return
            self.gui_is_active = True
            try:
                result = func(self, *args, **kwargs)
            except Exception:
                # Catch possible exceptions (except system-exit ones) and
                # report them.
                report_exception()
                result = None
            self.gui_is_active = False
            while self._batch_queue:
                batch_func, batch_args, batch_kwargs = self._batch_queue[0]
                del self._batch_queue[0]
                batch_func(*batch_args, **batch_kwargs)
            return result
        return gui_activity_guard_wrapper

    def _store_undo_state(self):
        # for now we only store the model
        if not self.model:
            return
        self._undo_states.append(pickle.dumps(self.model))
        log.debug("Stored the current state of the model for undo")
        while len(self._undo_states) > MAX_UNDO_STATES:
            self._undo_states.pop(0)
        self.gui.get_object("UndoButton").set_sensitive(True)

    def _restore_undo_state(self, widget=None, event=None):
        if len(self._undo_states) > 0:
            latest = StringIO.StringIO(self._undo_states.pop(-1))
            self.model = pickle.Unpickler(latest).load()
            self.gui.get_object("UndoButton").set_sensitive(
                    len(self._undo_states) > 0)
            log.info("Restored the previous state of the model")
            self._update_all_model_attributes()
        else:
            log.info("No previous undo state available - request ignored")

    def show_help(self, widget=None, page="Main_Page"):
        if not page.startswith("http"):
            url = HELP_WIKI_URL % page
        else:
            url = page
        webbrowser.open(url)

    def update_view(self, widget=None, data=None):
        if self.view3d and self.view3d.is_visible and not self.no_dialog:
            if data:
                self.view3d.glsetup()
            self.view3d.paint()

    def set_model_filename(self, filename):
        """ Store the given filename for a possible later "save model" action.
        Additionally the window's title is adjusted and the "save" buttons are
        updated.
        """
        uri = pycam.Utils.URIHandler(filename)
        self.last_model_uri = uri
        if not self.last_model_uri:
            self.window.set_title("PyCAM")
        else:
            short_name = os.path.basename(uri.get_path())
            self.window.set_title("%s - PyCAM" % short_name)
        self.update_save_actions()

    def update_save_actions(self):
        self.gui.get_object("SaveTaskSettings").set_sensitive(
            bool(self.last_task_settings_uri and \
                self.last_task_settings_uri.is_writable()))
        save_as_possible = self.model and self.model.is_export_supported()
        self.gui.get_object("SaveAsModel").set_sensitive(save_as_possible)
        save_possible = bool(self.last_model_uri and save_as_possible and \
                self.last_model_uri.is_writable())
        #TODO: fix this dirty hack to avoid silent overwrites of PS/DXF files as SVG
        if save_possible:
            extension = os.path.splitext(self.last_model_uri.get_path(
                    ))[-1].lower()
            # TODO: fix these hard-coded file extensions
            if extension[1:] in ("eps", "ps", "dxf"):
                # can't save 2D formats except SVG
                save_possible = False
        self.gui.get_object("SaveModel").set_sensitive(save_possible)

    @gui_activity_guard
    def update_support_controls(self, widget=None):
        controls = {"GridProfileExpander": ("grid", "automatic_edge",
                    "automatic_corner"),
                "GridPatternExpander": ("grid", ),
                "GridPositionExpander": ("grid", ),
                "GridManualShiftExpander": ("grid", ),
                "GridAverageDistanceExpander": ("automatic_edge",
                    "automatic_corner"),
        }
        grid_type = self.settings.get("support_grid_type")
        if grid_type == GRID_TYPES["grid"]:
            grid_square = self.gui.get_object("SupportGridDistanceSquare")
            distance_y = self.gui.get_object("SupportGridDistanceYControl")
            distance_y.set_sensitive(not grid_square.get_active())
            if grid_square.get_active():
                # We let "distance_y" track the value of "distance_x".
                self.settings.set("support_grid_distance_y",
                        self.settings.get("support_grid_distance_x"))
            self.update_support_grid_manual_model()
            self.switch_support_grid_manual_selector()
        elif grid_type in (GRID_TYPES["automatic_edge"],
                GRID_TYPES["automatic_corner"], GRID_TYPES["none"]):
            pass
        elif grid_type < 0:
            # not initialized
            pass
        else:
            log.error("Invalid grid type: %d" % grid_type)
        # show and hide all controls according to the current type
        for key, grid_types in controls.iteritems():
            obj = self.gui.get_object(key)
            if grid_type in [GRID_TYPES[allowed] for allowed in grid_types]:
                obj.show()
            else:
                obj.hide()
        self.update_support_model()
        self.update_view()

    def update_support_model(self, widget=None):
        grid_type = self.settings.get("support_grid_type")
        s = self.settings
        support_grid = None
        if grid_type == GRID_TYPES["grid"]: 
            if (s.get("support_grid_thickness") > 0) \
                    and ((s.get("support_grid_distance_x") > 0) \
                        or (s.get("support_grid_distance_y") > 0)) \
                    and ((s.get("support_grid_distance_x") == 0) \
                        or (s.get("support_grid_distance_x") \
                            > s.get("support_grid_thickness"))) \
                    and ((s.get("support_grid_distance_y") == 0) \
                        or (s.get("support_grid_distance_y") \
                            > s.get("support_grid_thickness"))) \
                    and (s.get("support_grid_height") > 0):
                support_grid = pycam.Toolpath.SupportGrid.get_support_grid(
                        s.get("minx"), s.get("maxx"), s.get("miny"), s.get("maxy"),
                        s.get("minz"), s.get("support_grid_distance_x"),
                        s.get("support_grid_distance_y"),
                        s.get("support_grid_thickness"),
                        s.get("support_grid_height"),
                        offset_x=s.get("support_grid_offset_x"),
                        offset_y=s.get("support_grid_offset_y"),
                        adjustments_x=self.grid_adjustments_x,
                        adjustments_y=self.grid_adjustments_y)
        elif grid_type in (GRID_TYPES["automatic_edge"],
                GRID_TYPES["automatic_corner"]):
            if (s.get("support_grid_thickness") > 0) \
                    and (s.get("support_grid_height") > 0) \
                    and (s.get("support_grid_average_distance") > 0) \
                    and (s.get("support_grid_minimum_bridges") > 0):
                # get the minimum z value of the bounding box
                bounds = self.settings.get("current_bounds")
                if (bounds is None) and (len(self.bounds_list) > 0):
                    bounds = self.bounds_list[0]
                if not bounds is None:
                    minz = bounds.get_absolute_limits(
                            reference=self.model.get_bounds())[0][2]
                    corner_start = (grid_type == GRID_TYPES["automatic_corner"])
                    support_grid = pycam.Toolpath.SupportGrid.get_support_distributed(
                            s.get("model"), minz,
                            s.get("support_grid_average_distance"),
                            s.get("support_grid_minimum_bridges"),
                            s.get("support_grid_thickness"),
                            s.get("support_grid_height"),
                            s.get("support_grid_length"),
                            bounds.get_referenced_bounds(s.get("model").get_bounds()),
                            start_at_corners=corner_start)
        elif grid_type == GRID_TYPES["none"]:
            pass
        s.set("support_grid", support_grid)
        self.update_view()

    def switch_support_grid_manual_selector(self, widget=None):
        old_axis_was_x = self.grid_adjustment_axis_x_last
        self.grid_adjustment_axis_x_last = \
                self.grid_adjustment_axis_x.get_active()
        if self.grid_adjustment_axis_x.get_active():
            # x axis is selected
            if not old_axis_was_x:
                self.update_support_grid_manual_model()
            max_distance = self.settings.get("support_grid_distance_x")
        else:
            # y axis
            if old_axis_was_x:
                self.update_support_grid_manual_model()
            max_distance = self.settings.get("support_grid_distance_y")
        # we allow an individual adjustment of 66% of the distance
        max_distance /= 1.5
        if hasattr(self.grid_adjustment_value, "set_lower"):
            # gtk 2.14 is required for "set_lower" and "set_upper"
            self.grid_adjustment_value.set_lower(-max_distance)
            self.grid_adjustment_value.set_upper(max_distance)
        if self.grid_adjustment_value.get_value() \
                != self.settings.get("support_grid_adjustment_value"):
            self.grid_adjustment_value.set_value(self.settings.get(
                    "support_grid_adjustment_value"))
        self.gui.get_object("SupportGridPositionManualShiftBox").set_sensitive(
                self.grid_adjustment_selector.get_active() >= 0)
        
    def update_support_grid_manual_adjust(self, widget=None, data1=None,
            data2=None):
        new_value = self.grid_adjustment_value.get_value()
        self.settings.set("support_grid_adjustment_value", new_value)
        tree_iter = self.grid_adjustment_selector.get_active_iter()
        if not tree_iter is None:
            value_string = "(%+.1f)" % new_value
            self.grid_adjustment_model.set(tree_iter, 1, value_string)
        self.update_support_model()
        self.update_view()

    def reset_support_grid_manual(self, widget=None, reset_all=False):
        if reset_all:
            self.grid_adjustments_x = []
            self.grid_adjustments_y = []
        else:
            self.settings.set("support_grid_adjustment_value", 0)
        self.update_support_grid_manual_model()
        self.switch_support_grid_manual_selector()
        self.update_support_model()
        self.update_view()

    def update_support_grid_manual_model(self):
        old_index = self.grid_adjustment_selector.get_active()
        model = self.grid_adjustment_model
        model.clear()
        s = self.settings
        # get the toolpath without adjustments
        base_x, base_y = pycam.Toolpath.SupportGrid.get_support_grid_locations(
                s.get("minx"), s.get("maxx"), s.get("miny"), s.get("maxy"),
                s.get("support_grid_distance_x"),
                s.get("support_grid_distance_y"),
                offset_x=s.get("support_grid_offset_x"),
                offset_y=s.get("support_grid_offset_y"))
        # fill the adjustment lists
        while len(self.grid_adjustments_x) < len(base_x):
            self.grid_adjustments_x.append(0)
        while len(self.grid_adjustments_y) < len(base_y):
            self.grid_adjustments_y.append(0)
        # select the currently active list
        if self.grid_adjustment_axis_x.get_active():
            base = base_x
            adjustments = self.grid_adjustments_x
        else:
            base = base_y
            adjustments = self.grid_adjustments_y
        # generate the model content
        for index, base_value in enumerate(base):
            position = "%.2f%s" % (base_value, s.get("unit"))
            if (0 <= index < len(adjustments)) and (adjustments[index] != 0):
                diff = "(%+.1f)" % adjustments[index]
            else:
                diff = ""
            model.append((position, diff))
        if old_index < len(base):
            self.grid_adjustment_selector.set_active(old_index)
        else:
            self.grid_adjustment_selector.set_active(-1)

    @gui_activity_guard
    def generate_random_server_password(self, widget=None):
        all_characters = string.letters + string.digits
        random_pw = "".join([random.choice(all_characters) for i in range(12)])
        self.gui.get_object("ServerPassword").set_text(random_pw)

    @gui_activity_guard
    def update_parallel_processes_settings(self, widget=None):
        parallel_settings = self.gui.get_object("ParallelProcessSettingsBox")
        server_enabled = self.gui.get_object("EnableServerMode")
        server_mode_settings = self.gui.get_object("ServerModeSettingsTable")
        # update the show/hide state of the password
        hide_password = self.gui.get_object("ServerPasswordShow").get_active()
        self.gui.get_object("ServerPassword").set_visibility(hide_password)
        if (self.gui.get_object("NumberOfProcesses").get_value() == 0) \
                and self.enable_parallel_processes.get_active():
            self.gui.get_object("ZeroProcessesWarning").show()
        else:
            self.gui.get_object("ZeroProcessesWarning").hide()
        if self.enable_parallel_processes.get_active():
            parallel_settings.set_sensitive(True)
            if server_enabled.get_active():
                # don't allow changes for an active connection
                server_mode_settings.set_sensitive(False)
            else:
                server_mode_settings.set_sensitive(True)
        else:
            parallel_settings.set_sensitive(False)
            server_enabled.set_active(False)
        # check availability of ODE again (conflicts with multiprocessing)
        self.update_ode_settings()

    def handle_parallel_processes_settings(self, widget=None):
        new_num_of_processes = self.number_of_processes.get_value()
        new_enable_parallel = self.enable_parallel_processes.get_active()
        old_num_of_processes = pycam.Utils.threading.get_number_of_processes()
        old_enable_parallel = pycam.Utils.threading.is_multiprocessing_enabled()
        if (old_num_of_processes != new_num_of_processes) \
                or (old_enable_parallel != new_enable_parallel):
            self.initialize_multiprocessing()

    @gui_activity_guard
    def initialize_multiprocessing(self, widget=None):
        complete_area = self.gui.get_object("MultiprocessingFrame")
        # prevent any further actions while the connection is established
        complete_area.set_sensitive(False)
        # wait for the above "set_sensitive" to finish
        while gtk.events_pending():
            gtk.main_iteration()
        enable_parallel = self.enable_parallel_processes.get_active()
        enable_server_obj = self.gui.get_object("EnableServerMode")
        enable_server = enable_server_obj.get_active()
        remote_host = self.gui.get_object("RemoteServerHostname").get_text()
        if remote_host:
            remote_port = int(self.gui.get_object(
                    "RemoteServerPort").get_value())
            remote = "%s:%s" % (remote_host, remote_port)
        else:
            remote = None
        local_port = int(self.gui.get_object("ServerPortLocal").get_value())
        auth_key = self.gui.get_object("ServerPassword").get_text()
        if not auth_key and enable_parallel and enable_server:
            log.error("You need to provide a password for this connection.")
            enable_server_obj.set_active(False)
        elif enable_parallel:
            if enable_server and \
                    (pycam.Utils.get_platform() == pycam.Utils.PLATFORM_WINDOWS):
                if self.number_of_processes.get_value() > 0:
                    log.warn("Mixed local and remote processes are " + \
                        "currently not available on the Windows platform. " + \
                        "Setting the number of local processes to zero." + \
                        os.linesep + "See <a href=\"" + \
                        HELP_WIKI_URL % "Parallel_Processing_on_different_Platforms" + \
                        "\">platform feature matrix</a> for more details.")
                    self.number_of_processes.set_value(0)
                self.number_of_processes.set_sensitive(False)
            else:
                self.number_of_processes.set_sensitive(True)
            num_of_processes = int(self.number_of_processes.get_value())
            error = pycam.Utils.threading.init_threading(
                    number_of_processes=num_of_processes,
                    enable_server=enable_server, remote=remote,
                    server_credentials=auth_key, local_port=local_port)
            if error:
                log.error("Failed to start server: %s" % error)
                pycam.Utils.threading.cleanup()
                enable_server_obj.set_active(False)
        else:
            pycam.Utils.threading.cleanup()
            log.info("Multiprocessing disabled")
        # set the label of the "connect" button
        if enable_server_obj.get_active():
            info = gtk.stock_lookup(gtk.STOCK_DISCONNECT)
        else:
            info = gtk.stock_lookup(gtk.STOCK_CONNECT)
        enable_server_obj.set_label(info[0])
        complete_area.set_sensitive(True)
        self.append_to_queue(self.update_parallel_processes_settings)

    def _browse_external_program_location(self, widget=None, key=None):
        location = self.get_filename_via_dialog(title="Select the executable " \
                + "for '%s'" % key, mode_load=True,
                parent=self.preferences_window)
        if not location is None:
            self.settings.set("external_program_%s" % key, location)


    def _locate_external_program(self, widget=None, key=None):
        # the button was just activated
        location = pycam.Utils.get_external_program_location(key)
        if not location:
            log.error("Failed to locate the external program '%s'. " % key \
                    + "Please install the program and try again." \
                    + os.linesep \
                    + "Or maybe you need to specify the location manually.")
        else:
            # store the new setting
            self.settings.set("external_program_%s" % key, location)

    @gui_activity_guard
    def adjust_bounds(self, widget, axis, change):
        bounds = self.settings.get("current_bounds")
        abs_bounds_low, abs_bounds_high = bounds.get_absolute_limits(
                reference=self.model.get_bounds())
        # calculate the "change" for +/- (10% of this axis' model dimension)
        if bounds is None:
            return
        if axis == "x":
            change_value = (self.model.maxx - self.model.minx) * 0.1
        elif axis == "y":
            change_value = (self.model.maxy - self.model.miny) * 0.1
        elif axis == "z":
            change_value = (self.model.maxz - self.model.minz) * 0.1
        else:
            # not allowed
            return
        # calculate the new bounds
        axis_index = "xyz".index(axis)
        if change == "0":
            abs_bounds_low[axis_index] = getattr(self.model, "min%s" % axis)
            abs_bounds_high[axis_index] = getattr(self.model, "max%s" % axis)
        elif change == "+":
            abs_bounds_low[axis_index] -= change_value
            abs_bounds_high[axis_index] += change_value
        elif change == "-":
            abs_bounds_low[axis_index] += change_value
            abs_bounds_high[axis_index] -= change_value
        else:
            # not allowed
            return
        # transfer the new bounds values to the old settings
        bounds.adjust_bounds_to_absolute_limits(abs_bounds_low, abs_bounds_high,
                reference=self.model.get_bounds())
        # update the controls
        self._put_bounds_settings_to_gui(bounds)
        # update the visualization
        self.append_to_queue(self.update_boundary_limits)

    @gui_activity_guard
    def switch_bounds_type(self, widget=None):
        bounds = self.settings.get("current_bounds")
        new_type = self._load_bounds_settings_from_gui().get_type()
        if new_type == bounds.get_type():
            # no change
            return
        # calculate the absolute bounds of the previous configuration
        abs_bounds_low, abs_bounds_high = bounds.get_absolute_limits(
                reference=self.model.get_bounds())
        bounds.set_type(new_type)
        bounds.adjust_bounds_to_absolute_limits(abs_bounds_low, abs_bounds_high,
                reference=self.model.get_bounds())
        self._put_bounds_settings_to_gui(bounds)
        # update the descriptive label for each margin type
        self.update_bounds_controls()
        self.append_to_queue(self.update_boundary_limits)
        # update the sensitivity of the lower z margin for contour models
        self.update_model_type_related_controls()

    @gui_activity_guard
    def update_boundary_limits(self, widget=None):
        # update the values in the manual support grid adjustment list
        self.update_support_grid_manual_model()
        # the support grid depends on the boundary
        self.update_support_model()
        self.update_view()

    def update_tasklist_controls(self):
        # en/disable some buttons
        index = self._treeview_get_active_index(self.tasklist_table, self.task_list)
        selection_active = not index is None
        self.gui.get_object("TaskListDelete").set_sensitive(selection_active)
        self.gui.get_object("TaskListMoveUp").set_sensitive(selection_active and index > 0)
        self.gui.get_object("TaskListMoveDown").set_sensitive(selection_active and index < len(self.task_list) - 1)
        self.gui.get_object("GenerateToolPathButton").set_sensitive(selection_active)
        # "add" is only allowed, if there are any tools, processes and bounds
        self.gui.get_object("TaskListAdd").set_sensitive(
                (len(self.tool_list) > 0) \
                and (len(self.process_list) > 0) \
                and (len(self.bounds_list) > 0))
        details_box = self.gui.get_object("TaskDetails")
        if selection_active:
            details_box.show()
        else:
            details_box.hide()
        # check if any of the tasks is marked as "enabled"
        enabled_count = len([True for task in self.task_list if task["enabled"]])
        self.gui.get_object("GenerateAllToolPathsButton").set_sensitive(enabled_count > 0)
        # update the summary description of the currently active task
        self.update_task_description()

    def update_task_description(self):
        # update the task description
        lines = []
        task_index = self._treeview_get_active_index(self.tasklist_table, self.task_list)
        if (not task_index is None) and (task_index < len(self.task_list)):
            task = self.task_list[task_index]
            # block all "change" signals for the task controls
            for obj, signal_handler in self._task_property_signals:
                obj.handler_block(signal_handler)
            self.gui.get_object("TaskNameControl").set_text(task["name"])
            tool = task["tool"]
            self.gui.get_object("TaskToolSelector").set_active(self.tool_list.index(tool))
            process = task["process"]
            self.gui.get_object("TaskProcessSelector").set_active(self.process_list.index(process))
            bounds = task["bounds"]
            self.gui.get_object("TaskBoundsSelector").set_active(self.bounds_list.index(bounds))
            # unblock the signals again
            for obj, signal_handler in self._task_property_signals:
                obj.handler_unblock(signal_handler)
            unit = self.settings.get("unit")
            tool_desc = "Tool: %s " % tool["shape"]
            if tool["shape"] != "ToroidalCutter":
                tool_desc += "(%.4f%s)" % (2 * tool["tool_radius"], unit)
            else:
                tool_desc += "(%.4f%s / %.4f%s)" % ( 2 * tool["tool_radius"], unit, 2 * tool["torus_radius"], unit)
            lines.append(tool_desc)
            lines.append("Spindle speed: %drpm / Feedrate: %d%s/minute" % (tool["speed"], tool["feedrate"], unit))
            lines.append("Strategy: %s" % process["path_strategy"])
            if process["path_strategy"] == "EngraveStrategy":
                lines.append("Engrave offset: %.3f" % process["engrave_offset"])
            else:
                lines.append("Milling style: %s" % process["milling_style"])
                if process["path_strategy"] != "ContourFollowStrategy":
                    lines.append("Overlap: %d%%" % process["overlap_percent"])
                    lines.append("Material allowance: %.2f%s" \
                            % (process["material_allowance"], unit))
            if process["path_strategy"] != "SurfaceStrategy":
                lines.append("Maximum step down: %.2f%s" % (process["step_down"], unit))
        else:
            lines.append("No task selected")
        self.gui.get_object("CurrentTaskSummary").set_text(os.linesep.join(lines))

    def update_tasklist_table(self, new_index=None, skip_model_update=False):
        tasklist_model = self.gui.get_object("TaskList")
        if new_index is None:
            # keep the old selection - this may return "None" if nothing is selected
            new_index = self._treeview_get_active_index(self.tasklist_table, self.task_list)
        if not skip_model_update:
            tasklist_model.clear()
            # remove broken tasks from the list (tool or process was deleted)
            self.task_list = [task for task in self.task_list
                    if (task["tool"] in self.tool_list) \
                            and (task["process"] in self.process_list) \
                            and (task["bounds"] in self.bounds_list)]
            counter = 0
            for task in self.task_list:
                tasklist_model.append((counter, task["name"], task["enabled"]))
                counter += 1
            if not new_index is None:
                self._treeview_set_active_index(self.tasklist_table, new_index)
        self.update_tasklist_controls()

    def switch_tasklist_table_selection(self, widget=None):
        current_task = self.settings.get("current_task")
        if not current_task is None:
            self.settings.set("current_tool", current_task["tool"])
            self.update_tool_table(skip_model_update=True)
            self.settings.set("current_process", current_task["process"])
            self.update_process_table(skip_model_update=True)
            self.settings.set("current_bounds", current_task["bounds"])
            self.update_bounds_table(skip_model_update=True)
        self.update_tasklist_controls()

    @gui_activity_guard
    def _handle_task_setting_change(self, widget, data=None):
        # get the index of the currently selected task
        task = self.settings.get("current_task")
        if task is None:
            return
        task_name_obj = self.gui.get_object("TaskNameControl")
        old_name = task["name"]
        new_name = task_name_obj.get_text()
        if old_name != new_name:
            task["name"] = new_name
        tool_id = self.gui.get_object("TaskToolSelector").get_active()
        task["tool"] = self.tool_list[tool_id]
        process_id = self.gui.get_object("TaskProcessSelector").get_active()
        task["process"] = self.process_list[process_id]
        bounds_id = self.gui.get_object("TaskBoundsSelector").get_active()
        old_bounds_id = self.bounds_list.index(task["bounds"])
        task["bounds"] = self.bounds_list[bounds_id]
        # update the current boundary limit, if it was changed
        if bounds_id != old_bounds_id:
            self.append_to_queue(self.update_boundary_limits)
        # update the tasklist table (especially for name changes)
        self.update_tasklist_table()
        # the task_name input control seems to loose focus somehow
        if old_name != new_name:
            task_name_obj.grab_focus()

    @gui_activity_guard
    def _handle_tasklist_button_event(self, widget, data, action=None):
        # "toggle" uses two parameters - all other actions have only one
        if action is None:
            action = data
        # get the index of the currently selected task
        try:
            current_task_index = self._treeview_get_active_index(self.tasklist_table, self.task_list)
        except ValueError:
            current_task_index = None
        self._treeview_button_event(self.tasklist_table, self.task_list, action, self.update_tasklist_table)
        if action == "add":
            new_task = {}
            # look for the first unused default name
            prefix = "New Task "
            index = 1
            # loop while the current name is in use
            while [True for task in self.task_list if task["name"] == "%s%d" % (prefix, index)]:
                index += 1
            new_task["name"] = "%s%d" % (prefix, index)
            new_task["tool"] = self.tool_list[0]
            new_task["process"] = self.process_list[0]
            new_task["bounds"] = self.bounds_list[0]
            new_task["enabled"] = True
            self.task_list.append(new_task)
            self.update_tasklist_table(self.task_list.index(new_task))
        elif action == "toggle_enabled":
            # "data" contains the row of the clicked checkbox
            if not data is None:
                current_task_index = int(data)
                if (not current_task_index is None) and (current_task_index < len(self.task_list)):
                    self.task_list[current_task_index]["enabled"] = not self.task_list[current_task_index]["enabled"]
                # update the table values
                self.update_tasklist_table(current_task_index)
        elif action == "generate_all_toolpaths":
            self.process_multiple_tasks()
        elif action == "generate_one_toolpath":
            self.process_one_task(current_task_index)
        else:
            pass

    def process_one_task(self, task_index):
        try:
            task = self.task_list[task_index]
        except IndexError:
            # this should only happen, if we were called in batch mode (command line)
            log.warn("The given task ID (%d) does not exist. Valid values are: %s." % (task_index, range(len(self.task_list))))
            return
        self.generate_toolpath(task["tool"], task["process"], task["bounds"])

    def process_multiple_tasks(self, task_list=None):
        if task_list is None:
            task_list = self.task_list[:]
        enabled_tasks = []
        for index in range(len(task_list)):
            task = task_list[index]
            if task["enabled"]:
                enabled_tasks.append(task)
        progress_bar = self.gui.get_object("MultipleProgressBar")
        progress_bar.show()
        for index in range(len(enabled_tasks)):
            progress_bar.set_fraction(float(index) / len(enabled_tasks))
            progress_bar.set_text("Toolpath %d/%d" % (index, len(enabled_tasks)))
            task = enabled_tasks[index]
            if not self.generate_toolpath(task["tool"], task["process"],
                    task["bounds"]):
                # break out of the loop, if cancel was requested
                break
        progress_bar.hide()

    def update_process_controls(self, widget=None, data=None):
        # possible dependencies of the DropCutter
        get_obj = self.gui.get_object
        strategy = None
        for one_strategy in ("PushRemoveStrategy", "ContourPolygonStrategy",
                "ContourFollowStrategy", "SurfaceStrategy", "EngraveStrategy"):
            if get_obj(one_strategy).get_active():
                strategy = one_strategy
                break
        else:
            raise ValueError("Invalid path strategy selected")
        if strategy == "ContourPolygonStrategy" \
                and not get_obj("MillingStyleIgnore").get_active():
            get_obj("MillingStyleIgnore").set_active(True)
        if strategy == "ContourPolygonStrategy" \
                and not get_obj("GridDirectionX").get_active():
            # only "x" direction for ContourPolygon
            get_obj("GridDirectionX").set_active(True)
        if strategy in ("ContourFollowStrategy", "EngraveStrategy") \
                and get_obj("MillingStyleIgnore").get_active():
            get_obj("MillingStyleConventional").set_active(True)
        all_controls = ("GridDirectionX", "GridDirectionY", "GridDirectionXY",
                "MillingStyleConventional", "MillingStyleClimb",
                "MillingStyleIgnore", "MaxStepDownControl",
                "MaterialAllowanceControl", "OverlapPercentControl",
                "EngraveOffsetControl", "PocketingControl")
        active_controls = {
            "PushRemoveStrategy": ("GridDirectionX", "GridDirectionY",
                    "GridDirectionXY", "MillingStyleConventional",
                    "MillingStyleClimb", "MillingStyleIgnore",
                    "MaxStepDownControl", "MaterialAllowanceControl",
                    "OverlapPercentControl"),
            # TODO: direction y and xy currently don't work for ContourPolygonStrategy
            "ContourPolygonStrategy": ("GridDirectionX",
                    "MillingStyleIgnore", "MaxStepDownControl",
                    "MaterialAllowanceControl", "OverlapPercentControl"),
            "ContourFollowStrategy": ("MillingStyleConventional",
                    "MillingStyleClimb", "MaxStepDownControl"),
            "SurfaceStrategy": ("GridDirectionX", "GridDirectionY",
                    "GridDirectionXY", "MillingStyleConventional",
                    "MillingStyleClimb", "MillingStyleIgnore",
                    "MaterialAllowanceControl", "OverlapPercentControl"),
            "EngraveStrategy": ("MaxStepDownControl", "EngraveOffsetControl",
                    "MillingStyleConventional", "MillingStyleClimb",
                    "PocketingControl"),
        }
        for one_control in all_controls:
            get_obj(one_control).set_sensitive(one_control in active_controls[strategy])

    def update_tool_controls(self, widget=None, data=None):
        # disable the toroidal radius if the toroidal cutter is not enabled
        if self.gui.get_object("ToroidalCutter").get_active():
            self.gui.get_object("TorusDiameterControl").show()
            self.gui.get_object("TorusDiameterLabel").show()
        else:
            self.gui.get_object("TorusDiameterControl").hide()
            self.gui.get_object("TorusDiameterLabel").hide()
        for objname, default_value in (("ToolDiameterControl", 1.0),
                ("TorusDiameterControl", 0.25),
                ("SpindleSpeedControl", 1000),
                ("FeedrateControl", 200)):
            obj = self.gui.get_object(objname)
            if obj.get_value() == 0:
                # set the value to the configured minimum
                obj.set_value(default_value)
        self.gui.get_object("ExportEMCToolDefinition").set_sensitive(len(self.tool_list) > 0)

    @gui_activity_guard
    @progress_activity_guard
    def toggle_font_dialog_window(self, widget=None, event=None, state=None):
        # only "delete-event" uses four arguments
        # TODO: unify all these "toggle" functions for different windows into one single function (including storing the position)
        if state is None:
            state = event
        if state is None:
            state = not self._font_dialog_window_visible
        if state:
            if self.font_selector is None:
                self.update_progress_bar("Initializing fonts")
                # create it manually to ease access
                font_selector = gtk.combo_box_new_text()
                self.gui.get_object("FontSelectionBox").pack_start(
                        font_selector, expand=False, fill=False)
                sorted_keys = list(self._fonts_cache.get_font_names())
                sorted_keys.sort(key=lambda x: x.upper())
                for name in sorted_keys:
                    font_selector.append_text(name)
                if sorted_keys:
                    font_selector.set_active(0)
                else:
                    log.warn("No single-line fonts found!")
                font_selector.connect("changed",
                        self.update_font_dialog_preview)
                font_selector.show()
                self.font_selector = font_selector
            if len(self._fonts_cache) > 0:
                # show the dialog only if fonts are available
                if self._font_dialog_window_position:
                    self.font_dialog_window.move(
                            *self._font_dialog_window_position)
                self.font_dialog_window.show()
                self._font_dialog_window_visible = True
            else:
                log.error("No fonts were found on your system. " \
                        + "Please check the Log Window for details.")
        else:
            self._font_dialog_window_position = \
                    self.font_dialog_window.get_position()
            self.font_dialog_window.hide()
            self._font_dialog_window_visible = False
        # don't close the window - just hide it (for "delete-event")
        return True

    def get_font_dialog_text_rendered(self):
        input_field = self.gui.get_object("FontDialogInput")
        text_buffer = input_field.get_buffer()
        text = text_buffer.get_text(text_buffer.get_start_iter(),
                text_buffer.get_end_iter())
        text = unicode(text)
        if text:
            skew = self.gui.get_object("FontSideSkewValue").get_value()
            line_space = self.gui.get_object("FontLineSpacingValue").get_value()
            pitch = self.gui.get_object("FontCharacterSpacingValue").get_value()
            # get the active align setting
            for objname, value, justification in (
                    ("FontTextAlignLeft", TEXT_ALIGN_LEFT, gtk.JUSTIFY_LEFT),
                    ("FontTextAlignCenter", TEXT_ALIGN_CENTER, gtk.JUSTIFY_CENTER),
                    ("FontTextAlignRight", TEXT_ALIGN_RIGHT, gtk.JUSTIFY_RIGHT)):
                obj = self.gui.get_object(objname)
                if obj.get_active():
                    align = value
                    input_field.set_justification(justification)
            font_name = self.font_selector.get_active_text()
            charset = self._fonts_cache.get_font(font_name)
            return charset.render(text, skew=skew, line_spacing=line_space,
                    pitch=pitch, align=align)
        else:
            # empty text
            return None

    @gui_activity_guard
    def import_from_font_dialog(self, widget=None):
        self.load_model(self.get_font_dialog_text_rendered())
        self.append_to_queue(self.toggle_font_dialog_window)

    def export_from_font_dialog(self, widget=None):
        text_model = self.get_font_dialog_text_rendered()
        if text_model and (not text_model.maxx is None):
            self.save_model(model=text_model, store_filename=False)

    def copy_font_dialog_to_clipboard(self, widget=None):
        text_model = self.get_font_dialog_text_rendered()
        if text_model and (not text_model.maxx is None):
            text_buffer = StringIO.StringIO()
            text_model.export(comment=self.get_meta_data(),
                    unit=self.settings.get("unit")).write(text_buffer)
            text_buffer.seek(0)
            text = text_buffer.read()
            self._copy_text_to_clipboard(text, CLIPBOARD_TARGETS["svg"])

    def update_clipboard_state(self, clipboard=None, event=None):
        data, importer = self._get_data_and_importer_from_clipboard()
        paste_button = self.gui.get_object("PasteModelFromClipboard")
        paste_button.set_sensitive(not data is None)

    def _copy_text_to_clipboard(self, text, targets):
        clip_targets = [(key, gtk.TARGET_OTHER_WIDGET, index)
                for index, key in enumerate(targets)]
        def get_func(clipboard, selectiondata, info, (text, clip_type)):
            selectiondata.set(clip_type, 8, text)
        if "svg" in "".join(targets).lower():
            # Inkscape for Windows strictly requires the BITMAP type
            clip_type = gtk.gdk.SELECTION_TYPE_BITMAP
        else:
            clip_type = gtk.gdk.SELECTION_TYPE_STRING
        result = self.clipboard.set_with_data(clip_targets, get_func,
                lambda *args: None, (text, clip_type))
        self.clipboard.store()

    def copy_model_to_clipboard(self, widget=None):
        if not self.model.is_export_supported():
            return
        text_buffer = StringIO.StringIO()
        self.model.export(comment=self.get_meta_data(),
                unit=self.settings.get("unit")).write(text_buffer)
        text_buffer.seek(0)
        is_contour = isinstance(self.model, pycam.Geometry.Model.ContourModel)
        # TODO: this should not be decided here
        if is_contour:
            targets = CLIPBOARD_TARGETS["svg"]
        else:
            targets = CLIPBOARD_TARGETS["stl"]
        self._copy_text_to_clipboard(text_buffer.read(), targets)

    def _get_data_and_importer_from_clipboard(self):
        for targets, filename in ((CLIPBOARD_TARGETS["svg"], "foo.svg"),
               (CLIPBOARD_TARGETS["stl"], "foo.stl"),
               (CLIPBOARD_TARGETS["ps"], "foo.ps"),
               (CLIPBOARD_TARGETS["dxf"], "foo.dxf")):
            for target in targets:
                data = self.clipboard.wait_for_contents(target)
                if not data is None:
                    importer = pycam.Importers.detect_file_type(filename)[1]
                    return data, importer
        return None, None

    @progress_activity_guard
    @gui_activity_guard
    def paste_model_from_clipboard(self, widget=None):
        data, importer = self._get_data_and_importer_from_clipboard()
        if data:
            self.update_progress_bar(text="Loading model from clipboard")
            text_buffer = StringIO.StringIO(data.data)
            model = importer(text_buffer,
                    program_locations=self._get_program_locations(),
                    unit=self.settings.get("unit"),
                    fonts_cache=self._fonts_cache,
                    callback=self.update_progress_bar)
            if model:
                log.info("Loaded a model from clipboard")
                self.load_model(model)
            else:
                log.warn("Failed to load a model from clipboard")
        else:
            log.warn("The clipboard does not contain suitable data")

    @gui_activity_guard
    def update_font_dialog_preview(self, widget=None, event=None):
        if not self.font_selector:
            # not initialized
            return
        if len(self._fonts_cache) == 0:
            # empty
            return
        font_name = self.font_selector.get_active_text()
        font = self._fonts_cache.get_font(font_name)
        self.gui.get_object("FontAuthorText").set_label(
                os.linesep.join(font.get_authors()))
        preview_widget = self.gui.get_object("FontDialogPreview")
        final_drawing_area = preview_widget.window
        text_model = self.get_font_dialog_text_rendered()
        # always clean the background
        x, y, width, height = preview_widget.get_allocation()
        drawing_area = gtk.gdk.Pixmap(final_drawing_area, width, height)
        drawing_area.draw_rectangle(preview_widget.get_style().white_gc, True,
                0, 0, width, height)
        # carefully check if there are lines in the rendered text
        if text_model and (not text_model.maxx is None) and \
                (text_model.maxx > text_model.minx):
            # leave a small border around the preview
            border = 3
            x_fac = (width - 1 - 2 * border) / \
                    (text_model.maxx - text_model.minx)
            y_fac = (height - 1 - 2 * border) / \
                    (text_model.maxy - text_model.miny)
            factor = min(x_fac, y_fac)
            # vertically centered preview
            y_offset = int((height - 2 * border - \
                    factor * (text_model.maxy - text_model.miny)) // 2)
            gc = drawing_area.new_gc()
            if text_model.minx == 0:
                # left align
                get_virtual_x = lambda x: int(x * factor) + border
            elif text_model.maxx == 0:
                # right align
                get_virtual_x = lambda x: width + int(x * factor) - 1 - border
            else:
                # center align
                get_virtual_x = lambda x: \
                        int(width / 2.0 + x * factor) - 1 - border
            get_virtual_y = lambda y: -y_offset + \
                    height - int((y - text_model.miny) * factor) - 1 - border
            for polygon in text_model.get_polygons():
                draw_points = []
                points = polygon.get_points()
                if polygon.is_closed:
                    # add the first point again to close the polygon
                    points.append(points[0])
                for point in points:
                    x = get_virtual_x(point.x)
                    y = get_virtual_y(point.y)
                    draw_points.append((x, y))
                drawing_area.draw_lines(gc, draw_points)
        final_gc = final_drawing_area.new_gc()
        final_drawing_area.draw_drawable(final_gc, drawing_area, 0, 0, 0, 0,
                -1, -1)

    @gui_activity_guard
    def toggle_about_window(self, widget=None, event=None, state=None):
        # only "delete-event" uses four arguments
        # TODO: unify all these "toggle" functions for different windows into one single function (including storing the position)
        if state is None:
            state = event
        if state:
            self.about_window.show()
        else:
            self.about_window.hide()
        # don't close the window - just hide it (for "delete-event")
        return True

    @progress_activity_guard
    @gui_activity_guard
    def extrude_model(self, widget=None):
        self.update_progress_bar("Calculating extrusion")
        extrusion_type_selector = self.gui.get_object("ExtrusionTypeSelector")
        type_model = extrusion_type_selector.get_model()
        type_active = extrusion_type_selector.get_active()
        if type_active >= 0:
            type_string = type_model[type_active][0]
            height = self.gui.get_object("ExtrusionHeight").get_value()
            width = self.gui.get_object("ExtrusionWidth").get_value()
            grid_size = self.gui.get_object("ExtrusionGrid").get_value()
            if type_string == "radius_up":
                func = lambda x: height * math.sqrt((width ** 2 - max(0, width - x) ** 2))
            elif type_string == "radius_down":
                func = lambda x: height * (1 - math.sqrt((width ** 2 - min(width, x) ** 2)) / width)
            elif type_string == "skewed":
                func = lambda x: height * min(1, x / width)
            elif type_string == "sine":
                func = lambda x: height * math.sin(min(x, width) / width * math.pi / 2)
            elif type_string == "sigmoid":
                func = lambda x: height * ((math.sin(((min(x, width) / width) - 0.5) * math.pi) + 1) / 2)
            else:
                log.error("Unknown extrusion type selected: %s" % type_string)
                return
            self.toggle_extrusion_dialog(False)
            model = self.model.extrude(stepping=grid_size, func=func,
                    callback=self.update_progress_bar)
            if model and (not model.minx is None):
                self.load_model(model)
            else:
                self.toggle_extrusion_dialog(True)

    def toggle_extrusion_dialog(self, widget=None, event=None, state=None):
        if state is None:
            # the "delete-event" issues the additional "event" argument
            state = event
        if state is None:
            state = not self._extrusion_dialog_visible
        if state:
            if self._extrusion_dialog_position:
                self.extrusion_dialog_window.move(*self._extrusion_dialog_position)
            self.extrusion_dialog_window.show()
        else:
            self._extrusion_dialog_position = self.extrusion_dialog_window.get_position()
            self.extrusion_dialog_window.hide()
        self._extrusion_dialog_visible = state
        # don't close the window - just hide it (for "delete-event")
        return True

    @gui_activity_guard
    def toggle_preferences_window(self, widget=None, event=None, state=None):
        if state is None:
            # the "delete-event" issues the additional "event" argument
            state = event
        if state is None:
            state = not self._preferences_window_visible
        if state:
            if self._preferences_window_position:
                self.preferences_window.move(*self._preferences_window_position)
            self.preferences_window.show()
        else:
            self._preferences_window_position = self.preferences_window.get_position()
            self.preferences_window.hide()
        self._preferences_window_visible = state
        # don't close the window - just hide it (for "delete-event")
        return True

    def add_log_message(self, title, message, record=None):
        timestamp = datetime.datetime.fromtimestamp(
                record.created).strftime("%H:%M")
        # avoid the ugly character for a linefeed
        message = " ".join(message.splitlines())
        try:
            message = message.encode("utf-8")
        except UnicodeDecodeError:
            # remove all non-ascii characters
            clean_char = lambda c: (32 <= ord(c) < 128) and c or " "
            message = "".join([clean_char(char) for char in message])
        self.log_model.append((timestamp, title, message))
        # update the status bar (if the GTK interface is still active)
        if not self.status_bar.window is None:
            # remove the last message from the stack (probably not necessary)
            self.status_bar.pop(0)
            # push the new message
            try:
                self.status_bar.push(0, message)
            except TypeError:
                new_message = re.sub("[^\w\s]", "", message)
                self.status_bar.push(0, new_message)
            # highlight the "warning" icon for warnings/errors
            if record and record.levelno > 20:
                self.gui.get_object("StatusBarWarning").show()

    @gui_activity_guard
    def copy_log_to_clipboard(self, widget=None):
        content = []
        def copy_row(model, path, it, content):
            columns = []
            for column in range(model.get_n_columns()):
                columns.append(model.get_value(it, column))
            content.append(" ".join(columns))
        self.log_model.foreach(copy_row, content)
        self.clipboard.set_text(os.linesep.join(content))
        self.gui.get_object("StatusBarWarning").hide()

    @gui_activity_guard
    def clear_log_window(self, widget=None):
        self.log_model.clear()
        self.gui.get_object("StatusBarWarning").hide()

    @gui_activity_guard
    def toggle_log_window(self, widget=None, value=None, action=None):
        toggle_log_checkbox = self.gui.get_object("ToggleLogWindow")
        checkbox_state = toggle_log_checkbox.get_active()
        if value is None:
            new_state = checkbox_state
        elif isinstance(value, gtk.gdk.Event):
            # someone clicked at the status bar -> toggle the window state
            new_state = not checkbox_state
        else:
            if action is None:
                new_state = value
            else:
                new_state = action
        if new_state:
            if self._log_window_position:
                self.log_window.move(*self._log_window_position)
            self.log_window.show()
        else:
            self._log_window_position = self.log_window.get_position()
            self.log_window.hide()
        toggle_log_checkbox.set_active(new_state)
        self.gui.get_object("StatusBarWarning").hide()
        # don't destroy the window with a "destroy" event
        return True

    @gui_activity_guard
    def toggle_process_pool_window(self, widget=None, value=None, action=None):
        toggle_process_pool_checkbox = self.gui.get_object("ToggleProcessPoolWindow")
        checkbox_state = toggle_process_pool_checkbox.get_active()
        if value is None:
            new_state = checkbox_state
        else:
            if action is None:
                new_state = value
            else:
                new_state = action
        if new_state:
            is_available = pycam.Utils.threading.is_pool_available()
            disabled_box = self.gui.get_object("ProcessPoolDisabledBox")
            statistics_box = self.gui.get_object("ProcessPoolStatisticsBox")
            if is_available:
                disabled_box.hide()
                statistics_box.show()
                # start the refresh function
                interval = int(max(1, self.gui.get_object(
                        "ProcessPoolRefreshInterval").get_value()))
                gobject.timeout_add_seconds(interval,
                        self.update_process_pool_statistics, interval)
            else:
                disabled_box.show()
                statistics_box.hide()
            self.process_pool_window.show()
        else:
            self.process_pool_window.hide()
        toggle_process_pool_checkbox.set_active(new_state)
        # don't destroy the window with a "destroy" event
        return True

    def update_process_pool_statistics(self, original_interval):
        stats = pycam.Utils.threading.get_pool_statistics()
        model = self.process_pool_model
        model.clear()
        for item in stats:
            model.append(item)
        self.gui.get_object("ProcessPoolConnectedWorkersValue").set_text(
                str(len(stats)))
        details = pycam.Utils.threading.get_task_statistics()
        detail_text = os.linesep.join(["%s: %s" % (key, value)
                for (key, value) in details.iteritems()])
        self.gui.get_object("ProcessPoolDetails").set_text(detail_text)
        current_interval = int(max(1, self.gui.get_object(
                "ProcessPoolRefreshInterval").get_value()))
        if original_interval != current_interval:
            # initiate a new repetition
            gobject.timeout_add_seconds(current_interval,
                    self.update_process_pool_statistics, current_interval)
            # stop the current repetition
            return False
        else:
            # don't repeat, if the window is hidden
            return self.gui.get_object("ToggleProcessPoolWindow").get_active()

    @gui_activity_guard
    def toggle_3d_view(self, widget=None, value=None):
        toggle_3d_checkbox = self.gui.get_object("Toggle3DView")
        # no interactive mode
        if self.no_dialog:
            return
        if self.view3d and not self.view3d.enabled:
            # initialization failed - don't do anything
            return
        if not self.model:
            # no model loaded - don't enable the window
            return
        current_state = not ((self.view3d is None) or (not self.view3d.is_visible))
        if value is None:
            new_state = not current_state
        else:
            new_state = value
        if new_state == current_state:
            return
        elif new_state:
            if self.view3d is None:
                # These buttons are replicated to appear in the 3D view - for
                # easier configuration of visible items without the Preferences
                # window.
                item_buttons = self.gui.get_object(
                        "PreferencesVisibleItemsBox").get_children()
                # do the gl initialization
                self.view3d = ModelViewWindowGL(self.gui, self.settings,
                        notify_destroy=self.toggle_3d_view,
                        accel_group=self._accel_group,
                        item_buttons=item_buttons,
                        context_menu_actions=[self.gui.get_object(name)
                                for name in ("GeneralSettings", "Help3DView")])
                if self.model and self.view3d.enabled:
                    self.view3d.reset_view()
                # configure drag-and-drop for the 3D window
                self.configure_drag_and_drop(self.view3d.window)
                # disable the "toggle" button, if the 3D view does not work
                toggle_3d_checkbox.set_sensitive(self.view3d.enabled)
            else:
                # the window is just hidden
                self.view3d.show()
            self.update_view()
        else:
            self.view3d.hide()
        # enable the toggle button only, if the 3d view is available
        # (e.g. disabled if no OpenGL support is available)
        toggle_3d_checkbox.set_active(self.view3d.enabled and new_state)

    @progress_activity_guard
    @gui_activity_guard
    def transform_model(self, widget):
        if widget is self.gui.get_object("Rotate"):
            controls = (("x-axis", "x"), ("y-axis", "y"), ("z-axis", "z"))
        elif widget is self.gui.get_object("Flip"):
            controls = (("xy-plane", "xy"), ("xz-plane", "xz"), ("yz-plane", "yz"))
        elif widget is self.gui.get_object("Swap"):
            controls = (("x <-> y", "x_swap_y"), ("x <-> z", "x_swap_z"), ("y <-> z", "y_swap_z"))
        else:
            # broken gui
            log.warn("Unknown button action: %s" % str(widget.get_name()))
            return
        for obj, value in controls:
            if self.gui.get_object(obj).get_active():
                self._store_undo_state()
                self.disable_progress_cancel_button()
                self.update_progress_bar("Transforming model")
                self.model.transform_by_template(value,
                        callback=self.update_progress_bar)
        self.append_to_queue(self.update_support_model)
        self.append_to_queue(self.update_model_dimensions)
        self.append_to_queue(self.update_view)

    def _treeview_get_active_index(self, table, datalist):
        if len(datalist) == 0:
            result = None
        else:
            treeselection = table.get_selection()
            (model, iteration) = treeselection.get_selected()
            # the first item in the model is the index within the list
            try:
                result = model[iteration][0]
            except TypeError:
                result = None
        return result

    def _treeview_set_active_index(self, table, index):
        treeselection = table.get_selection()
        treeselection.select_path((index,))

    def _treeview_button_event(self, table, datalist, action, update_func):
        future_selection_index = None
        index = self._treeview_get_active_index(table, datalist)
        skip_model_update = False
        if action == "update_buttons":
            skip_model_update = True
        elif action == "move_up":
            if index > 0:
                # move an item one position up the list
                selected = datalist[index]
                above = datalist[index-1]
                datalist[index] = above
                datalist[index-1] = selected
                future_selection_index = index - 1
        elif action == "move_down":
            if index + 1 < len(datalist):
                # move an item one position down the list
                selected = datalist[index]
                below = datalist[index+1]
                datalist[index] = below
                datalist[index+1] = selected
                future_selection_index = index + 1
        elif action == "delete":
            # delete one item from the list
            item = datalist[index]
            # Check if we need to remove items that depended on the currently
            # deleted one.
            if not datalist in (self.tool_list, self.process_list,
                    self.bounds_list):
                # tasks do not depend on this list - just continue
                pass
            elif len(datalist) == 1:
                # There are no replacements available for this item.
                # Thus we need to remove _all_ tasks.
                while len(self.task_list) > 0:
                    self.task_list.remove(self.task_list[0])
            else:
                if index > 0:
                    alternative = datalist[0]
                else:
                    alternative = datalist[1]
                # Replace all references to the to-be-deleted item with the
                # alternative.
                for task in self.task_list:
                    for sublist in ("tool", "process", "bounds"):
                        if item is task[sublist]:
                            task[sublist] = alternative
            # Delete the object. Maybe this is not necessary, if it was the
            # last remaining task item (see above).
            if item in datalist:
                datalist.remove(item)
            # don't set a new index, if the list is empty now
            if len(datalist) > 0:
                if index < len(datalist):
                    future_selection_index = index
                else:
                    # the last item was removed
                    future_selection_index = len(datalist) - 1
            # update the tasklist table (maybe we removed some items)
            self.update_tasklist_table()
            # also update the specific description of the tool/process/bounds
            if not future_selection_index is None:
                if datalist is self.tool_list:
                    self.settings.set("current_tool",
                            self.tool_list[future_selection_index])
                    self.switch_tool_table_selection()
                elif datalist is self.process_list:
                    self.settings.set("current_process",
                            self.process_list[future_selection_index])
                    self.switch_process_table_selection()
                elif datalist is self.bounds_list:
                    self.settings.set("current_bounds",
                            self.bounds_list[future_selection_index])
                    self.switch_bounds_table_selection()
        else:
            pass
        # any new item can influence the "New task" button
        self.append_to_queue(self.update_tasklist_controls)
        # removing or adding "bounds" may change the visualization
        self.append_to_queue(self.update_boundary_limits)
        update_func(new_index=future_selection_index,
                skip_model_update=skip_model_update)

    def _put_tool_settings_to_gui(self, settings):
        self.gui.get_object("ToolName").set_text(settings["name"])
        # cutter shapes
        def set_cutter_shape_name(value):
            self.gui.get_object(value).set_active(True)
        set_cutter_shape_name(settings["shape"])
        for objname, key in (
                ("FeedrateControl", "feedrate"),
                ("SpindleSpeedControl", "speed")):
            self.gui.get_object(objname).set_value(settings[key])
        # radius -> diameter
        for objname, key in (
                ("ToolDiameterControl", "tool_radius"),
                ("TorusDiameterControl", "torus_radius")):
            self.gui.get_object(objname).set_value(2 * settings[key])

    def _load_tool_settings_from_gui(self, settings=None):
        if settings is None:
            settings = {}
        settings["name"] = self.gui.get_object("ToolName").get_text()
        def get_cutter_shape_name():
            for name in ("SphericalCutter", "CylindricalCutter", "ToroidalCutter"):
                if self.gui.get_object(name).get_active():
                    return name
        settings["shape"] = get_cutter_shape_name()
        for objname, key in (
                ("FeedrateControl", "feedrate"),
                ("SpindleSpeedControl", "speed")):
            settings[key] = self.gui.get_object(objname).get_value()
        # diameter -> radius
        for objname, key in (
                ("ToolDiameterControl", "tool_radius"),
                ("TorusDiameterControl", "torus_radius")):
            settings[key] = 0.5 * self.gui.get_object(objname).get_value()
        return settings

    @gui_activity_guard
    def handle_tool_settings_change(self, widget=None, data=None):
        current_tool = self.settings.get("current_tool")
        if not current_tool is None:
            self._load_tool_settings_from_gui(current_tool)
            self.update_tool_table()
        self.update_tool_controls()

    @gui_activity_guard
    def switch_tool_table_selection(self, widget=None, data=None):
        current_tool = self.settings.get("current_tool")
        # hide all controls if no process is defined
        if not current_tool is None:
            self.gui.get_object("ToolSettingsControlsBox").show()
            self._put_tool_settings_to_gui(current_tool)
            self.update_tool_table()
        else:
            self.gui.get_object("ToolSettingsControlsBox").hide()
        
    @gui_activity_guard
    def _tool_editor_button_event(self, widget, data, action=None):
        # "toggle" uses two parameters - all other actions have only one
        if action is None:
            action = data
        self._treeview_button_event(self.tool_editor_table, self.tool_list, action, self.update_tool_table)
        if action == "add":
            # look for the first unused default name
            prefix = "New Tool "
            index = 1
            # loop while the current name is in use
            while [True for process in self.tool_list if process["name"] == "%s%d" % (prefix, index)]:
                index += 1
            new_settings = self._load_tool_settings_from_gui()
            new_settings["name"] = "%s%d" % (prefix, index)
            self.tool_list.append(new_settings)
            self.update_tool_table(self.tool_list.index(new_settings))
            self._put_tool_settings_to_gui(new_settings)
        elif action == "delete":
            self.append_to_queue(self.switch_tool_table_selection)

    def update_tool_table(self, new_index=None, skip_model_update=False):
        tool_model = self.gui.get_object("ToolList")
        if new_index is None:
            # keep the old selection - this may return "None" if nothing is selected
            new_index = self._treeview_get_active_index(self.tool_editor_table, self.tool_list)
        if not skip_model_update:
            tool_model.clear()
            counter = 0
            for tool in self.tool_list:
                # add the tool size to the descriptive text
                description = "%s (d=%s)" % (tool["name"], 2 * tool["tool_radius"])
                tool_model.append((counter, counter + 1, description))
                counter += 1
            if not new_index is None:
                self._treeview_set_active_index(self.tool_editor_table, new_index)
        # en/disable some buttons
        selection_active = not new_index is None
        self.gui.get_object("ToolListDelete").set_sensitive(selection_active)
        self.gui.get_object("ToolListMoveUp").set_sensitive(selection_active and new_index > 0)
        self.gui.get_object("ToolListMoveDown").set_sensitive(selection_active and new_index < len(self.tool_list) - 1)
        # hide all controls if no process is defined
        if new_index is None:
            self.gui.get_object("ToolSettingsControlsBox").hide()
        else:
            self.gui.get_object("ToolSettingsControlsBox").show()
        # remove any broken tasks and update changed names
        self.update_tool_controls()
        self.update_task_description()

    def change_unit_init(self, widget=None):
        new_unit = self.gui.get_object("unit_control").get_active_text()
        if self._last_unit is None:
            # first initialization
            self._last_unit = new_unit
            return
        if self._last_unit == new_unit:
            # don't show the dialog if the conversion would make no sense
            return
        if self.no_dialog:
            # without the dialog we don't scale anything
            return
        # show a dialog asking for a possible model scaling due to the unit change
        self.unit_change_window.show()

    def change_unit_set_selection(self, widget, state):
        for key in ("UnitChangeModel", "UnitChangeProcesses", "UnitChangeTools",
                "UnitChangeBounds"):
            self.gui.get_object(key).set_active(state)

    def change_unit_apply(self, widget=None, data=None, apply_scale=True):
        if self.no_dialog:
            # without the dialog we don't scale anything
            return
        new_unit = self.gui.get_object("unit_control").get_active_text()
        factors = {
                ("mm", "inch"): 1 / 25.4,
                ("inch", "mm"): 25.4,
        }
        conversion = (self._last_unit, new_unit)
        if conversion in factors.keys():
            factor = factors[conversion]
            if apply_scale:
                if self.gui.get_object("UnitChangeModel").get_active():
                    # transform the model if it is selected
                    # keep the original center of the model
                    old_center = self._get_model_center()
                    self._store_undo_state()
                    self.model.scale(factor)
                    self._set_model_center(old_center)
                if self.gui.get_object("UnitChangeProcesses").get_active():
                    # scale the process settings
                    for process in self.process_list:
                        for key in ("material_allowance", "step_down",
                                "engrave_offset"):
                            process[key] *= factor
                if self.gui.get_object("UnitChangeBounds").get_active():
                    # scale the boundaries and keep their center
                    for bounds in self.bounds_list:
                        low, high = bounds.get_bounds()
                        if bounds.get_type() == Bounds.TYPE_FIXED_MARGIN:
                            low[0] *= factor
                            high[0] *= factor
                            low[1] *= factor
                            high[1] *= factor
                            low[2] *= factor
                            high[2] *= factor
                            bounds.set_bounds(low, high)
                        elif bounds.get_type() == Bounds.TYPE_CUSTOM:
                            center = [0, 0, 0]
                            for i in range(3):
                                center[i] = (high[i] + low[i]) / 2
                            for i in range(3):
                                low[i] = center[i] + (low[i] - center[i]) * factor
                                high[i] = center[i] + (high[i] - center[i]) * factor
                            bounds.set_bounds(low, high)
                        elif bounds.get_type() == Bounds.TYPE_RELATIVE_MARGIN:
                            # no need to change relative margins
                            pass
                if self.gui.get_object("UnitChangeTools").get_active():
                    # scale all tool dimensions
                    for tool in self.tool_list:
                        for key in ("tool_radius", "torus_radius"):
                            tool[key] *= factor
        self.unit_change_window.hide()
        # store the current unit (for the next run of this function)
        self._last_unit = new_unit
        # update all labels containing the unit size
        self.update_unit_labels()
        # update all controls and redraw the boundaries
        self.switch_tool_table_selection()
        self.switch_process_table_selection()
        self.switch_bounds_table_selection()
        self.switch_tasklist_table_selection()
        # redraw the model
        self.update_view()

    def update_unit_labels(self, widget=None, data=None):
        # don't use the "unit" setting, since we need the plural of "inch"
        if self.settings.get("unit") == "mm":
            base_unit = "mm"
        else:
            base_unit = "inches"
        for key in ("SpeedUnit1", "SpeedUnit2"):
            self.gui.get_object(key).set_text("%s/minute" % base_unit)
        for key in ("LengthUnit1", "LengthUnit2", "LengthUnitTouchOffHeight"):
            self.gui.get_object(key).set_text(base_unit)

    def get_filename_with_suffix(self, filename, type_filter):
        # use the first extension provided by the filter as the default
        if isinstance(type_filter[0], (tuple, list)):
            filter_ext = type_filter[0][1]
        else:
            filter_ext = type_filter[1]
        if isinstance(filter_ext, (list, tuple)):
            filter_ext = filter_ext[0]
        if not filter_ext.startswith("*"):
            # weird filter content
            return filename
        else:
            filter_ext = filter_ext[1:]
        basename = os.path.basename(filename)
        if (basename.rfind(".") == -1) or (basename[-6:].rfind(".") == -1):
            # The filename does not contain a dot or the dot is not within the
            # last five characters. Dots within the start of the filename are
            # ignored.
            return filename + filter_ext
        else:
            # contains at least one dot
            return filename

    @gui_activity_guard
    def save_model(self, widget=None, filename=None, model=None,
            store_filename=True):
        if model is None:
            model = self.model
        if not model.is_export_supported():
            log.warn(("Saving this type of model (%s) is currently not " \
                    + "implemented!") % str(type(model)))
            return
        # get the filename
        if callable(filename):
            filename = filename()
        uri = None
        if not isinstance(filename, (basestring, pycam.Utils.URIHandler)):
            # we open a dialog
            # determine the file type
            # TODO: this needs to be decided by the exporter code
            if isinstance(model, pycam.Geometry.Model.Model):
                # TODO: fix this extremely fragile filter
                type_filter = [(name, patterns)
                        for name, patterns in FILTER_MODEL
                        if "STL" in name.upper()]
            elif isinstance(model, pycam.Geometry.Model.ContourModel):
                type_filter = [(name, patterns)
                        for name, patterns in FILTER_MODEL
                        if "SVG" in name.upper()]
            filename = self.get_filename_via_dialog("Save model to ...",
                    mode_load=False, type_filter=type_filter,
                    filename_templates=(self.last_model_uri,))
            if filename:
                uri = pycam.Utils.URIHandler(filename)
                if uri.is_local() and store_filename:
                    self.set_model_filename(filename)
        else:
            uri = pycam.Utils.URIHandler(filename)
        # no filename given -> exit
        if not uri:
            return
        if not uri.is_local():
            log.error("Unable to write file to a non-local " + \
                    "destination: %s" % uri)
        else:
            try:
                file_in = open(uri.get_local_path(), "w")
                model.export(comment=self.get_meta_data(),
                        unit=self.settings.get("unit")).write(file_in)
                file_in.close()
            except IOError, err_msg:
                log.error("Failed to save model file: %s" % err_msg)
            else:
                log.info("Successfully stored the current model as '%s'." % \
                        str(filename))
                self.update_save_actions()
                self.add_to_recent_file_list(filename)

    @gui_activity_guard
    def reset_preferences(self, widget=None):
        """ reset all preferences to their default values """
        for key, value in PREFERENCES_DEFAULTS.items():
            self.settings.set(key, value)
        # redraw the model due to changed colors, display items ...
        self.update_view()

    def load_preferences(self):
        """ load all settings that are available in the Preferences window from
        a file in the user's home directory """
        config_filename = pycam.Gui.Settings.get_config_filename()
        if config_filename is None:
            # failed to create the personal preferences directory
            return
        config = ConfigParser.ConfigParser()
        if not config.read(config_filename):
            # no config file was read
            return
        # report any ignored (obsolete) preference keys present in the file
        for item, value in config.items("DEFAULT"):
            if not item in PREFERENCES_DEFAULTS.keys():
                log.warn("Skipping obsolete preference item: %s" % str(item))
        for item in PREFERENCES_DEFAULTS.keys():
            if not config.has_option("DEFAULT", item):
                # a new preference setting is missing in the (old) file
                continue
            value_raw = config.get("DEFAULT", item)
            old_value = self.settings.get(item)
            value_type = type(PREFERENCES_DEFAULTS[item])
            if isinstance(value_type(), basestring):
                # keep strings as they are
                value = str(value_raw)
            else:
                # parse tuples, integers, bools, ...
                value = eval(value_raw)
            self.settings.set(item, value)

    def save_preferences(self):
        """ save all settings that are available in the Preferences window to
        a file in the user's home directory """
        config_filename = pycam.Gui.Settings.get_config_filename()
        if config_filename is None:
            # failed to create the personal preferences directory
            log.warn("Failed to create a preferences directory in " \
                    + "your user's home directory.")
            return
        config = ConfigParser.ConfigParser()
        for item in PREFERENCES_DEFAULTS.keys():
            config.set("DEFAULT", item, self.settings.get(item))
        try:
            config_file = file(config_filename, "w")
            config.write(config_file)
            config_file.close()
        except IOError, err_msg:
            log.warn("Failed to write preferences file (%s): %s" % (config_filename, err_msg))

    @progress_activity_guard
    @gui_activity_guard
    def shift_model(self, widget, use_form_values=True):
        if use_form_values:
            shift_x = self.gui.get_object("shift_x").get_value()
            shift_y = self.gui.get_object("shift_y").get_value()
            shift_z = self.gui.get_object("shift_z").get_value()
        else:
            shift_x = -self.model.minx
            shift_y = -self.model.miny
            shift_z = -self.model.minz
        self._store_undo_state()
        self.update_progress_bar("Shifting model")
        self.disable_progress_cancel_button()
        self.model.shift(shift_x, shift_y, shift_z,
                callback=self.update_progress_bar)
        self.append_to_queue(self.update_support_model)
        self.append_to_queue(self.update_model_dimensions)
        self.append_to_queue(self.update_view)

    def _get_model_center(self):
        if not self.model:
            return None
        else:
            return ((self.model.maxx + self.model.minx) / 2,
                    (self.model.maxy + self.model.miny) / 2,
                    (self.model.maxz + self.model.minz) / 2)

    def _set_model_center(self, center):
        new_x, new_y, new_z = center
        old_x, old_y, old_z = self._get_model_center()
        self.update_progress_bar("Centering model")
        # undo state should be stored in the caller function
        self.model.shift(new_x - old_x, new_y - old_y, new_z - old_z,
                callback=self.update_progress_bar)


    def _get_projection_plane(self):
        # determine projection plane
        if (self.model.maxz < 0) or (self.model.minz > 0):
            # completely above or below zero
            plane_z = self.model.minz
        else:
            plane_z = 0
        return Plane(Point(0, 0, plane_z), Vector(0, 0, 1))

    @progress_activity_guard
    @gui_activity_guard
    def projection_2d(self, widget=None):
        self.update_progress_bar("Calculating 2D projection")
        plane = self._get_projection_plane()
        log.info("Projecting current model at level z=%g" % plane.p.z)
        if hasattr(self.model, "get_flat_projection"):
            projection = self.model.get_flat_projection(plane)
        else:
            projection = self.model.get_waterline_contour(plane)
        if projection:
            self.load_model(projection)
        else:
            log.warn("The 2D projection at z=%g is empty. Aborted." % plane.p.z)

    @progress_activity_guard
    @gui_activity_guard
    def scale_model(self, widget=None, percent=None, keep_center=True):
        if percent is None:
            percent = self.gui.get_object("ScalePercent").get_value()
        factor = percent / 100.0
        if (factor <= 0) or (factor == 1):
            return
        old_center = self._get_model_center()
        self._store_undo_state()
        self.update_progress_bar("Scaling model")
        self.disable_progress_cancel_button()
        self.model.scale(factor, callback=self.update_progress_bar)
        if keep_center:
            self._set_model_center(old_center)
        self.append_to_queue(self.update_model_dimensions)
        self.append_to_queue(self.update_support_model)
        self.append_to_queue(self.update_view)

    @gui_activity_guard
    def update_model_dimensions(self, widget=None):
        if not self.model:
            return
        # scale controls
        axis_control = self.gui.get_object("ScaleDimensionAxis")
        scale_button = self.gui.get_object("ScaleDimensionButton")
        scale_value = self.gui.get_object("ScaleDimensionControl")
        index = axis_control.get_active()
        dims = (self.model.maxx - self.model.minx,
                self.model.maxy - self.model.miny,
                self.model.maxz - self.model.minz)
        value = dims[index]
        non_zero_dimensions = [i for i, dim in enumerate(dims) if dim > 0]
        enable_controls = index in non_zero_dimensions
        scale_button.set_sensitive(enable_controls)
        scale_value.set_sensitive(enable_controls)
        scale_value.set_value(value)
        # model corners in 3D view
        for attr, label_suffix in (("minx", "XMin"), ("miny", "YMin"),
                ("minz", "ZMin"), ("maxx", "XMax"), ("maxy", "YMax"),
                ("maxz", "ZMax")):
            label_name = "ModelCorner%s" % label_suffix
            value = "%.3f" % getattr(self.model, attr)
            self.gui.get_object(label_name).set_label(value)

    @progress_activity_guard
    @gui_activity_guard
    def guess_model_directions(self, widget=None):
        if not (self.model and hasattr(self.model, "reverse_directions")):
            return
        self._store_undo_state()
        self.update_progress_bar(text="Analyzing directions of contour model")
        self.model.revise_directions(callback=self.update_progress_bar)
        self.update_support_model()

    @progress_activity_guard
    @gui_activity_guard
    def reverse_model_direction(self, widget=None):
        if not (self.model and hasattr(self.model, "reverse_directions")):
            return
        self._store_undo_state()
        self.update_progress_bar(text="Reversing directions of contour model")
        self.model.reverse_directions(callback=self.update_progress_bar)
        self.update_support_model()

    @progress_activity_guard
    @gui_activity_guard
    def scale_model_axis_fit(self, widget=None):
        proportionally = self.gui.get_object("ScaleDimensionsProportionally").get_active()
        value = self.gui.get_object("ScaleDimensionValue").get_value()
        index = self.gui.get_object("ScaleDimensionAxis").get_active()
        axes = "xyz"
        axis_suffix = axes[index]
        factor = value / (getattr(self.model, "max" + axis_suffix) - getattr(self.model, "min" + axis_suffix))
        # store the original center of the model
        old_center = self._get_model_center()
        self._store_undo_state()
        self.update_progress_bar("Scaling model")
        self.disable_progress_cancel_button()
        if proportionally:
            self.model.scale(factor, callback=self.update_progress_bar)
        else:
            factor_x, factor_y, factor_z = (1, 1, 1)
            if index == 0:
                factor_x = factor
            elif index == 1:
                factor_y = factor
            elif index == 2:
                factor_z = factor
            else:
                return
            self.model.scale(factor_x, factor_y, factor_z,
                    callback=self.update_progress_bar)
        # move the model to its previous center
        self._set_model_center(old_center)
        self.append_to_queue(self.update_support_model)
        self.append_to_queue(self.update_model_dimensions)
        self.append_to_queue(self.update_view)

    def destroy(self, widget=None, data=None):
        self.update_view()
        # check if there is a running process
        # BEWARE: this is useless without threading - but we keep it for now
        if self._progress_running:
            self.cancel_progress()
            # wait steps
            delay = 0.5
            # timeout in seconds
            timeout = 5
            # wait until if is finished
            while self._progress_running and (timeout > 0):
                time.sleep(delay)
                timeout -= delay
        gtk.main_quit()
        self.quit()

    def quit(self):
        self.save_preferences()

    def configure_drag_and_drop(self, obj):
        obj.connect("drag-data-received", self.handle_data_drop)
        flags = gtk.DEST_DEFAULT_ALL
        targets = [(key, gtk.TARGET_OTHER_APP, index)
                for index, key in enumerate(CLIPBOARD_TARGETS["filename_drag"])]
        actions = gtk.gdk.ACTION_COPY | gtk.gdk.ACTION_LINK | \
                gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_PRIVATE | \
                gtk.gdk.ACTION_ASK
        obj.drag_dest_set(flags, targets, actions)

    def handle_data_drop(self, widget, drag_context, x, y, selection_data, info,
            timestamp):
        if info != 0:
            uris = [str(selection_data.data)]
        elif pycam.Utils.get_platform() == pycam.Utils.PLATFORM_WINDOWS:
            uris = selection_data.data.splitlines()
        else:
            uris = selection_data.get_uris()
        if not uris:
            # empty selection
            return True
        for uri in uris:
            if not uri or (uri == chr(0)):
                continue
            uri = pycam.Utils.URIHandler(uri)
            file_type, importer = pycam.Importers.detect_file_type(uri,
                    quiet=True)
            if importer:
                # looks like the file can be loaded
                if self.load_model_file(filename=uri):
                    return True
        if len(uris) > 1:
            log.error("Failed to open any of the given models: %s" % \
                    str(uris))
        else:
            log.error("Failed to open the model: %s" % str(uris[0]))
        return False

    def append_to_queue(self, func, *args, **kwargs):
        # check if gui is currently active
        if self.gui_is_active:
            # queue the function call
            self._batch_queue.append((func, args, kwargs))
        else:
            # call the function right now
            func(*args, **kwargs)

    def load_recent_model_file(self, widget):
        uri = widget.get_current_uri()
        self.load_model_file(filename=uri)

    def _get_program_locations(self):
        # import all external program locations into a dict
        program_locations = {}
        prefix = "external_program_"
        for key in self.settings.get_keys():
            if key.startswith(prefix) and self.settings.get(key):
                program_locations[key[len(prefix):]] = self.settings.get(key)
        return program_locations

    @gui_activity_guard
    @progress_activity_guard
    def load_model_file(self, widget=None, filename=None, store_filename=True):
        if callable(filename):
            filename = filename()
        if not filename:
            filename = self.get_filename_via_dialog("Loading model ...",
                    mode_load=True, type_filter=FILTER_MODEL)
        if filename:
            file_type, importer = pycam.Importers.detect_file_type(filename)
            if file_type and callable(importer):
                self.update_progress_bar(text="Loading model ...")
                # "cancel" is not allowed
                self.disable_progress_cancel_button()
                if self.load_model(importer(filename,
                        program_locations=self._get_program_locations(),
                        unit=self.settings.get("unit"),
                        fonts_cache=self._fonts_cache,
                        callback=self.update_progress_bar)):
                    if store_filename:
                        self.set_model_filename(filename)
                    self.add_to_recent_file_list(filename)
                    return True
                else:
                    return False
            else:
                log.error("Failed to detect filetype!")
                return False

    @gui_activity_guard
    def export_emc_tools(self, widget=None, filename=None):
        if callable(filename):
            filename = filename()
        if not filename:
            filename = self.get_filename_via_dialog("Exporting EMC tool definition ...",
                    mode_load=False, type_filter=FILTER_EMC_TOOL,
                    filename_templates=(self.last_model_uri,))
        if filename:
            export = pycam.Exporters.EMCToolExporter.EMCToolExporter(self.tool_list)
            text = export.get_tool_definition_string()
            try:
                out = file(filename, "w")
                out.write(text)
                out.close()
            except IOError, err_msg:
                log.error("Failed to save EMC tool file: %s" % err_msg)
            else:
                self.add_to_recent_file_list(filename)

    def finish_startup(self):
        """ This function is called by the pycam script after everything is
        set up properly.
        """
        # empty the "undo" states (accumulated by loading the defualt model)
        while self._undo_states:
            self._undo_states.pop(0)

    def open_task_settings_file(self, filename):
        """ This function is used by the commandline handler """
        self.last_task_settings_uri = pycam.Utils.URIHandler(filename)
        self.load_task_settings_file(filename=filename)
        self.update_save_actions()

    @gui_activity_guard
    def load_task_settings_file(self, widget=None, filename=None):
        if callable(filename):
            filename = filename()
        if not filename:
            filename = self.get_filename_via_dialog("Loading settings ...",
                    mode_load=True, type_filter=FILTER_CONFIG)
            # Only update the last_task_settings attribute if the task file was
            # loaded interactively. E.g. ignore the initial task file loading.
            if filename:
                self.last_task_settings_uri = pycam.Utils.URIHandler(filename)
        if filename:
            log.info("Loading task settings file: %s" % str(filename))
            self.load_task_settings(filename)
            self.add_to_recent_file_list(filename)
        self.update_save_actions()

    def _update_all_model_attributes(self):
        self.append_to_queue(self.update_model_dimensions)
        self.append_to_queue(self.update_model_type_related_controls)
        self.append_to_queue(self.update_save_actions)
        self.append_to_queue(self.update_support_controls)
        self.append_to_queue(self.toggle_3d_view, value=True)
        self.append_to_queue(self.update_view)

    def load_model(self, model):
        # load the new model only if the import worked
        if model:
            self._store_undo_state()
            self.model = model
            self.last_model_uri = None
            # do some initialization
            self._update_all_model_attributes()
            if self.model and self.view3d and self.view3d.enabled:
                self.append_to_queue(self.view3d.reset_view)
            return True
        else:
            return False

    def load_task_settings(self, filename=None):
        settings = pycam.Gui.Settings.ProcessSettings()
        if not filename is None:
            settings.load_file(filename)
        # flush all tables (without re-assigning new objects)
        for one_list in (self.tool_list, self.process_list, self.bounds_list, self.task_list):
            while len(one_list) > 0:
                one_list.pop()
        self.tool_list.extend(settings.get_tools())
        self.process_list.extend(settings.get_processes())
        self.bounds_list.extend(settings.get_bounds())
        self.task_list.extend(settings.get_tasks())
        self.update_tool_table()
        self.update_process_table()
        self.update_bounds_table()
        self.update_tasklist_table()

    def _put_bounds_settings_to_gui(self, settings):
        self.gui.get_object("BoundsName").set_text(settings.get_name())
        self.gui.get_object(self.BOUNDARY_TYPES[settings.get_type()]).set_active(True)
        low, high = settings.get_bounds()
        # relative margins are given in percent
        if settings.get_type() == Bounds.TYPE_RELATIVE_MARGIN:
            factor = 100
        else:
            factor = 1
        for index, axis in enumerate("xyz"):
            self.gui.get_object("boundary_%s_low" % axis).set_value(low[index] * factor)
            self.gui.get_object("boundary_%s_high" % axis).set_value(high[index] * factor)

    def _load_bounds_settings_from_gui(self, settings=None):
        def get_boundary_type_from_gui():
            for key, objname in self.BOUNDARY_TYPES.items():
                if self.gui.get_object(objname).get_active():
                    return key
        if settings is None:
            settings = pycam.Toolpath.Bounds()
        settings.set_name(self.gui.get_object("BoundsName").get_text())
        settings.set_type(get_boundary_type_from_gui())
        low = [None] * 3
        high = [None] * 3
        # relative margins are given in percent
        if settings.get_type() == Bounds.TYPE_RELATIVE_MARGIN:
            factor = 0.01
        else:
            factor = 1
        for index, axis in enumerate("xyz"):
            low[index] = self.gui.get_object(
                    "boundary_%s_low" % axis).get_value() * factor
            high[index] = self.gui.get_object(
                    "boundary_%s_high" % axis).get_value() * factor
        settings.set_bounds(low, high)
        return settings

    @gui_activity_guard
    def handle_bounds_settings_change(self, widget=None, data=None):
        current_index = self._treeview_get_active_index(
                self.bounds_editor_table, self.bounds_list)
        if not current_index is None:
            self._load_bounds_settings_from_gui(self.bounds_list[current_index])
            self.update_bounds_table()
        self.append_to_queue(self.update_boundary_limits)

    def update_bounds_controls(self):
        current_index = self._treeview_get_active_index(
                self.bounds_editor_table, self.bounds_list)
        if current_index is None:
            # no bounds setting is active
            return
        # show the proper descriptive label for the current margin type
        current_settings = self._load_bounds_settings_from_gui()
        current_type = current_settings.get_type()
        type_labels = {
                Bounds.TYPE_RELATIVE_MARGIN: "BoundsMarginTypeRelativeLabel",
                Bounds.TYPE_FIXED_MARGIN: "BoundsMarginTypeFixedLabel",
                Bounds.TYPE_CUSTOM: "BoundsMarginTypeCustomLabel",
        }
        for type_key, label_name in type_labels.items():
            is_active = type_key == current_type
            if is_active:
                self.gui.get_object(label_name).show()
            else:
                self.gui.get_object(label_name).hide()
        # return the control for one of the axes (low/high)
        def get_control(index, side):
            return self.gui.get_object("boundary_%s_%s" % ("xyz"[index], side))
        # disable each zero-dimension in relative margin mode
        if current_type == Bounds.TYPE_RELATIVE_MARGIN:
            model_dims = (self.model.maxx - self.model.minx,
                    self.model.maxy - self.model.miny,
                    self.model.maxz - self.model.minz)
            # disable the low/high controls for each zero-dimension
            for index in range(3):
                # enabled, if dimension is non-zero
                state = model_dims[index] != 0
                get_control(index, "high").set_sensitive(state)
                if (index == 2) and isinstance(self.model,
                        pycam.Geometry.Model.ContourModel):
                    # disable lower z for contour models
                    state = False
                get_control(index, "low").set_sensitive(state)
        else:
            # non-relative margins: enable all controls
            for index in range(3):
                get_control(index, "high").set_sensitive(True)
                if (index == 2) and isinstance(self.model,
                        pycam.Geometry.Model.ContourModel) and \
                        (current_type != Bounds.TYPE_CUSTOM):
                    # disable lower z for contour models
                    state = False
                else:
                    state = True
                get_control(index, "low").set_sensitive(state)

    def update_bounds_table(self, new_index=None, skip_model_update=False):
        # reset the model data and the selection
        if new_index is None:
            # keep the old selection - this may return "None" if nothing is selected
            new_index = self._treeview_get_active_index(self.bounds_editor_table, self.bounds_list)
        if not skip_model_update:
            # update the TreeModel data
            model = self.gui.get_object("BoundsList")
            model.clear()
            # columns: index, description
            for index, bounds in enumerate(self.bounds_list):
                items = (index, bounds.get_name())
                model.append(items)
            if not new_index is None:
                self._treeview_set_active_index(self.bounds_editor_table, new_index)
        selection_active = not new_index is None
        # enable/disable the modification buttons
        self.gui.get_object("BoundsListMoveUp").set_sensitive(selection_active \
                and (new_index > 0))
        self.gui.get_object("BoundsListDelete").set_sensitive(selection_active)
        self.gui.get_object("BoundsListMoveDown").set_sensitive(
                selection_active and (new_index + 1 < len(self.bounds_list)))
        # hide all controls if no bound is defined
        if selection_active:
            self.gui.get_object("BoundsSettingsControlsBox").show()
        else:
            self.gui.get_object("BoundsSettingsControlsBox").hide()
        self.update_bounds_controls()
        # remove any broken tasks and update changed names
        self.update_task_description()

    @gui_activity_guard
    def switch_bounds_table_selection(self, widget=None, data=None):
        bounds = self.settings.get("current_bounds")
        if not bounds is None:
            self.gui.get_object("BoundsSettingsControlsBox").show()
            self._put_bounds_settings_to_gui(bounds)
            self.update_bounds_table()
        else:
            self.gui.get_object("BoundsSettingsControlsBox").hide()
        self.append_to_queue(self.update_boundary_limits)

    @gui_activity_guard
    def handle_bounds_table_event(self, widget, data, action=None):
        # "toggle" uses two parameters - all other actions have only one
        if action is None:
            action = data
        self._treeview_button_event(self.bounds_editor_table, self.bounds_list,
                action, self.update_bounds_table)
        # do some post-processing ...
        if action == "add":
            # look for the first unused default name
            prefix = "New Bounds "
            index = 1
            # loop while the current name is in use
            while [True for bounds in self.bounds_list
                    if bounds.get_name() == "%s%d" % (prefix, index)]:
                index += 1
            new_settings = self._load_bounds_settings_from_gui()
            new_settings.set_name("%s%d" % (prefix, index))
            self.bounds_list.append(new_settings)
            self.update_bounds_table(self.bounds_list.index(new_settings))
            self._put_bounds_settings_to_gui(new_settings)
        elif action == "delete":
            self.append_to_queue(self.switch_bounds_table_selection)

    def _load_process_settings_from_gui(self, settings=None):
        if settings is None:
            settings = {}
        settings["name"] = self.gui.get_object("ProcessSettingName").get_text()
        # path generator
        for key in ("PushRemoveStrategy", "ContourPolygonStrategy",
                "ContourFollowStrategy", "SurfaceStrategy", "EngraveStrategy"):
            if self.gui.get_object(key).get_active():
                strategy = key
                break
        settings["path_strategy"] = strategy
        # path direction
        for obj, value in (("GridDirectionX", "x"), ("GridDirectionY", "y"),
                ("GridDirectionXY", "xy")):
            if self.gui.get_object(obj).get_active():
                direction = value
                break
        # milling style
        for obj, value in (("MillingStyleConventional", "conventional"),
                ("MillingStyleClimb", "climb"),
                ("MillingStyleIgnore", "ignore")):
            if self.gui.get_object(obj).get_active():
                milling_style = value
                break
        # post_processor and reverse
        settings["milling_style"] = milling_style
        settings["path_direction"] = direction
        for objname, key in (("OverlapPercentControl", "overlap_percent"),
                ("MaterialAllowanceControl", "material_allowance"),
                ("MaxStepDownControl", "step_down"),
                ("EngraveOffsetControl", "engrave_offset")):
            settings[key] = self.gui.get_object(objname).get_value()
        settings["pocketing_type"] = POCKETING_TYPES[
                self.gui.get_object("PocketingControl").get_active()]
        return settings

    def _put_process_settings_to_gui(self, settings):
        self.gui.get_object("ProcessSettingName").set_text(settings["name"])
        # path direction
        def set_path_direction(direction):
            for obj, value in (("GridDirectionX", "x"), ("GridDirectionY", "y"),
                    ("GridDirectionXY", "xy")):
                if value == direction:
                    self.gui.get_object(obj).set_active(True)
                    return
        set_path_direction(settings["path_direction"])
        def set_path_strategy(value):
            self.gui.get_object(value).set_active(True)
        set_path_strategy(settings["path_strategy"])
        # milling style
        def set_milling_style(style):
            STYLES = {"conventional": "MillingStyleConventional",
                    "climb": "MillingStyleClimb",
                    "ignore": "MillingStyleIgnore"}
            self.gui.get_object(STYLES[style]).set_active(True)
        set_milling_style(settings["milling_style"])
        for objname, key in (("OverlapPercentControl", "overlap_percent"),
                ("MaterialAllowanceControl", "material_allowance"),
                ("MaxStepDownControl", "step_down"),
                ("EngraveOffsetControl", "engrave_offset")):
            self.gui.get_object(objname).set_value(settings[key])
        if settings["pocketing_type"] in POCKETING_TYPES:
            self.gui.get_object("PocketingControl").set_active(
                    POCKETING_TYPES.index(settings["pocketing_type"]))

    @gui_activity_guard
    def handle_process_settings_change(self, widget=None, data=None):
        current_process = self.settings.get("current_process")
        if not current_process is None:
            self._load_process_settings_from_gui(current_process)
            self.update_process_table()

    def update_process_table(self, new_index=None, skip_model_update=False):
        # reset the model data and the selection
        if new_index is None:
            # keep the old selection - this may return "None" if nothing is selected
            new_index = self._treeview_get_active_index(self.process_editor_table, self.process_list)
        if not skip_model_update:
            # update the TreeModel data
            model = self.gui.get_object("ProcessList")
            model.clear()
            # columns: index, description
            for index in range(len(self.process_list)):
                process = self.process_list[index]
                items = (index, process["name"])
                model.append(items)
            if not new_index is None:
                self._treeview_set_active_index(self.process_editor_table, new_index)
        # enable/disable the modification buttons
        self.gui.get_object("ProcessListMoveUp").set_sensitive((not new_index is None) and (new_index > 0))
        self.gui.get_object("ProcessListDelete").set_sensitive(not new_index is None)
        self.gui.get_object("ProcessListMoveDown").set_sensitive((not new_index is None) and (new_index + 1 < len(self.process_list)))
        # hide all controls if no process is defined
        if new_index is None:
            self.gui.get_object("ProcessSettingsControlsBox").hide()
        else:
            self.gui.get_object("ProcessSettingsControlsBox").show()
        # remove any broken tasks and update changed names
        self.update_task_description()

    @gui_activity_guard
    def switch_process_table_selection(self, widget=None, data=None):
        current_process = self.settings.get("current_process")
        if not current_process is None:
            self.gui.get_object("ProcessSettingsControlsBox").show()
            self._put_process_settings_to_gui(current_process)
            self.update_process_table()
        else:
            self.gui.get_object("ProcessSettingsControlsBox").hide()
        
    @gui_activity_guard
    def handle_process_table_event(self, widget, data, action=None):
        # "toggle" uses two parameters - all other actions have only one
        if action is None:
            action = data
        self._treeview_button_event(self.process_editor_table, self.process_list, action, self.update_process_table)
        # do some post-processing ...
        if action == "add":
            # look for the first unused default name
            prefix = "New Process "
            index = 1
            # loop while the current name is in use
            while [True for process in self.process_list if process["name"] == "%s%d" % (prefix, index)]:
                index += 1
            new_settings = self._load_process_settings_from_gui()
            new_settings["name"] = "%s%d" % (prefix, index)
            self.process_list.append(new_settings)
            self.update_process_table(self.process_list.index(new_settings))
            self._put_process_settings_to_gui(new_settings)
        elif action == "delete":
            self.append_to_queue(self.switch_process_table_selection)

    @gui_activity_guard
    def toolpath_table_event(self, widget, data, action=None):
        # "toggle" uses two parameters - all other actions have only one
        if action is None:
            action = data
        if action == "toggle_visibility":
            # get the id of the currently selected toolpath
            try:
                path = int(data)
            except ValueError:
                path = None
            if (not path is None) and (path < len(self.toolpath)):
                self.toolpath[path].visible = not self.toolpath[path].visible
                tp_model = self.toolpath_table.get_model()
                tp_model[path][2] = self.toolpath[path].visible
                self.update_toolpath_related_controls()
        elif action == "simulate":
            index = self._treeview_get_active_index(self.toolpath_table,
                    self.toolpath)
            if not index is None:
                self.show_toolpath_simulation(self.toolpath[index])
        elif action == "crop":
            index = self._treeview_get_active_index(self.toolpath_table,
                    self.toolpath)
            if not index is None:
                self.crop_toolpath(self.toolpath[index])
                self.update_toolpath_table()
        elif action == "grid":
            index = self._treeview_get_active_index(self.toolpath_table,
                    self.toolpath)
            if not index is None:
                self.create_toolpath_grid(self.toolpath[index])
        else:
            # process the default operations (move, delete)
            self._treeview_button_event(self.toolpath_table, self.toolpath,
                    action, self.update_toolpath_table)
        # do some post-processing ...
        if action in ("toggle_visibility", "delete", "crop", "grid"):
            self.update_view()

    def update_toolpath_grid_window(self, widget=None):
        data = self._toolpath_for_grid_data
        x_dim = data["maxx"] - data["minx"]
        y_dim = data["maxy"] - data["miny"]
        x_count = self.gui.get_object("GridXCount").get_value()
        x_space = self.gui.get_object("GridXDistance").get_value()
        y_count = self.gui.get_object("GridYCount").get_value()
        y_space = self.gui.get_object("GridYDistance").get_value()
        x_width = x_dim * x_count + x_space * (x_count - 1)
        y_width = y_dim * y_count + y_space * (y_count - 1)
        self.gui.get_object("LabelGridXWidth").set_label("%g%s" % \
                (x_width, self.settings.get("unit")))
        self.gui.get_object("LabelGridYWidth").set_label("%g%s" % \
                (y_width, self.settings.get("unit")))

    def create_toolpath_grid(self, toolpath):
        dialog = self.gui.get_object("ToolpathGridDialog")
        data = self._toolpath_for_grid_data
        data["minx"] = toolpath.minx()
        data["maxx"] = toolpath.maxx()
        data["miny"] = toolpath.miny()
        data["maxy"] = toolpath.maxy()
        self.gui.get_object("GridXCount").set_value(1)
        self.gui.get_object("GridYCount").set_value(1)
        self.update_toolpath_grid_window()
        result = dialog.run()
        if result == 1:
            # "OK" was pressed
            new_tp = []
            x_count = int(self.gui.get_object("GridXCount").get_value())
            y_count = int(self.gui.get_object("GridYCount").get_value())
            x_space = self.gui.get_object("GridXDistance").get_value()
            y_space = self.gui.get_object("GridYDistance").get_value()
            x_dim = data["maxx"] - data["minx"]
            y_dim = data["maxy"] - data["miny"]
            for x in range(x_count):
                for y in range(y_count):
                    shift = Point(x * (x_space + x_dim),
                            y * (y_space + y_dim), 0)
                    for path in toolpath.get_paths():
                        new_path = pycam.Geometry.Path.Path()
                        new_path.points = [shift.add(p) for p in path.points]
                        new_tp.append(new_path)
            new_toolpath = pycam.Toolpath.Toolpath(new_tp, toolpath.name,
                    toolpath.toolpath_settings)
            toolpath.visible = False
            new_toolpath.visible = True
            self.toolpath.append(new_toolpath)
            self.update_toolpath_table()
        dialog.hide()

    @progress_activity_guard
    def crop_toolpath(self, toolpath):
        if hasattr(self.model, "get_polygons"):
            contour = self.model
        elif hasattr(self.model, "get_waterline_contour"):
            plane = self._get_projection_plane()
            self.update_progress_bar("Calculating the 2D projection")
            contour = self.model.get_waterline_contour(plane)
            self.update_progress_bar("Applying the tool diameter offset")
            contour = contour.get_offset_model(
                    2 * toolpath.get_tool_settings()["tool_radius"])
        else:
            log.warn(("The current model (%s) does not support " \
                    + "projections") % str(type(self.model)))
            return
        self.update_progress_bar("Cropping the toolpath")
        toolpath.crop(contour.get_polygons(), callback=self.update_progress_bar)

    def update_toolpath_related_controls(self):
        # show or hide the "toolpath" tab
        toolpath_tab = self.gui.get_object("ToolPathTab")
        if not self.toolpath:
            toolpath_tab.hide()
        else:
            self.gui.get_object("ToolPathTabLabel").set_text(
                    "%s (%d)" % (self._original_toolpath_tab_label, len(self.toolpath)))
            toolpath_tab.show()
        # enable/disable the export menu item
        self.gui.get_object("ExportGCodeAll").set_sensitive(len(self.toolpath) > 0)
        toolpaths_are_visible = any([tp.visible for tp in self.toolpath])
        self.gui.get_object("ExportGCodeVisible").set_sensitive(
                toolpaths_are_visible)
        self.gui.get_object("ExportVisibleToolpathsButton").set_sensitive(
                toolpaths_are_visible)

    def update_toolpath_table(self, new_index=None, skip_model_update=False):
        def get_time_string(minutes):
            if minutes > 180:
                return "%d hours" % int(round(minutes / 60))
            elif minutes > 3:
                return "%d minutes" % int(round(minutes))
            else:
                return "%d seconds" % int(round(minutes * 60))
        self.update_toolpath_related_controls()
        # reset the model data and the selection
        if new_index is None:
            # keep the old selection - this may return "None" if nothing is selected
            new_index = self._treeview_get_active_index(self.toolpath_table, self.toolpath)
        if not skip_model_update:
            # update the TreeModel data
            model = self.gui.get_object("ToolPathListModel")
            model.clear()
            # columns: name, visible, drill_size, drill_id, allowance, speed, feedrate
            for index in range(len(self.toolpath)):
                tp = self.toolpath[index]
                toolpath_settings = tp.get_toolpath_settings()
                tool = toolpath_settings.get_tool_settings()
                process = toolpath_settings.get_process_settings()
                items = (index, tp.name, tp.visible, tool["tool_radius"],
                        tool["id"], process["material_allowance"],
                        tool["speed"], tool["feedrate"],
                        get_time_string(tp.get_machine_time(
                                self.settings.get("gcode_safety_height"))))
                model.append(items)
            if not new_index is None:
                self._treeview_set_active_index(self.toolpath_table, new_index)
        # enable/disable the modification buttons
        self.gui.get_object("toolpath_up").set_sensitive((not new_index is None) and (new_index > 0))
        self.gui.get_object("toolpath_delete").set_sensitive(not new_index is None)
        self.gui.get_object("toolpath_down").set_sensitive((not new_index is None) and (new_index + 1 < len(self.toolpath)))
        self.gui.get_object("toolpath_simulate").set_sensitive(not new_index is None)
        self.gui.get_object("toolpath_crop").set_sensitive(not new_index is None)
        self.gui.get_object("ToolpathGrid").set_sensitive(not new_index is None)

    @gui_activity_guard
    def save_task_settings_file(self, widget=None, filename=None):
        if callable(filename):
            filename = filename()
        if not isinstance(filename, (basestring, pycam.Utils.URIHandler)):
            # we open a dialog
            filename = self.get_filename_via_dialog("Save settings to ...",
                    mode_load=False, type_filter=FILTER_CONFIG,
                    filename_templates=(self.last_task_settings_uri, self.last_model_uri))
            if filename:
                self.last_task_settings_uri = pycam.Utils.URIHandler(filename)
                self.update_save_actions()
        # no filename given -> exit
        if not filename:
            return
        settings = pycam.Gui.Settings.ProcessSettings()
        if not settings.write_to_file(filename, self.tool_list,
                self.process_list, self.bounds_list, self.task_list):
            log.error("Failed to save settings file")
        else:
            log.info("Task settings written to %s" % filename)
            self.add_to_recent_file_list(filename)
        self.update_save_actions()

    def toggle_progress_bar(self, status):
        # always hide the progress button - it will be enabled later
        self.show_progress_button.hide()
        if status:
            self.menubar.set_sensitive(False)
            self.task_pane.set_sensitive(False)
            self._progress_start_time = time.time()
            self.update_progress_bar(text="", percent=0)
            self.progress_cancel_button.set_sensitive(True)
            # enable "pulse" mode for a start (in case of unknown ETA)
            self.progress_bar.pulse()
            self.progress_widget.show()
        else:
            self.progress_widget.hide()
            self.task_pane.set_sensitive(True)
            self.menubar.set_sensitive(True)

    def disable_progress_cancel_button(self):
        """ mainly useful for non-interruptable operations (e.g. model
        transformations)
        """
        self.progress_cancel_button.set_sensitive(False)

    def update_progress_bar(self, text=None, percent=None):
        if not percent is None:
            percent = min(max(percent, 0.0), 100.0)
            self.progress_bar.set_fraction(percent/100.0)
        if (not percent) and (self.progress_bar.get_fraction() == 0):
            # use "pulse" mode until we reach 1% of the work to be done
            self.progress_bar.pulse()
        # update the GUI
        current_time = time.time()
        # Don't update the GUI more often than once per second.
        # Exception: text-only updates
        # This restriction improves performance and reduces the
        # "snappiness" of the GUI.
        if (self._last_gtk_events_time is None) \
                or text \
                or (self._last_gtk_events_time + 1 <= current_time):
            # "estimated time of arrival" text
            time_estimation_suffix = " remaining ..."
            if self.progress_bar.get_fraction() > 0:
                eta_full = (time.time() - self._progress_start_time) / self.progress_bar.get_fraction()
                if eta_full > 0:
                    eta_delta = eta_full - (time.time() - self._progress_start_time)
                    eta_delta = int(round(eta_delta))
                    if hasattr(self, "_last_eta_delta"):
                        previous_eta_delta = self._last_eta_delta
                        if eta_delta == previous_eta_delta + 1:
                            # We are currently toggling between two numbers.
                            # We want to avoid screen flicker, thus we just live
                            # with the slight inaccuracy.
                            eta_delta = self._last_eta_delta
                    self._last_eta_delta = eta_delta
                    eta_delta_obj = datetime.timedelta(seconds=eta_delta)
                    eta_text = "%s%s" % (eta_delta_obj, time_estimation_suffix)
                else:
                    eta_text = None
            else:
                eta_text = None
            if not text is None:
                lines = [text]
            else:
                old_lines = self.progress_bar.get_text().split(os.linesep)
                # skip the time estimation line
                lines = [line for line in old_lines
                        if not line.endswith(time_estimation_suffix)]
            if eta_text:
                lines.append(eta_text)
            self.progress_bar.set_text(os.linesep.join(lines))
            # show the "show_tool_button" ("hide" is called in the progress decorator)
            if self.settings.get("toolpath_in_progress"):
                self.show_progress_button.show()
            while gtk.events_pending():
                gtk.main_iteration()
            if not text or (self._progress_start_time + 5 < current_time):
                # We don't store the timining if the text was changed.
                # This is especially nice for the snappines during font
                # initialization. This exception is only valid for the first
                # five seconds of the operation.
                self._last_gtk_events_time = current_time
        # return if the user requested a break
        return self._progress_cancel_requested

    def cancel_progress(self, widget=None):
        self._progress_cancel_requested = True

    def finish_toolpath_simulation(self, widget=None, data=None):
        # hide the simulation tab
        self.simulation_window.hide()
        # enable all other tabs again
        self.toggle_tabs_for_simulation(True)
        self.settings.set("simulation_object", None)
        self.settings.set("simulation_toolpath_moves", None)
        self.settings.set("show_simulation", False)
        self.settings.set("simulation_toolpath", None)
        self.update_view()
        # don't destroy the simulation window (for "destroy" event)
        return True

    def update_toolpath_simulation(self, widget=None, toolpath=None):
        s = self.settings
        # update the GUI
        while gtk.events_pending():
            gtk.main_iteration()
        if not s.get("show_simulation"):
            # cancel
            return False
        safety_height = s.get("gcode_safety_height")
        if not s.get("simulation_toolpath"):
            # get the currently selected toolpath, if none is give
            if toolpath is None:
                toolpath_index = self._treeview_get_active_index(self.toolpath_table, self.toolpath)
                if toolpath_index is None:
                    return
                else:
                    toolpath = self.toolpath[toolpath_index]
            s.set("simulation_toolpath", toolpath)
            # set the current cutter
            self.cutter = toolpath.toolpath_settings.get_tool()
            # calculate steps
            s.set("simulation_machine_time",
                    toolpath.get_machine_time(safety_height=safety_height))
            s.set("simulation_complete_distance",
                    toolpath.get_machine_movement_distance(
                        safety_height=safety_height))
            s.set("simulation_current_distance", 0)
        else:
            toolpath = s.get("simulation_toolpath")
        if (s.get("simulation_current_distance") \
                < s.get("simulation_complete_distance")):
            if s.get("simulation_current_distance") < 0:
                # "-1" -> simulation is finished
                updated_distance = s.get("simulation_complete_distance")
            else:
                time_step = 1.0 / s.get("drill_progress_max_fps")
                feedrate = toolpath.toolpath_settings.get_tool_settings(
                        )["feedrate"]
                distance_step = s.get("simulation_speed_factor") * \
                        time_step * feedrate / 60
                updated_distance = min(distance_step + \
                        s.get("simulation_current_distance"),
                        s.get("simulation_complete_distance"))
            if updated_distance != s.get("simulation_current_distance"):
                s.set("simulation_current_distance", updated_distance)
                moves = toolpath.get_moves(safety_height=safety_height,
                        max_movement=updated_distance)
                s.set("simulation_toolpath_moves", moves)
                if moves:
                    self.cutter.moveto(moves[-1][0])
                self.update_view()
        progress_value_percent = 100.0 * s.get("simulation_current_distance") \
                / s.get("simulation_complete_distance")
        self.gui.get_object("SimulationProgressTimelineValue").set_value(
                progress_value_percent)
        return True

    @progress_activity_guard
    def update_toolpath_simulation_ode(self, widget=None, toolpath=None):
        import pycam.Simulation.ODEBlocks as ODEBlocks
        # get the currently selected toolpath, if none is give
        if toolpath is None:
            toolpath_index = self._treeview_get_active_index(self.toolpath_table, self.toolpath)
            if toolpath_index is None:
                return
            else:
                toolpath = self.toolpath[toolpath_index]
        paths = toolpath.get_paths()
        # set the current cutter
        self.cutter = pycam.Cutters.get_tool_from_settings(
                toolpath.get_tool_settings())
        # calculate steps
        detail_level = self.gui.get_object("SimulationDetailsValue").get_value()
        grid_size = 100 * pow(2, detail_level - 1)
        bounding_box = toolpath.get_toolpath_settings().get_bounds()
        (minx, miny, minz), (maxx, maxy, maxz) = bounding_box.get_bounds()
        # proportion = dimension_x / dimension_y
        proportion = (maxx - minx) / (maxy - miny)
        x_steps = int(sqrt(grid_size) * proportion)
        y_steps = int(sqrt(grid_size) / proportion)
        simulation_backend = ODEBlocks.ODEBlocks(toolpath.get_tool_settings(),
                toolpath.get_bounding_box(), x_steps=x_steps, y_steps=y_steps)
        self.settings.set("simulation_object", simulation_backend)
        # disable the simulation widget (avoids confusion regarding "cancel")
        if not widget is None:
            self.gui.get_object("SimulationTab").set_sensitive(False)
        # update the view
        self.update_view()
        # calculate the simulation and show it simulteneously
        for path_index, path in enumerate(paths):
            progress_text = "Simulating path %d/%d" % (path_index, len(paths))
            progress_value_percent = 100.0 * path_index / len(paths)
            if self.update_progress_bar(progress_text, progress_value_percent):
                # break if the user pressed the "cancel" button
                break
            for index in range(len(path.points)):
                self.cutter.moveto(path.points[index])
                if index != 0:
                    start = path.points[index - 1]
                    end = path.points[index]
                    if start != end:
                        simulation_backend.process_cutter_movement(start, end)
                self.update_view()
                # break the loop if someone clicked the "cancel" button
                if self.update_progress_bar():
                    break
        # enable the simulation widget again (if we were started from the GUI)
        if not widget is None:
            self.gui.get_object("SimulationTab").set_sensitive(True)

    def toggle_tabs_for_simulation(self, new_state):
        for objname in ("ModelTab", "ModelTabLabel", "TasksTab",
                "TasksTabLabel", "ToolPathTab", "ToolPathTabLabel", "ToolTab",
                "ToolTabLabel", "ProcessTab", "ProcessTabLabel", "BoundsTab",
                "BoundsTabLabel"):
            self.gui.get_object(objname).set_sensitive(new_state)

    def show_toolpath_simulation(self, toolpath=None):
        # disable the main controls
        self.toggle_tabs_for_simulation(False)
        # show the simulation controls
        self.simulation_window.show()
        # start the simulation
        self.settings.set("show_simulation", True)
        time_step = int(1000 / self.settings.get("drill_progress_max_fps"))
        # update the toolpath simulation repeatedly
        gobject.timeout_add(time_step, self.update_toolpath_simulation)

    @progress_activity_guard
    def generate_toolpath(self, tool_settings, process_settings, bounds):
        start_time = time.time()
        self.update_progress_bar("Preparing toolpath generation")
        parent = self
        class UpdateView:
            def __init__(self, func, max_fps=1):
                self.last_update = time.time()
                self.max_fps = max_fps
                self.func = func
            def update(self, text=None, percent=None, tool_position=None,
                    toolpath=None):
                if parent.settings.get("show_drill_progress"):
                    if not tool_position is None:
                        parent.cutter.moveto(tool_position)
                    if not toolpath is None:
                        parent.settings.set("toolpath_in_progress", toolpath)
                    current_time = time.time()
                    if (current_time - self.last_update) > 1.0/self.max_fps:
                        self.last_update = current_time
                        if self.func:
                            self.func()
                # break the loop if someone clicked the "cancel" button
                return parent.update_progress_bar(text, percent)
        draw_callback = UpdateView(self.update_view,
                max_fps=self.settings.get("drill_progress_max_fps")).update

        self.update_progress_bar("Generating collision model")

        # turn the toolpath settings into a dict
        toolpath_settings = self.get_toolpath_settings(tool_settings,
                process_settings, bounds)
        if toolpath_settings is None:
            # behave as if "cancel" was requested
            return True

        self.cutter = toolpath_settings.get_tool()

        # run the toolpath generation
        self.update_progress_bar("Starting the toolpath generation")
        try:
            toolpath = pycam.Toolpath.Generator.generate_toolpath_from_settings(
                    self.model, toolpath_settings, callback=draw_callback)
        except Exception:
            # catch all non-system-exiting exceptions
            report_exception()
            return False

        log.info("Toolpath generation time: %f" % (time.time() - start_time))
        # don't show the new toolpath anymore
        self.settings.set("toolpath_in_progress", None)

        if toolpath is None:
            # user interruption
            # return "False" if the action was cancelled
            return not self.update_progress_bar()
        elif isinstance(toolpath, basestring):
            # an error occoured - "toolpath" contains the error message
            log.error("Failed to generate toolpath: %s" % toolpath)
            # we were not successful (similar to a "cancel" request)
            return False
        else:
            # hide the previous toolpath if it is the only visible one (automatic mode)
            if (len([True for path in self.toolpath if path.visible]) == 1) \
                    and self.toolpath[-1].visible:
                self.toolpath[-1].visible = False
            # add the new toolpath
            description = "%s / %s" % (tool_settings["name"],
                    process_settings["name"])
            # the tool id numbering should start with 1 instead of zero
            self.toolpath.add_toolpath(toolpath, description, toolpath_settings)
            self.update_toolpath_table()
            self.update_view()
            # return "False" if the action was cancelled
            return not self.update_progress_bar()

    def get_toolpath_settings(self, tool_settings, process_settings, bounds):
        toolpath_settings = pycam.Gui.Settings.ToolpathSettings()

        # this offset allows to cut a model with a minimal boundary box correctly
        offset = tool_settings["tool_radius"]
        # check the configured direction of the offset (boundary mode)
        if self.settings.get("boundary_mode") == self.BOUNDARY_MODES["inside"]:
            # use the negative offset to stay inside the boundaries
            offset *= -1
        elif self.settings.get("boundary_mode") == self.BOUNDARY_MODES["along"]:
            # don't use any offset
            offset = 0
        elif self.settings.get("boundary_mode") == self.BOUNDARY_MODES["around"]:
            # just use the positive offset - no change required
            pass
        else:
            # this should never happen
            log.error("Assertion failed: invalid boundary_mode (%s)" % str(self.settings.get("boundary_mode")))

        border = (offset, offset, 0)
        bounds.set_reference(self.model.get_bounds())
        processing_bounds = Bounds(Bounds.TYPE_FIXED_MARGIN, border, border,
                reference=bounds)

        # check if the boundary limits are valid
        if not processing_bounds.is_valid():
            # don't generate a toolpath if the area is too small (e.g. due to the tool size)
            log.error("Processing boundaries are too small for this tool size.")
            return None

        toolpath_settings.set_bounds(processing_bounds)

        # put the tool settings together
        tool_id = self.tool_list.index(tool_settings) + 1
        toolpath_settings.set_tool(tool_id, tool_settings["shape"],
                tool_settings["tool_radius"], tool_settings["torus_radius"],
                tool_settings["speed"], tool_settings["feedrate"])

        # get the support grid options
        grid_type = self.settings.get("support_grid_type")
        if grid_type == GRID_TYPES["grid"]:
            toolpath_settings.set_support_grid(
                    self.settings.get("support_grid_distance_x"),
                    self.settings.get("support_grid_distance_y"),
                    self.settings.get("support_grid_thickness"),
                    self.settings.get("support_grid_height"),
                    offset_x=self.settings.get("support_grid_offset_x"),
                    offset_y=self.settings.get("support_grid_offset_y"),
                    adjustments_x=self.grid_adjustments_x,
                    adjustments_y=self.grid_adjustments_y)
        elif grid_type in (GRID_TYPES["automatic_edge"],
                GRID_TYPES["automatic_corner"]):
            corner_start = (grid_type == GRID_TYPES["automatic_corner"])
            toolpath_settings.set_support_distributed(
                    self.settings.get("support_grid_average_distance"),
                    self.settings.get("support_grid_minimum_bridges"),
                    self.settings.get("support_grid_thickness"),
                    self.settings.get("support_grid_height"),
                    self.settings.get("support_grid_length"),
                    start_at_corners=corner_start)
        elif grid_type == GRID_TYPES["none"]:
            pass
        else:
            log.error("Invalid support grid type: %d" % grid_type)
        
        # calculation backend: ODE / None
        if self.settings.get("enable_ode"):
            toolpath_settings.set_calculation_backend("ODE")

        # unit size
        toolpath_settings.set_unit_size(self.settings.get("unit"))

        STRATEGY_GENERATORS = {
                "PushRemoveStrategy": ("PushCutter", "SimpleCutter"),
                "ContourPolygonStrategy": ("PushCutter", "ContourCutter"),
                "ContourFollowStrategy": ("ContourFollow", "SimpleCutter"),
                "SurfaceStrategy": ("DropCutter", "PathAccumulator"),
                "EngraveStrategy": ("EngraveCutter", "SimpleCutter")}
        generator, postprocessor = STRATEGY_GENERATORS[
                process_settings["path_strategy"]]

        # process settings
        toolpath_settings.set_process_settings(
                generator, postprocessor, process_settings["path_direction"],
                process_settings["material_allowance"],
                process_settings["overlap_percent"],
                process_settings["step_down"],
                process_settings["engrave_offset"],
                process_settings["milling_style"],
                process_settings["pocketing_type"])

        return toolpath_settings

    def get_filename_via_dialog(self, title, mode_load=False, type_filter=None,
            filename_templates=None, filename_extension=None, parent=None):
        if parent is None:
            parent = self.window
        # we open a dialog
        if mode_load:
            dialog = gtk.FileChooserDialog(title=title,
                    parent=parent, action=gtk.FILE_CHOOSER_ACTION_OPEN,
                    buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                        gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        else:
            dialog = gtk.FileChooserDialog(title=title,
                    parent=self.window, action=gtk.FILE_CHOOSER_ACTION_SAVE,
                    buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                        gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        # set the initial directory to the last one used
        if self.last_dirname and os.path.isdir(self.last_dirname):
            dialog.set_current_folder(self.last_dirname)
        # add filter for files
        if type_filter:
            for file_filter in get_filters_from_list(type_filter):
                dialog.add_filter(file_filter)
        # guess the export filename based on the model's filename
        valid_templates = []
        if filename_templates:
            for template in filename_templates:
                if not template:
                    continue
                elif hasattr(template, "get_path"):
                    valid_templates.append(template.get_path())
                else:
                    valid_templates.append(template)
        if valid_templates:
            filename_template = valid_templates[0]
            # remove the extension
            default_filename = os.path.splitext(filename_template)[0]
            if filename_extension:
                default_filename += os.path.extsep + filename_extension
            elif type_filter:
                for one_type in type_filter:
                    extension = one_type[1]
                    if isinstance(extension, (list, tuple, set)):
                        extension = extension[0]
                    # use only the extension of the type filter string
                    extension = os.path.splitext(extension)[1]
                    if extension:
                        default_filename += extension
                        # finish the loop
                        break
            dialog.select_filename(default_filename)
            try:
                dialog.set_current_name(
                        os.path.basename(default_filename).encode("utf-8"))
            except UnicodeError:
                # ignore
                pass
        # add filter for all files
        ext_filter = gtk.FileFilter()
        ext_filter.set_name("All files")
        ext_filter.add_pattern("*")
        dialog.add_filter(ext_filter)
        done = False
        while not done:
            dialog.set_filter(dialog.list_filters()[0])
            response = dialog.run()
            filename = dialog.get_filename()
            uri = pycam.Utils.URIHandler(filename)
            dialog.hide()
            if response != gtk.RESPONSE_OK:
                dialog.destroy()
                return None
            if not mode_load and filename:
                # check if we want to add a default suffix
                filename = self.get_filename_with_suffix(filename, type_filter)
            if not mode_load and os.path.exists(filename):
                overwrite_window = gtk.MessageDialog(self.window, type=gtk.MESSAGE_WARNING,
                        buttons=gtk.BUTTONS_YES_NO,
                        message_format="This file exists. Do you want to overwrite it?")
                overwrite_window.set_title("Confirm overwriting existing file")
                response = overwrite_window.run()
                overwrite_window.destroy()
                done = (response == gtk.RESPONSE_YES)
            elif mode_load and not uri.exists():
                not_found_window = gtk.MessageDialog(self.window, type=gtk.MESSAGE_ERROR,
                        buttons=gtk.BUTTONS_OK,
                        message_format="This file does not exist. Please choose a different filename.")
                not_found_window.set_title("Invalid filename selected")
                response = not_found_window.run()
                not_found_window.destroy()
                done = False
            else:
                done = True
        dialog.destroy()
        # add the file to the list of recently used ones
        if filename:
            self.add_to_recent_file_list(filename)
        return filename

    def add_to_recent_file_list(self, filename):
        # Add the item to the recent files list - if it already exists.
        # Otherwise it will be added later after writing the file.
        uri = pycam.Utils.URIHandler(filename)
        if uri.exists():
            # skip this, if the recent manager is not available (e.g. GTK 2.12.1 on Windows)
            if self.recent_manager:
                if self.recent_manager.has_item(uri.get_url()):
                    try:
                        self.recent_manager.remove_item(uri.get_url())
                    except gobject.GError:
                        pass
                self.recent_manager.add_item(uri.get_url())
            # store the directory of the last loaded file
            if uri.is_local():
                self.last_dirname = os.path.dirname(uri.get_local_path())

    @gui_activity_guard
    def save_toolpath(self, widget=None, only_visible=False):
        if not self.toolpath:
            return
        if callable(widget):
            widget = widget()
        if isinstance(widget, basestring):
            filename = widget
        else:
            # we open a dialog
            if self.settings.get("gcode_filename_extension"):
                filename_extension = self.settings.get("gcode_filename_extension")
            else:
                filename_extension = None
            filename = self.get_filename_via_dialog("Save toolpath to ...",
                    mode_load=False, type_filter=FILTER_GCODE,
                    filename_templates=(self.last_toolpath_file, self.last_model_uri),
                    filename_extension=filename_extension)
            if filename:
                self.last_toolpath_file = filename
        self.update_save_actions()
        # no filename given -> exit
        if not filename:
            return
        if self.settings.get("gcode_safety_height") < self.settings.get("maxz"):
            log.warn(("Safety height (%.4f) is below the top of the model " \
                    + "(%.4f) - this can cause collisions of the tool with " \
                    + "the material.") % (self.settings.get(
                    "gcode_safety_height"), self.settings.get("maxz")))
        try:
            if only_visible:
                export_toolpaths = [tp for tp in self.toolpath if tp.visible]
            else:
                export_toolpaths = self.toolpath
            destination = open(filename, "w")
            safety_height = self.settings.get("gcode_safety_height")
            meta_data = self.get_meta_data()
            machine_time = 0
            # calculate the machine time and store it in the GCode header
            for toolpath in export_toolpaths:
                machine_time += toolpath.get_machine_time(safety_height)
            all_info = meta_data + os.linesep \
                    + "Estimated machine time: %.0f minutes" % machine_time
            minimum_steps = [self.settings.get("gcode_minimum_step_x"),  
                    self.settings.get("gcode_minimum_step_y"),  
                    self.settings.get("gcode_minimum_step_z")]
            if self.settings.get("touch_off_position_type") == "absolute":
                pos_x = self.settings.get("touch_off_position_x")
                pos_y = self.settings.get("touch_off_position_y")
                pos_z = self.settings.get("touch_off_position_z")
                touch_off_pos = Point(pos_x, pos_y, pos_z)
            else:
                touch_off_pos = None
            generator = GCodeGenerator(destination,
                    metric_units=(self.settings.get("unit") == "mm"),
                    safety_height=safety_height,
                    toggle_spindle_status=self.settings.get("gcode_start_stop_spindle"),
                    spindle_delay=self.settings.get("gcode_spindle_delay"),
                    comment=all_info, minimum_steps=minimum_steps,
                    touch_off_on_startup=self.settings.get("touch_off_on_startup"),
                    touch_off_on_tool_change=self.settings.get("touch_off_on_tool_change"),
                    touch_off_position=touch_off_pos,
                    touch_off_rapid_move=self.settings.get("touch_off_rapid_move"),
                    touch_off_slow_move=self.settings.get("touch_off_slow_move"),
                    touch_off_slow_feedrate=self.settings.get("touch_off_slow_feedrate"),
                    touch_off_height=self.settings.get("touch_off_height"),
                    touch_off_pause_execution=self.settings.get("touch_off_pause_execution"))
            path_mode = self.settings.get("gcode_path_mode")
            if path_mode == 0:
                generator.set_path_mode(PATH_MODES["exact_path"])
            elif path_mode == 1:
                generator.set_path_mode(PATH_MODES["exact_stop"])
            elif path_mode == 2:
                generator.set_path_mode(PATH_MODES["continuous"])
            else:
                naive_tolerance = self.settings.get("gcode_naive_tolerance")
                if naive_tolerance == 0:
                    naive_tolerance = None
                generator.set_path_mode(PATH_MODES["continuous"],
                        self.settings.get("gcode_motion_tolerance"),
                        naive_tolerance)
            for toolpath in export_toolpaths:
                settings = toolpath.get_toolpath_settings()
                tool = settings.get_tool_settings()
                generator.set_speed(tool["feedrate"], tool["speed"])
                generator.add_moves(toolpath.get_moves(safety_height),
                        tool_id=tool["id"], comment=toolpath.get_meta_data())
            generator.finish()
            destination.close()
            log.info("GCode file successfully written: %s" % str(filename))
        except IOError, err_msg:
            log.error("Failed to save toolpath file: %s" % err_msg)
        else:
            self.add_to_recent_file_list(filename)

    def get_meta_data(self):
        filename = "Filename: %s" % str(self.last_model_uri)
        timestamp = "Timestamp: %s" % str(datetime.datetime.now())
        version = "Version: %s" % VERSION
        result = []
        for text in (filename, timestamp, version):
            result.append("%s %s" % (self.META_DATA_PREFIX, text))
        return os.linesep.join(result)

    def mainloop(self):
        # run the mainloop only if a GUI was requested
        if not self.no_dialog:
            gtk_settings = gtk.settings_get_default()
            # force the icons to be displayed
            gtk_settings.props.gtk_menu_images = True
            gtk_settings.props.gtk_button_images = True
            try:
                gtk.main()
            except KeyboardInterrupt:
                self.quit()

if __name__ == "__main__":
    GUI = ProjectGui()
    if len(sys.argv) > 1:
        GUI.load_model_file(sys.argv[1])
    GUI.mainloop()

