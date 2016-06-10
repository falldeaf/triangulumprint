# -*- coding: utf-8 -*-
"""
$Id: OpenGLTools.py 1023 2011-03-23 01:50:03Z sumpfralle $

Copyright 2010-2011 Lars Kruse <devel@sumpfralle.de>

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

# careful import - otherwise pycam.Gui.Project will throw an exception
try:
    import gtk.gtkgl
    import OpenGL.GL as GL
    import OpenGL.GLU as GLU
    import OpenGL.GLUT as GLUT
    GL_ENABLED = True
except (ImportError, RuntimeError):
    GL_ENABLED = False

from pycam.Geometry.Point import Point
import pycam.Geometry.Matrix as Matrix
from pycam.Geometry.utils import sqrt, number
import pycam.Utils.log
import gtk
import pango
import math

# buttons for rotating, moving and zooming the model view window
BUTTON_ROTATE = gtk.gdk.BUTTON1_MASK
BUTTON_MOVE = gtk.gdk.BUTTON2_MASK
BUTTON_ZOOM = gtk.gdk.BUTTON3_MASK
BUTTON_RIGHT = 3

# The length of the distance vector does not matter - it will be normalized and
# multiplied later anyway.
VIEWS = {
    "reset": {"distance": (-1.0, -1.0, 1.0), "center": (0.0, 0.0, 0.0),
            "up": (0.0, 0.0, 1.0), "znear": 0.1, "zfar": 1000.0, "fovy": 30.0},
    "top": {"distance": (0.0, 0.0, 1.0), "center": (0.0, 0.0, 0.0),
            "up": (0.0, 1.0, 0.0), "znear": 0.1, "zfar": 1000.0, "fovy": 30.0},
    "bottom": {"distance": (0.0, 0.0, -1.0), "center": (0.0, 0.0, 0.0),
            "up": (0.0, 1.0, 0.0), "znear": 0.1, "zfar": 1000.0, "fovy": 30.0},
    "left": {"distance": (-1.0, 0.0, 0.0), "center": (0.0, 0.0, 0.0),
            "up": (0.0, 0.0, 1.0), "znear": 0.1, "zfar": 1000.0, "fovy": 30.0},
    "right": {"distance": (1.0, 0.0, 0.0), "center": (0.0, 0.0, 0.0),
            "up": (0.0, 0.0, 1.0), "znear": 0.1, "zfar": 1000.0, "fovy": 30.0},
    "front": {"distance": (0.0, -1.0, 0.0), "center": (0.0, 0.0, 0.0),
            "up": (0.0, 0.0, 1.0), "znear": 0.1, "zfar": 1000.0, "fovy": 30.0},
    "back": {"distance": (0.0, 1.0, 0.0), "center": (0.0, 0.0, 0.0),
            "up": (0.0, 0.0, 1.0), "znear": 0.1, "zfar": 1000.0, "fovy": 30.0},
}


log = pycam.Utils.log.get_logger()


def connect_button_handlers(signal, original_button, derived_button):
    """ Join two buttons (probably "toggle" buttons) to keep their values
    synchronized.
    """
    def derived_handler(widget, original_button=original_button):
        original_button.set_active(not original_button.get_active())
    derived_handler_id = derived_button.connect_object_after(
            signal, derived_handler, derived_button)
    def original_handler(original_button, derived_button=derived_button,
            derived_handler_id=derived_handler_id):
        derived_button.handler_block(derived_handler_id)
        # prevent any recursive handler-triggering
        if derived_button.get_active() != original_button.get_active():
            derived_button.set_active(not derived_button.get_active())
        derived_button.handler_unblock(derived_handler_id)
    original_button.connect_object_after(signal, original_handler,
            original_button)


class Camera:

    def __init__(self, settings, get_dim_func, view=None):
        self.view = None
        self.settings = settings
        self._get_dim_func = get_dim_func
        self.set_view(view)

    def set_view(self, view=None):
        if view is None:
            self.view = VIEWS["reset"].copy()
        else:
            self.view = view.copy()
        self.center_view()
        self.auto_adjust_distance()

    def center_view(self):
        s = self.settings
        # center the view on the object
        self.view["center"] = ((s.get("maxx") + s.get("minx")) / 2,
                (s.get("maxy") + s.get("miny")) / 2,
                (s.get("maxz") + s.get("minz")) / 2)

    def auto_adjust_distance(self):
        s = self.settings
        v = self.view
        # adjust the distance to get a view of the whole object
        dimx = s.get("maxx") - s.get("minx")
        dimy = s.get("maxy") - s.get("miny")
        dimz = s.get("maxz") - s.get("minz")
        max_dim = max(max(dimx, dimy), dimz)
        distv = Point(v["distance"][0], v["distance"][1],
                v["distance"][2]).normalized()
        # The multiplier "1.25" is based on experiments. 1.414 (sqrt(2)) should
        # be roughly sufficient for showing the diagonal of any model.
        distv = distv.mul((max_dim * 1.25) / number(math.sin(v["fovy"] / 2)))
        self.view["distance"] = (distv.x, distv.y, distv.z)
        # Adjust the "far" distance for the camera to make sure, that huge
        # models (e.g. x=1000) are still visible.
        self.view["zfar"] = 100 * max_dim

    def scale_distance(self, scale):
        if scale != 0:
            scale = number(scale)
            dist = self.view["distance"]
            self.view["distance"] = (scale * dist[0], scale * dist[1],
                    scale * dist[2])

    def get(self, key, default=None):
        if (not self.view is None) and self.view.has_key(key):
            return self.view[key]
        else:
            return default

    def set(self, key, value):
        self.view[key] = value

    def move_camera_by_screen(self, x_move, y_move, max_model_shift):
        """ move the camera acoording to a mouse movement
        @type x_move: int
        @value x_move: movement of the mouse along the x axis
        @type y_move: int
        @value y_move: movement of the mouse along the y axis
        @type max_model_shift: float
        @value max_model_shift: maximum shifting of the model view (e.g. for
            x_move == screen width)
        """
        factors_x, factors_y = self._get_axes_vectors()
        width, height = self._get_screen_dimensions()
        # relation of x/y movement to the respective screen dimension
        win_x_rel = (-2 * x_move) / float(width) / math.sin(self.view["fovy"])
        win_y_rel = (-2 * y_move) / float(height) / math.sin(self.view["fovy"])
        # This code is completely arbitrarily based on trial-and-error for
        # finding a nice movement speed for all distances.
        # Anyone with a better approach should just fix this.
        distance_vector = self.get("distance")
        distance = float(sqrt(sum([dim ** 2 for dim in distance_vector])))
        win_x_rel *= math.cos(win_x_rel / distance) ** 20
        win_y_rel *= math.cos(win_y_rel / distance) ** 20
        # update the model position that should be centered on the screen
        old_center = self.view["center"]
        new_center = []
        for i in range(3):
            new_center.append(old_center[i] \
                    + max_model_shift * (number(win_x_rel) * factors_x[i] \
                    + number(win_y_rel) * factors_y[i]))
        self.view["center"] = tuple(new_center)

    def rotate_camera_by_screen(self, start_x, start_y, end_x, end_y):
        factors_x, factors_y = self._get_axes_vectors()
        width, height = self._get_screen_dimensions()
        # calculate rotation factors - based on the distance to the center
        # (between -1 and 1)
        rot_x_factor = (2.0 * start_x) / width - 1
        rot_y_factor = (2.0 * start_y) / height - 1
        # calculate rotation angles (between -90 and +90 degrees)
        xdiff = end_x - start_x
        ydiff = end_y - start_y
        # compensate inverse rotation left/right side (around x axis) and
        # top/bottom (around y axis)
        if rot_x_factor < 0:
            ydiff = -ydiff
        if rot_y_factor > 0:
            xdiff = -xdiff
        rot_x_angle = rot_x_factor * math.pi * ydiff / height
        rot_y_angle = rot_y_factor * math.pi * xdiff / width
        # rotate around the "up" vector with the y-axis rotation
        original_distance = self.view["distance"]
        original_up = self.view["up"]
        y_rot_matrix = Matrix.get_rotation_matrix_axis_angle(factors_y,
                rot_y_angle)
        new_distance = Matrix.multiply_vector_matrix(original_distance,
                y_rot_matrix)
        new_up = Matrix.multiply_vector_matrix(original_up, y_rot_matrix)
        # rotate around the cross vector with the x-axis rotation
        x_rot_matrix = Matrix.get_rotation_matrix_axis_angle(factors_x,
                rot_x_angle)
        new_distance = Matrix.multiply_vector_matrix(new_distance, x_rot_matrix)
        new_up = Matrix.multiply_vector_matrix(new_up, x_rot_matrix)
        self.view["distance"] = new_distance
        self.view["up"] = new_up

    def position_camera(self):
        width, height = self._get_screen_dimensions()
        prev_mode = GL.glGetIntegerv(GL.GL_MATRIX_MODE)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        v = self.view
        # position the light according to the current bounding box
        light_pos = range(3)
        model = self.settings.get("model")
        light_pos[0] = 2 * model.maxx - model.minx
        light_pos[1] = 2 * model.maxy - model.miny
        light_pos[2] = 2 * model.maxz - model.minz
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_POSITION, (light_pos[0], light_pos[1],
                light_pos[2], 1.0))
        # position the camera
        camera_position = (v["center"][0] + v["distance"][0],
                v["center"][1] + v["distance"][1],
                v["center"][2] + v["distance"][2])
        if self.settings.get("view_perspective"):
            # perspective view
            GLU.gluPerspective(v["fovy"], (0.0 + width) / height, v["znear"],
                    v["zfar"])
        else:
            # parallel projection
            # This distance calculation is completely based on trial-and-error.
            distance = math.sqrt(sum([d ** 2 for d in v["distance"]]))
            distance *= math.log(math.sqrt(width * height)) / math.log(10)
            sin_factor = math.sin(v["fovy"] / 360.0 * math.pi) * distance
            left = v["center"][0] - sin_factor
            right = v["center"][0] + sin_factor
            top = v["center"][1] + sin_factor
            bottom = v["center"][1] - sin_factor
            near = v["center"][2] - 2 * sin_factor
            far = v["center"][2] + 2 * sin_factor
            GL.glOrtho(left, right, bottom, top, near, far)
        GLU.gluLookAt(camera_position[0], camera_position[1],
                camera_position[2], v["center"][0], v["center"][1],
                v["center"][2], v["up"][0], v["up"][1], v["up"][2])
        GL.glMatrixMode(prev_mode)

    def shift_view(self, x_dist=0, y_dist=0):
        obj_dim = []
        obj_dim.append(self.settings.get("maxx") - self.settings.get("minx"))
        obj_dim.append(self.settings.get("maxy") - self.settings.get("miny"))
        obj_dim.append(self.settings.get("maxz") - self.settings.get("minz"))
        max_dim = max(obj_dim)
        factor = 50
        self.move_camera_by_screen(x_dist * factor, y_dist * factor, max_dim)

    def zoom_in(self):
        self.scale_distance(sqrt(0.5))

    def zoom_out(self):
        self.scale_distance(sqrt(2))

    def _get_screen_dimensions(self):
        return self._get_dim_func()

    def _get_axes_vectors(self):
        """calculate the model vectors along the screen's x and y axes"""
        # The "up" vector defines, in what proportion each axis of the model is
        # in line with the screen's y axis.
        v_up = self.view["up"]
        factors_y = (number(v_up[0]), number(v_up[1]), number(v_up[2]))
        # Calculate the proportion of each model axis according to the x axis of
        # the screen.
        distv = self.view["distance"]
        distv = Point(distv[0], distv[1], distv[2]).normalized()
        factors_x = distv.cross(Point(v_up[0], v_up[1], v_up[2])).normalized()
        factors_x = (factors_x.x, factors_x.y, factors_x.z)
        return (factors_x, factors_y)


class ModelViewWindowGL:
    def __init__(self, gui, settings, notify_destroy=None, accel_group=None,
            item_buttons=None, context_menu_actions=None):
        # assume, that initialization will fail
        self.gui = gui
        self.window = self.gui.get_object("view3dwindow")
        if not accel_group is None:
            self.window.add_accel_group(accel_group)
        self.initialized = False
        self.busy = False
        self.settings = settings
        self.is_visible = False
        # check if the 3D view is available
        if GL_ENABLED:
            self.enabled = True
        else:
            log.error("Failed to initialize the interactive 3D model view."
                    + "\nPlease install 'python-gtkglext1' to enable it.")
            self.enabled = False
            return
        self.mouse = {"start_pos": None, "button": None,
                "event_timestamp": 0, "last_timestamp": 0,
                "pressed_pos": None, "pressed_timestamp": 0,
                "pressed_button": None}
        self.notify_destroy_func = notify_destroy
        self.window.connect("delete-event", self.destroy)
        self.window.set_default_size(560, 400)
        self._position = self.gui.get_object("ProjectWindow").get_position()
        self._position = (self._position[0] + 100, self._position[1] + 100)
        self.container = self.gui.get_object("view3dbox")
        self.gui.get_object("Reset View").connect("clicked", self.rotate_view,
                VIEWS["reset"])
        self.gui.get_object("Left View").connect("clicked", self.rotate_view,
                VIEWS["left"])
        self.gui.get_object("Right View").connect("clicked", self.rotate_view,
                VIEWS["right"])
        self.gui.get_object("Front View").connect("clicked", self.rotate_view,
                VIEWS["front"])
        self.gui.get_object("Back View").connect("clicked", self.rotate_view,
                VIEWS["back"])
        self.gui.get_object("Top View").connect("clicked", self.rotate_view,
                VIEWS["top"])
        self.gui.get_object("Bottom View").connect("clicked", self.rotate_view,
                VIEWS["bottom"])
        # key binding
        self.window.connect("key-press-event", self.key_handler)
        # OpenGL stuff
        glconfig = gtk.gdkgl.Config(mode=gtk.gdkgl.MODE_RGBA \
                | gtk.gdkgl.MODE_DEPTH | gtk.gdkgl.MODE_DOUBLE)
        self.area = gtk.gtkgl.DrawingArea(glconfig)
        # first run; might also be important when doing other fancy
        # gtk/gdk stuff
        self.area.connect_after('realize', self.paint)
        # called when a part of the screen is uncovered
        self.area.connect('expose-event', self.paint)
        # resize window
        self.area.connect('configure-event', self._resize_window)
        # catch mouse events
        self.area.set_events(gtk.gdk.MOUSE | gtk.gdk.POINTER_MOTION_HINT_MASK \
                | gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.BUTTON_RELEASE_MASK \
                | gtk.gdk.SCROLL_MASK)
        self.area.connect("button-press-event", self.mouse_press_handler)
        self.area.connect('motion-notify-event', self.mouse_handler)
        self.area.connect("button-release-event", self.context_menu_handler)
        self.area.connect("scroll-event", self.scroll_handler)
        self.container.pack_end(self.area)
        self.camera = Camera(self.settings, lambda: (self.area.allocation.width,
                self.area.allocation.height))
        # Color the dimension value according to the axes.
        # For "y" axis: 100% green is too bright on light background - we
        # reduce it a bit.
        for color, names in (
                (pango.AttrForeground(65535, 0, 0, 0, 100),
                        ("model_dim_x_label", "model_dim_x", "ModelCornerXMax",
                            "ModelCornerXMin", "ModelCornerXSpaces")),
                (pango.AttrForeground(0, 50000, 0, 0, 100),
                        ("model_dim_y_label", "model_dim_y", "ModelCornerYMax",
                            "ModelCornerYMin", "ModelCornerYSpaces")),
                (pango.AttrForeground(0, 0, 65535, 0, 100),
                        ("model_dim_z_label", "model_dim_z", "ModelCornerZMax",
                            "ModelCornerZMin", "ModelCornerZSpaces"))):
            attributes = pango.AttrList()
            attributes.insert(color)
            for name in names:
                self.gui.get_object(name).set_attributes(attributes)
        # add the items buttons (for configuring visible items)
        if item_buttons:
            items_button_container = self.gui.get_object("ViewItems")
            for button in item_buttons:
                new_checkbox = gtk.ToggleToolButton()
                new_checkbox.set_label(button.get_label())
                new_checkbox.set_active(button.get_active())
                # Configure the two buttons (in "Preferences" and in the 3D view
                # widget) to toggle each other. This is required for a
                # consistent view of the setting.
                connect_button_handlers("toggled", button, new_checkbox)
                items_button_container.insert(new_checkbox, -1)
            items_button_container.show_all()
            # create the drop-down menu
            if context_menu_actions:
                action_group = gtk.ActionGroup("context")
                for action in context_menu_actions:
                    action_group.add_action(action)
                uimanager = gtk.UIManager()
                # The "pos" parameter is optional since gtk 2.12 - we can
                # remove it later.
                uimanager.insert_action_group(action_group, pos=-1)
                uimanager_template = '<ui><popup name="context">%s</popup></ui>'
                uimanager_item_template = """<menuitem action="%s" />"""
                uimanager_text = uimanager_template % "".join(
                        [uimanager_item_template % action.get_name()
                                for action in context_menu_actions])
                uimanager.add_ui_from_string(uimanager_text)
                self.context_menu = uimanager.get_widget("/context")
                self.context_menu.insert(gtk.SeparatorMenuItem(), 0)
            else:
                self.context_menu = gtk.Menu()
            for index, button in enumerate(item_buttons):
                new_item = gtk.CheckMenuItem(button.get_label())
                new_item.set_active(button.get_active())
                connect_button_handlers("toggled", button, new_item)
                self.context_menu.insert(new_item, index)
            self.context_menu.show_all()
        else:
            self.context_menu = None
        # show the window
        self.area.show()
        self.container.show()
        self.show()

    def show(self):
        self.is_visible = True
        self.window.move(*self._position)
        self.window.show()

    def hide(self):
        self.is_visible = False
        self._position = self.window.get_position()
        self.window.hide()

    def key_handler(self, widget=None, event=None):
        if event is None:
            return
        try:
            keyval = getattr(event, "keyval")
            get_state = getattr(event, "get_state")
            key_string = getattr(event, "string")
        except AttributeError:
            return
        # define arrow keys and "vi"-like navigation keys
        move_keys_dict = {
                gtk.keysyms.Left: (1, 0),
                gtk.keysyms.Down: (0, -1),
                gtk.keysyms.Up: (0, 1),
                gtk.keysyms.Right: (-1, 0),
                ord("h"): (1, 0),
                ord("j"): (0, -1),
                ord("k"): (0, 1),
                ord("l"): (-1, 0),
                ord("H"): (1, 0),
                ord("J"): (0, -1),
                ord("K"): (0, 1),
                ord("L"): (-1, 0),
        }
        if key_string and (key_string in '1234567'):
            names = ["reset", "front", "back", "left", "right", "top", "bottom"]
            index = '1234567'.index(key_string)
            self.rotate_view(view=VIEWS[names[index]])
            self._paint_ignore_busy()
        elif key_string in ('i', 'm', 's', 'p'):
            if key_string == 'i':
                key = "view_light"
            elif key_string == 'm':
                key = "view_polygon"
            elif key_string == 's':
                key = "view_shadow"
            elif key_string == 'p':
                key = "view_perspective"
            else:
                key = None
            # toggle setting
            self.settings.set(key, not self.settings.get(key))
            # re-init gl settings
            self.glsetup()
            self.paint()
        elif key_string in ("+", "-"):
            if key_string == "+":
                self.camera.zoom_in()
            else:
                self.camera.zoom_out()
            self._paint_ignore_busy()
        elif keyval in move_keys_dict.keys():
            move_x, move_y = move_keys_dict[keyval]
            if get_state() & gtk.gdk.SHIFT_MASK:
                # shift key pressed -> rotation
                base = 0
                factor = 10
                self.camera.rotate_camera_by_screen(base, base,
                        base - factor * move_x, base - factor * move_y)
            else:
                # no shift key -> moving
                self.camera.shift_view(x_dist=move_x, y_dist=move_y)
            self._paint_ignore_busy()
        else:
            # see dir(gtk.keysyms)
            #print "Key pressed: %s (%s)" % (keyval, get_state())
            pass

    def check_busy(func):
        def check_busy_wrapper(self, *args, **kwargs):
            if not self.enabled or self.busy:
                return
            self.busy = True
            result = func(self, *args, **kwargs)
            self.busy = False
            return result
        return check_busy_wrapper

    def gtkgl_refresh(func):
        def gtkgl_refresh_wrapper(self, *args, **kwargs):
            prev_mode = GL.glGetIntegerv(GL.GL_MATRIX_MODE)
            GL.glMatrixMode(GL.GL_MODELVIEW)
            # clear the background with the configured color
            bg_col = self.settings.get("color_background")
            GL.glClearColor(bg_col[0], bg_col[1], bg_col[2], 0.0)
            GL.glClear(GL.GL_COLOR_BUFFER_BIT|GL.GL_DEPTH_BUFFER_BIT)
            result = func(self, *args, **kwargs)
            self.camera.position_camera()
            self._paint_raw()
            GL.glMatrixMode(prev_mode)
            GL.glFlush()
            self.area.get_gl_drawable().swap_buffers()
            return result
        return gtkgl_refresh_wrapper

    def glsetup(self):
        GLUT.glutInit()
        if self.settings.get("view_shadow"):
            GL.glShadeModel(GL.GL_FLAT)
        else:
            GL.glShadeModel(GL.GL_SMOOTH)
        bg_col = self.settings.get("color_background")
        GL.glClearColor(bg_col[0], bg_col[1], bg_col[2], 0.0)
        GL.glClearDepth(1.)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glDepthFunc(GL.GL_LEQUAL)
        GL.glDepthMask(GL.GL_TRUE)
        GL.glHint(GL.GL_PERSPECTIVE_CORRECTION_HINT, GL.GL_NICEST)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        #GL.glMaterial(GL.GL_FRONT_AND_BACK, GL.GL_AMBIENT,
        #        (0.1, 0.1, 0.1, 1.0))
        GL.glMaterial(GL.GL_FRONT_AND_BACK, GL.GL_SPECULAR,
                (0.1, 0.1, 0.1, 1.0))
        #GL.glMaterial(GL.GL_FRONT_AND_BACK, GL.GL_SHININESS, (0.5))
        if self.settings.get("view_polygon"):
            GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)
        else:
            GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_LINE)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        GL.glViewport(0, 0, self.area.allocation.width,
                self.area.allocation.height)
        # lighting
        # Setup The Ambient Light
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_AMBIENT, (0.3, 0.3, 0.3, 3.))
        # Setup The Diffuse Light
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, (1., 1., 1., .0))
        # Setup The SpecularLight
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_SPECULAR, (.3, .3, .3, 1.0))
        GL.glEnable(GL.GL_LIGHT0)
        # Enable Light One
        if self.settings.get("view_light"):
            GL.glEnable(GL.GL_LIGHTING)
        else:
            GL.glDisable(GL.GL_LIGHTING)
        GL.glEnable(GL.GL_NORMALIZE)
        GL.glColorMaterial(GL.GL_FRONT_AND_BACK, GL.GL_AMBIENT_AND_DIFFUSE)
        #GL.glColorMaterial(GL.GL_FRONT_AND_BACK, GL.GL_SPECULAR)
        #GL.glColorMaterial(GL.GL_FRONT_AND_BACK, GL.GL_EMISSION)
        GL.glEnable(GL.GL_COLOR_MATERIAL)
        # enable blending/transparency (alpha) for colors
        GL.glEnable(GL.GL_BLEND)
        # see http://wiki.delphigl.com/index.php/glBlendFunc
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

    def destroy(self, widget=None, data=None):
        if self.notify_destroy_func:
            self.notify_destroy_func()
        # don't close the window
        return True

    def gtkgl_functionwrapper(function):
        def gtkgl_functionwrapper_function(self, *args, **kwords):
            gldrawable = self.area.get_gl_drawable()
            if not gldrawable:
                return
            glcontext = self.area.get_gl_context()
            if not gldrawable.gl_begin(glcontext):
                return
            if not self.initialized:
                self.glsetup()
                self.initialized = True
            result = function(self, *args, **kwords)
            gldrawable.gl_end()
            return result
        return gtkgl_functionwrapper_function

    @check_busy
    @gtkgl_functionwrapper
    def context_menu_handler(self, widget, event):
        if (event.button == self.mouse["pressed_button"] == BUTTON_RIGHT) \
                and self.context_menu \
                and (event.get_time() - self.mouse["pressed_timestamp"] < 300) \
                and (abs(event.x - self.mouse["pressed_pos"][0]) < 3) \
                and (abs(event.y - self.mouse["pressed_pos"][1]) < 3):
            # A quick press/release cycle with the right mouse button
            # -> open the context menu.
            self.context_menu.popup(None, None, None, event.button,
                    int(event.get_time()))

    @check_busy
    @gtkgl_functionwrapper
    def scroll_handler(self, widget, event):
        """ handle events of the scroll wheel

        shift key: horizontal pan instead of vertical
        control key: zoom
        """
        try:
            modifier_state = event.get_state()
        except AttributeError:
            # this should probably never happen
            return
        control_pressed = modifier_state & gtk.gdk.CONTROL_MASK
        shift_pressed = modifier_state & gtk.gdk.SHIFT_MASK
        if (event.direction == gtk.gdk.SCROLL_RIGHT) or \
                ((event.direction == gtk.gdk.SCROLL_UP) and shift_pressed):
            # horizontal move right
            self.camera.shift_view(x_dist=-1)
        elif (event.direction == gtk.gdk.SCROLL_LEFT) or \
                ((event.direction == gtk.gdk.SCROLL_DOWN) and shift_pressed):
            # horizontal move left
            self.camera.shift_view(x_dist=1)
        elif (event.direction == gtk.gdk.SCROLL_UP) and control_pressed:
            # zoom in
            self.camera.zoom_in()
        elif event.direction == gtk.gdk.SCROLL_UP:
            # vertical move up
            self.camera.shift_view(y_dist=1)
        elif (event.direction == gtk.gdk.SCROLL_DOWN) and control_pressed:
            # zoom out
            self.camera.zoom_out()
        elif event.direction == gtk.gdk.SCROLL_DOWN:
            # vertical move down
            self.camera.shift_view(y_dist=-1)
        else:
            # no interesting event -> no re-painting
            return
        self._paint_ignore_busy()

    def mouse_press_handler(self, widget, event):
        self.mouse["pressed_timestamp"] = event.get_time()
        self.mouse["pressed_button"] = event.button
        self.mouse["pressed_pos"] = event.x, event.y
        self.mouse_handler(widget, event)

    @check_busy
    @gtkgl_functionwrapper
    def mouse_handler(self, widget, event):
        x, y, state = event.x, event.y, event.state
        if self.mouse["button"] is None:
            if (state & BUTTON_ZOOM) or (state & BUTTON_ROTATE) \
                    or (state & BUTTON_MOVE):
                self.mouse["button"] = state
                self.mouse["start_pos"] = [x, y]
        else:
            # Don't try to create more than 25 frames per second (enough for
            # a decent visualization).
            if event.get_time() - self.mouse["event_timestamp"] < 40:
                return
            elif state & self.mouse["button"] & BUTTON_ZOOM:
                # the start button is still active: update the view
                start_x, start_y = self.mouse["start_pos"]
                self.mouse["start_pos"] = [x, y]
                # Move the mouse from lower left to top right corner for
                # scaling up.
                scale = 1 - 0.01 * ((x - start_x) + (start_y - y))
                # do some sanity checks, scale no more than
                # 1:100 on any given click+drag
                if scale < 0.01:
                    scale = 0.01
                elif scale > 100:
                    scale = 100
                self.camera.scale_distance(scale)
                self._paint_ignore_busy()
            elif (state & self.mouse["button"] & BUTTON_MOVE) \
                    or (state & self.mouse["button"] & BUTTON_ROTATE):
                start_x, start_y = self.mouse["start_pos"]
                self.mouse["start_pos"] = [x, y]
                if (state & BUTTON_MOVE):
                    # Determine the biggest dimension (x/y/z) for moving the
                    # screen's center in relation to this value.
                    obj_dim = []
                    obj_dim.append(self.settings.get("maxx") \
                            - self.settings.get("minx"))
                    obj_dim.append(self.settings.get("maxy") \
                            - self.settings.get("miny"))
                    obj_dim.append(self.settings.get("maxz") \
                            - self.settings.get("minz"))
                    max_dim = max(obj_dim)
                    self.camera.move_camera_by_screen(x - start_x, y - start_y,
                            max_dim)
                else:
                    # BUTTON_ROTATE
                    # update the camera position according to the mouse movement
                    self.camera.rotate_camera_by_screen(start_x, start_y, x, y)
                self._paint_ignore_busy()
            else:
                # button was released
                self.mouse["button"] = None
                self._paint_ignore_busy()
        self.mouse["event_timestamp"] = event.get_time()

    @check_busy
    @gtkgl_functionwrapper
    @gtkgl_refresh
    def rotate_view(self, widget=None, view=None):
        self.camera.set_view(view)

    def reset_view(self):
        self.rotate_view(None, None)

    @check_busy
    @gtkgl_functionwrapper
    @gtkgl_refresh
    def _resize_window(self, widget, data=None):
        GL.glViewport(0, 0, self.area.allocation.width,
                self.area.allocation.height)

    @check_busy
    @gtkgl_functionwrapper
    @gtkgl_refresh
    def paint(self, widget=None, data=None):
        # the decorators take core for redraw
        pass

    @gtkgl_functionwrapper
    @gtkgl_refresh
    def _paint_ignore_busy(self, widget=None):
        pass

    def _paint_raw(self, widget=None):
        # draw the model
        draw_complete_model_view(self.settings)
        # update the dimension display
        s = self.settings
        dimension_bar = self.gui.get_object("view3ddimension")
        if s.get("show_dimensions"):
            for name, size in (
                    ("model_dim_x", s.get("maxx") - s.get("minx")),
                    ("model_dim_y", s.get("maxy") - s.get("miny")),
                    ("model_dim_z", s.get("maxz") - s.get("minz"))):
                self.gui.get_object(name).set_text("%.3f %s" \
                        % (size, s.get("unit")))
            dimension_bar.show()
        else:
            dimension_bar.hide()


def keep_gl_mode(func):
    def keep_gl_mode_wrapper(*args, **kwargs):
        prev_mode = GL.glGetIntegerv(GL.GL_MATRIX_MODE)
        result = func(*args, **kwargs)
        GL.glMatrixMode(prev_mode)
        return result
    return keep_gl_mode_wrapper

def keep_matrix(func):
    def keep_matrix_wrapper(*args, **kwargs):
        pushed_matrix_mode = GL.glGetIntegerv(GL.GL_MATRIX_MODE)
        GL.glPushMatrix()
        result = func(*args, **kwargs)
        final_matrix_mode = GL.glGetIntegerv(GL.GL_MATRIX_MODE)
        GL.glMatrixMode(pushed_matrix_mode)
        GL.glPopMatrix()
        GL.glMatrixMode(final_matrix_mode)
        return result
    return keep_matrix_wrapper

@keep_matrix
def draw_direction_cone(p1, p2):
    distance = p2.sub(p1)
    length = distance.norm
    direction = distance.normalized()
    if direction is None:
        # zero-length line
        return
    cone_radius = length / 30
    cone_length = length / 10
    # move the cone to the middle of the line
    GL.glTranslatef((p1.x + p2.x) / 2, (p1.y + p2.y) / 2, (p1.z + p2.z) / 2)
    # rotate the cone according to the line direction
    # The cross product is a good rotation axis.
    cross = direction.cross(Point(0, 0, -1))
    if cross.norm != 0:
        # The line direction is not in line with the z axis.
        try:
            angle = math.asin(sqrt(direction.x ** 2 + direction.y ** 2))
        except ValueError:
            # invalid angle - just ignore this cone
            return
        # convert from radians to degree
        angle = angle / math.pi * 180
        if direction.z < 0:
            angle = 180 - angle
        GL.glRotatef(angle, cross.x, cross.y, cross.z)
    elif direction.z == -1:
        # The line goes down the z axis - turn it around.
        GL.glRotatef(180, 1, 0, 0)
    else:
        # The line goes up the z axis - nothing to be done.
        pass
    # center the cone
    GL.glTranslatef(0, 0, -cone_length / 2)
    # draw the cone
    GLUT.glutSolidCone(cone_radius, cone_length, 12, 1)

@keep_matrix
def draw_string(x, y, z, p, s, scale=.01):
    GL.glPushMatrix()
    GL.glTranslatef(x, y, z)
    if p == 'xy':
        GL.glRotatef(90, 1, 0, 0)
    elif p == 'yz':
        GL.glRotatef(90, 0, 1, 0)
        GL.glRotatef(90, 0, 0, 1)
    elif p == 'xz':
        GL.glRotatef(90, 0, 1, 0)
        GL.glRotatef(90, 0, 0, 1)
        GL.glRotatef(45, 0, 1, 0)
    GL.glScalef(scale, scale, scale)
    for c in str(s):
        GLUT.glutStrokeCharacter(GLUT.GLUT_STROKE_ROMAN, ord(c))
    GL.glPopMatrix()

@keep_gl_mode
@keep_matrix
def draw_axes(settings):
    GL.glMatrixMode(GL.GL_MODELVIEW)
    GL.glLoadIdentity()
    #GL.glTranslatef(0, 0, -2)
    size_x = abs(settings.get("maxx"))
    size_y = abs(settings.get("maxy"))
    size_z = abs(settings.get("maxz"))
    size = number(1.7) * max(size_x, size_y, size_z)
    # the divider is just based on playing with numbers
    scale = size / number(1500.0)
    string_distance = number(1.1) * size
    GL.glBegin(GL.GL_LINES)
    GL.glColor3f(1, 0, 0)
    GL.glVertex3f(0, 0, 0)
    GL.glVertex3f(size, 0, 0)
    GL.glEnd()
    draw_string(string_distance, 0, 0, 'xy', "X", scale=scale)
    GL.glBegin(GL.GL_LINES)
    GL.glColor3f(0, 1, 0)
    GL.glVertex3f(0, 0, 0)
    GL.glVertex3f(0, size, 0)
    GL.glEnd()
    draw_string(0, string_distance, 0, 'yz', "Y", scale=scale)
    GL.glBegin(GL.GL_LINES)
    GL.glColor3f(0, 0, 1)
    GL.glVertex3f(0, 0, 0)
    GL.glVertex3f(0, 0, size)
    GL.glEnd()
    draw_string(0, 0, string_distance, 'xz', "Z", scale=scale)

@keep_matrix
def draw_bounding_box(minx, miny, minz, maxx, maxy, maxz, color):
    p1 = [minx, miny, minz]
    p2 = [minx, maxy, minz]
    p3 = [maxx, maxy, minz]
    p4 = [maxx, miny, minz]
    p5 = [minx, miny, maxz]
    p6 = [minx, maxy, maxz]
    p7 = [maxx, maxy, maxz]
    p8 = [maxx, miny, maxz]
    # lower rectangle
    GL.glBegin(GL.GL_LINES)
    GL.glColor4f(*color)
    # all combinations of neighbouring corners
    for corner_pair in [(p1, p2), (p1, p5), (p1, p4), (p2, p3),
                (p2, p6), (p3, p4), (p3, p7), (p4, p8), (p5, p6),
                (p6, p7), (p7, p8), (p8, p5)]:
        GL.glVertex3f(*(corner_pair[0]))
        GL.glVertex3f(*(corner_pair[1]))
    GL.glEnd()

@keep_gl_mode
@keep_matrix
def draw_complete_model_view(settings):
    GL.glMatrixMode(GL.GL_MODELVIEW)
    GL.glLoadIdentity()
    # axes
    if settings.get("show_axes"):
        draw_axes(settings)
    # stock model
    if settings.get("show_bounding_box"):
        draw_bounding_box(
                float(settings.get("minx")), float(settings.get("miny")),
                float(settings.get("minz")), float(settings.get("maxx")),
                float(settings.get("maxy")), float(settings.get("maxz")),
                settings.get("color_bounding_box"))
    # draw the material (for simulation mode)
    if settings.get("show_simulation"):
        obj = settings.get("simulation_object")
        if not obj is None:
            GL.glColor4f(*settings.get("color_material"))
            obj.to_OpenGL()
    # draw the model
    if settings.get("show_model") \
            and not (settings.get("show_simulation") \
                and settings.get("simulation_toolpath_moves")):
        GL.glColor4f(*settings.get("color_model"))
        model = settings.get("model")
        """
        min_area = abs(model.maxx - model.minx) * abs(model.maxy - model.miny) / 100
        # example for coloring specific triangles
        groups = model.get_flat_areas(min_area)
        all_flat_ids = []
        for group in groups:
            all_flat_ids.extend([t.id for t in group])
        flat_color = (1.0, 0.0, 0.0, 1.0)
        normal_color = settings.get("color_model")
        def check_triangle_draw(triangle):
            if triangle.id in all_flat_ids:
                return True, flat_color
            else:
                return True, normal_color
        model.to_OpenGL(visible_filter=check_triangle_draw)
        """
        model.to_OpenGL(show_directions=settings.get("show_directions"))
    # draw the support grid
    if settings.get("show_support_grid") and settings.get("support_grid"):
        GL.glColor4f(*settings.get("color_support_grid"))
        settings.get("support_grid").to_OpenGL()
    # draw the toolpath simulation
    if settings.get("show_simulation"):
        moves = settings.get("simulation_toolpath_moves")
        if not moves is None:
            draw_toolpath(moves, settings.get("color_toolpath_cut"),
                    settings.get("color_toolpath_return"),
                    show_directions=settings.get("show_directions"))
    # draw the toolpath
    # don't do it, if a new toolpath is just being calculated
    safety_height = settings.get("gcode_safety_height")
    if settings.get("show_toolpath") \
            and not settings.get("toolpath_in_progress") \
            and not (settings.get("show_simulation") \
                    and settings.get("simulation_toolpath_moves")):
        for toolpath_obj in settings.get("toolpath"):
            if toolpath_obj.visible:
                draw_toolpath(toolpath_obj.get_moves(safety_height),
                        settings.get("color_toolpath_cut"),
                        settings.get("color_toolpath_return"),
                        show_directions=settings.get("show_directions"))
    # draw the drill
    if settings.get("show_drill"):
        cutter = settings.get("cutter")
        if not cutter is None:
            GL.glColor4f(*settings.get("color_cutter"))
            cutter.to_OpenGL()
    if settings.get("show_drill_progress") \
            and settings.get("toolpath_in_progress"):
        # show the toolpath that is currently being calculated
        toolpath_in_progress = settings.get("toolpath_in_progress")
        # do a quick conversion from a list of Paths to a list of points
        moves = []
        for path in toolpath_in_progress:
            for point in path.points:
                moves.append((point, False))
        if not toolpath_in_progress is None:
            draw_toolpath(moves, settings.get("color_toolpath_cut"),
                    settings.get("color_toolpath_return"),
                    show_directions=settings.get("show_directions"))

@keep_gl_mode
@keep_matrix
def draw_toolpath(moves, color_cut, color_rapid, show_directions=False):
    GL.glMatrixMode(GL.GL_MODELVIEW)
    GL.glLoadIdentity()
    last_position = None
    last_rapid = None
    GL.glBegin(GL.GL_LINE_STRIP)
    for position, rapid in moves:
        if last_rapid != rapid:
            GL.glEnd()
            if rapid:
                GL.glColor4f(*color_rapid)
            else:
                GL.glColor4f(*color_cut)
            GL.glBegin(GL.GL_LINE_STRIP)
            if not last_position is None:
                GL.glVertex3f(last_position.x, last_position.y, last_position.z)
            last_rapid = rapid
        GL.glVertex3f(position.x, position.y, position.z)
        last_position = position
    GL.glEnd()
    if show_directions:
        for index in range(len(moves) - 1):
            p1 = moves[index][0]
            p2 = moves[index + 1][0]
            draw_direction_cone(p1, p2)

