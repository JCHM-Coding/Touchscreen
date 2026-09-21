import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Matrix, Quaternion
import math


GROUP_ID = "NAVIGATION_CUSTOM_GGT"

MAX_ID = "NAVIGATION_MAX_GT"
FRAME_ID = "NAVIGATION_FRAME_GT"
QUAD_ID = "NAVIGATION_QUAD_GT"
LOCK_ID = "NAVIGATION_LOCK_GT"
FRONT_ID = "NAVIGATION_FRONT_GT"
SIDE_ID = "NAVIGATION_SIDE_GT"
TOP_ID = "NAVIGATION_TOP_GT"
INVERT_ID = "NAVIGATION_INVERT_GT"


# ---------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------

BUTTON_RADIUS = 16.0
BUTTON_HIT_RADIUS = 24.0
CIRCLE_SEGMENTS = 64
ICON_SIZE = 22.8


def _viewport_scale():
    """Return the user-selected Viewport Controls scale."""
    try:
        prefs = bpy.context.preferences.addons[__package__].preferences
        return 2.0 if getattr(prefs, "viewport_controls_2x", False) else 1.0
    except Exception:
        return 1.0


# ---------------------------------------------------------
# DRAW HELPERS
# ---------------------------------------------------------

def draw_lines(points, color=(0.8, 0.8, 0.8, 1.0), width=2.0):

    shader = gpu.shader.from_builtin('UNIFORM_COLOR')

    batch = batch_for_shader(
        shader,
        'LINES',
        {"pos": points}
    )

    shader.bind()
    shader.uniform_float("color", color)

    gpu.state.line_width_set(width)
    batch.draw(shader)
    gpu.state.line_width_set(1.0)


def draw_circle(x, y, radius, color, width=2.0):

    points = []

    for i in range(CIRCLE_SEGMENTS + 1):

        angle = (
            2.0 *
            math.pi *
            i /
            CIRCLE_SEGMENTS
        )

        points.append(
            (
                x + math.cos(angle) * radius,
                y + math.sin(angle) * radius
            )
        )

    draw_lines(
        points,
        color,
        width
    )


def draw_maximize_icon(x, y, size, color):

    s = size
    a = s * 0.42
    b = s * 0.16

    points = [
        (x-a, y+a), (x-a+b, y+a),
        (x-a, y+a), (x-a, y+a-b),

        (x+a, y+a), (x+a-b, y+a),
        (x+a, y+a), (x+a, y+a-b),

        (x-a, y-a), (x-a+b, y-a),
        (x-a, y-a), (x-a, y-a+b),

        (x+a, y-a), (x+a-b, y-a),
        (x+a, y-a), (x+a, y-a+b),
    ]

    draw_lines(
        points,
        color,
        2.2
    )


def draw_quad_icon(x, y, size, color):

    s = size * 0.42

    left = x - s
    right = x + s
    bottom = y - s
    top = y + s

    points = [
        (left, bottom), (right, bottom),
        (right, bottom), (right, top),
        (right, top), (left, top),
        (left, top), (left, bottom),

        (x, bottom), (x, top),
        (left, y), (right, y),
    ]

    draw_lines(
        points,
        color,
        2.0
    )


def draw_lock_icon(x, y, size, color):

    s = size * 0.34

    # Lock body
    points = [
        (x-s, y-s),
        (x+s, y-s),

        (x+s, y-s),
        (x+s, y+s*0.10),

        (x+s, y+s*0.10),
        (x-s, y+s*0.10),

        (x-s, y+s*0.10),
        (x-s, y-s),
    ]

    draw_lines(
        points,
        color,
        2.0
    )

    # Shackle
    points2 = [
        (x-s*0.65, y+s*0.10),
        (x-s*0.65, y+s*0.65),

        (x-s*0.65, y+s*0.65),
        (x+s*0.65, y+s*0.65),

        (x+s*0.65, y+s*0.65),
        (x+s*0.65, y+s*0.10),
    ]

    draw_lines(
        points2,
        color,
        2.0
    )


def draw_letter_icon(x, y, letter, size, color):

    s = size * 0.34
    w = size * 0.20

    if letter == "Y":

        points = [
            (x-w, y+s),
            (x, y),

            (x+w, y+s),
            (x, y),

            (x, y),
            (x, y-s),
        ]

    elif letter == "X":

        points = [
            (x-w, y+s),
            (x+w, y-s),

            (x+w, y+s),
            (x-w, y-s),
        ]

    elif letter == "Z":

        points = [
            (x-w, y+s),
            (x+w, y+s),

            (x+w, y+s),
            (x-w, y-s),

            (x-w, y-s),
            (x+w, y-s),
        ]

    elif letter == "I":

        points = [
            (x-w, y+s),
            (x+w, y+s),

            (x, y+s),
            (x, y-s),

            (x-w, y-s),
            (x+w, y-s),
        ]

    elif letter == "F":

        points = [
            (x-w, y+s),
            (x-w, y-s),

            (x-w, y+s),
            (x+w, y+s),

            (x-w, y),
            (x+w*0.65, y),
        ]

    else:
        return

    draw_lines(
        points,
        color,
        2.2
    )


# ---------------------------------------------------------
# BASE GIZMO
# ---------------------------------------------------------

class NAVIGATION_BaseGizmo(bpy.types.Gizmo):

    def setup(self):
        self.clicked = False

    def test_select(self, context, location):

        x = self.matrix_world[0][3]
        y = self.matrix_world[1][3]

        dx = location[0] - x
        dy = location[1] - y

        hit_radius = BUTTON_HIT_RADIUS * _viewport_scale()

        if (
            dx * dx +
            dy * dy
            <= hit_radius * hit_radius
        ):
            return 0

        return -1

    def invoke(self, context, event):

        self.execute_function(context)

        if context.area:
            context.area.tag_redraw()

        return {'FINISHED'}

    def modal(self, context, event, tweak):

        return {'FINISHED'}

    def get_icon_color(self):

        if self.clicked:
            return (
                1.0,
                1.0,
                1.0,
                1.0
            )

        return (
            0.70,
            0.70,
            0.70,
            1.0
        )

    def draw_button_background(self):

        x = self.matrix_world[0][3]
        y = self.matrix_world[1][3]

        color = (
            0.18,
            0.18,
            0.18,
            1.0
        )

        draw_circle(
            x,
            y,
            BUTTON_RADIUS * _viewport_scale(),
            color,
            2.0
        )


# ---------------------------------------------------------
# MAXIMIZE
# ---------------------------------------------------------

class NAVIGATION_MAX_GT(NAVIGATION_BaseGizmo):

    bl_idname = MAX_ID

    def execute_function(self, context):

        try:
            bpy.ops.screen.screen_full_area()
        except Exception as e:
            print("Navigation - Maximize:", e)

    def draw(self, context):

        self.draw_button_background()

        x = self.matrix_world[0][3]
        y = self.matrix_world[1][3]

        draw_maximize_icon(
            x,
            y,
            ICON_SIZE,
            self.get_icon_color()
        )

    def draw_select(self, context, select_id=0):

        self.draw_preset_box(
            self.matrix_world,
            select_id=select_id
        )


# ---------------------------------------------------------
# FRAME SELECTED
# ---------------------------------------------------------

class NAVIGATION_FRAME_GT(NAVIGATION_BaseGizmo):

    bl_idname = FRAME_ID

    def execute_function(self, context):

        try:
            bpy.ops.view3d.view_selected()
        except Exception as e:
            print("Navigation - Frame Selected:", e)

    def draw(self, context):

        self.draw_button_background()

        x = self.matrix_world[0][3]
        y = self.matrix_world[1][3]

        draw_letter_icon(
            x,
            y,
            "F",
            ICON_SIZE,
            self.get_icon_color()
        )

    def draw_select(self, context, select_id=0):

        self.draw_preset_box(
            self.matrix_world,
            select_id=select_id
        )


# ---------------------------------------------------------
# QUAD VIEW
# ---------------------------------------------------------

class NAVIGATION_QUAD_GT(NAVIGATION_BaseGizmo):

    bl_idname = QUAD_ID

    def execute_function(self, context):

        try:
            bpy.ops.screen.region_quadview()
        except Exception as e:
            print("Navigation - Quad View:", e)

    def draw(self, context):

        self.draw_button_background()

        x = self.matrix_world[0][3]
        y = self.matrix_world[1][3]

        draw_quad_icon(
            x,
            y,
            ICON_SIZE,
            self.get_icon_color()
        )

    def draw_select(self, context, select_id=0):

        self.draw_preset_box(
            self.matrix_world,
            select_id=select_id
        )


# ---------------------------------------------------------
# LOCK ROTATION
# ---------------------------------------------------------

class NAVIGATION_LOCK_GT(NAVIGATION_BaseGizmo):

    bl_idname = LOCK_ID

    def execute_function(self, context):

        space = context.space_data

        if not space:
            return

        region_3d = context.region_data

        if region_3d is None:
            return

        if hasattr(region_3d, "lock_rotation"):

            region_3d.lock_rotation = (
                not region_3d.lock_rotation
            )

            self.clicked = region_3d.lock_rotation

    def draw(self, context):

        self.draw_button_background()

        region_3d = context.region_data

        locked = False

        if region_3d is not None:

            if hasattr(region_3d, "lock_rotation"):
                locked = region_3d.lock_rotation

        x = self.matrix_world[0][3]
        y = self.matrix_world[1][3]

        color = (
            (1.0, 1.0, 1.0, 1.0)
            if locked
            else (0.70, 0.70, 0.70, 1.0)
        )

        draw_lock_icon(
            x,
            y,
            ICON_SIZE,
            color
        )

    def draw_select(self, context, select_id=0):

        self.draw_preset_box(
            self.matrix_world,
            select_id=select_id
        )


# ---------------------------------------------------------
# VIEW AXIS BASE
# ---------------------------------------------------------

class NAVIGATION_AXIS_BaseGizmo(NAVIGATION_BaseGizmo):

    def set_axis_selection(self, context):

        try:
            group = context.space_data

            if group is None:
                return

        except Exception:
            pass

    def execute_axis(self, context, axis_type):

        try:

            bpy.ops.view3d.view_axis(
                type=axis_type,
                align_active=False,
                relative=False
            )

        except Exception as e:

            print(
                "Navigation - Axis:",
                axis_type,
                e
            )


# ---------------------------------------------------------
# FRONT VIEW - Y
# ---------------------------------------------------------

class NAVIGATION_FRONT_GT(NAVIGATION_AXIS_BaseGizmo):

    bl_idname = FRONT_ID
    axis_name = "Y"

    def execute_function(self, context):

        self.execute_axis(
            context,
            'FRONT'
        )

        self.clicked = True

    def draw(self, context):

        self.draw_button_background()

        x = self.matrix_world[0][3]
        y = self.matrix_world[1][3]

        draw_letter_icon(
            x,
            y,
            "Y",
            ICON_SIZE,
            self.get_icon_color()
        )

    def draw_select(self, context, select_id=0):

        self.draw_preset_box(
            self.matrix_world,
            select_id=select_id
        )


# ---------------------------------------------------------
# SIDE VIEW - X
# ---------------------------------------------------------

class NAVIGATION_SIDE_GT(NAVIGATION_AXIS_BaseGizmo):

    bl_idname = SIDE_ID
    axis_name = "X"

    def execute_function(self, context):

        self.execute_axis(
            context,
            'RIGHT'
        )

        self.clicked = True

    def draw(self, context):

        self.draw_button_background()

        x = self.matrix_world[0][3]
        y = self.matrix_world[1][3]

        draw_letter_icon(
            x,
            y,
            "X",
            ICON_SIZE,
            self.get_icon_color()
        )

    def draw_select(self, context, select_id=0):

        self.draw_preset_box(
            self.matrix_world,
            select_id=select_id
        )


# ---------------------------------------------------------
# TOP VIEW - Z
# ---------------------------------------------------------

class NAVIGATION_TOP_GT(NAVIGATION_AXIS_BaseGizmo):

    bl_idname = TOP_ID
    axis_name = "Z"

    def execute_function(self, context):

        self.execute_axis(
            context,
            'TOP'
        )

        self.clicked = True

    def draw(self, context):

        self.draw_button_background()

        x = self.matrix_world[0][3]
        y = self.matrix_world[1][3]

        draw_letter_icon(
            x,
            y,
            "Z",
            ICON_SIZE,
            self.get_icon_color()
        )

    def draw_select(self, context, select_id=0):

        self.draw_preset_box(
            self.matrix_world,
            select_id=select_id
        )


# ---------------------------------------------------------
# INVERT VIEW - I
# ---------------------------------------------------------

class NAVIGATION_INVERT_GT(NAVIGATION_BaseGizmo):

    bl_idname = INVERT_ID

    def execute_function(self, context):

        region_3d = context.region_data

        if region_3d is None:
            return

        try:

            region_3d.view_rotation = (
                region_3d.view_rotation
                @ Quaternion(
                    (0.0, 0.0, 1.0),
                    3.141592653589793
                )
            )

            if context.area:
                context.area.tag_redraw()

        except Exception as e:

            print(
                "Navigation - Invert:",
                e
            )

    def draw(self, context):

        self.draw_button_background()

        x = self.matrix_world[0][3]
        y = self.matrix_world[1][3]

        draw_letter_icon(
            x,
            y,
            "I",
            ICON_SIZE,
            self.get_icon_color()
        )

    def draw_select(self, context, select_id=0):

        self.draw_preset_box(
            self.matrix_world,
            select_id=select_id
        )


# ---------------------------------------------------------
# GIZMO GROUP
# ---------------------------------------------------------

class NAVIGATION_CUSTOM_GGT(bpy.types.GizmoGroup):

    bl_idname = GROUP_ID
    bl_label = "Navigation"

    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'

    bl_options = set()

    @classmethod
    def poll(cls, context):

        return (
            context.area is not None
            and context.area.type == 'VIEW_3D'
        )

    def setup(self, context):

        self.maximize = self.gizmos.new(MAX_ID)
        self.maximize.scale_basis = 1.1
        self.maximize.use_tooltip = True

        self.frame = self.gizmos.new(FRAME_ID)
        self.frame.scale_basis = 1.1
        self.frame.use_tooltip = True

        self.quad = self.gizmos.new(QUAD_ID)
        self.quad.scale_basis = 1.1
        self.quad.use_tooltip = True

        self.lock = self.gizmos.new(LOCK_ID)
        self.lock.scale_basis = 1.1
        self.lock.use_tooltip = True

        self.front = self.gizmos.new(FRONT_ID)
        self.front.scale_basis = 1.1
        self.front.use_tooltip = True

        self.side = self.gizmos.new(SIDE_ID)
        self.side.scale_basis = 1.1
        self.side.use_tooltip = True

        self.top = self.gizmos.new(TOP_ID)
        self.top.scale_basis = 1.1
        self.top.use_tooltip = True

        self.invert = self.gizmos.new(INVERT_ID)
        self.invert.scale_basis = 1.1
        self.invert.use_tooltip = True

    def draw_prepare(self, context):

        region = context.region

        width = region.width
        height = region.height

        space = context.space_data

        region_quadviews = ()

        if space is not None:

            region_quadviews = getattr(
                space,
                "region_quadviews",
                ()
            )

        quad_view_active = len(region_quadviews) > 0

        # Check if the screen/area is in full screen mode (maximized or fullscreen)
        is_full_screen = (
            getattr(context.screen, "show_fullscreen", False) or
            getattr(context.area, "show_fullscreen", False)
        )

        # Detect the Sidebar and Asset Shelf through SpaceView3D when the
        # properties are available. This is more reliable on touch/Android
        # than relying on UI region dimensions, which can remain non-zero
        # even while the region is not actually visible.
        n_panel_open = False
        asset_shelf_open = False

        space = context.space_data

        if space is not None:
            n_panel_prop = getattr(space, "show_region_ui", None)
            shelf_prop = getattr(space, "show_region_asset_shelf", None)

            if n_panel_prop is not None:
                n_panel_open = bool(n_panel_prop)
            if shelf_prop is not None:
                asset_shelf_open = bool(shelf_prop)

        # Fallback for Blender builds that do not expose the SpaceView3D
        # visibility properties.
        if (
            (getattr(space, "show_region_ui", None) is None)
            or (getattr(space, "show_region_asset_shelf", None) is None)
        ) and context.area:
            for r in context.area.regions:
                if r.type == 'UI' and r.width > 1 and getattr(space, "show_region_ui", None) is None:
                    n_panel_open = True
                elif r.type == 'ASSET_SHELF' and r.height > 1 and getattr(space, "show_region_asset_shelf", None) is None:
                    asset_shelf_open = True

        # Hide all viewport controls whenever the N-panel or Asset Shelf is open.
        if n_panel_open or asset_shelf_open:
            self.maximize.hide = True
            self.frame.hide = True
            self.quad.hide = True
            self.lock.hide = True
            self.front.hide = True
            self.side.hide = True
            self.top.hide = True
            self.invert.hide = True
            return

        scale = _viewport_scale()
        step = 45 * scale

        # =================================================
        # NORMAL / FULL SCREEN VIEW
        # =================================================

        if not quad_view_active:

            x = width - (30 * scale)

            # Lower position.
            center_y = height * 0.20

            self.maximize.matrix_basis = Matrix.Translation(
                (x, center_y + step, 0)
            )

            self.frame.matrix_basis = Matrix.Translation(
                (x, center_y, 0)
            )

            self.quad.matrix_basis = Matrix.Translation(
                (x, center_y - step, 0)
            )

            # Disable Maximize / Restore Areas while already in full screen.
            self.maximize.hide = bool(is_full_screen)
            self.frame.hide = False
            self.quad.hide = False

            self.lock.hide = True
            self.front.hide = True
            self.side.hide = True
            self.top.hide = True
            self.invert.hide = True

            return

        # =================================================
        # QUAD VIEW
        # =================================================

        y = 30 * scale

        total_buttons = 8
        horizontal_step = 45 * scale

        center_x = width * 0.5

        start_x = center_x - (
            horizontal_step *
            (total_buttons - 1) /
            2
        )

        self.maximize.matrix_basis = Matrix.Translation(
            (start_x, y, 0)
        )

        self.frame.matrix_basis = Matrix.Translation(
            (start_x + horizontal_step, y, 0)
        )

        self.quad.matrix_basis = Matrix.Translation(
            (start_x + horizontal_step * 2, y, 0)
        )

        self.lock.matrix_basis = Matrix.Translation(
            (start_x + horizontal_step * 3, y, 0)
        )

        self.front.matrix_basis = Matrix.Translation(
            (start_x + horizontal_step * 4, y, 0)
        )

        self.side.matrix_basis = Matrix.Translation(
            (start_x + horizontal_step * 5, y, 0)
        )

        self.top.matrix_basis = Matrix.Translation(
            (start_x + horizontal_step * 6, y, 0)
        )

        self.invert.matrix_basis = Matrix.Translation(
            (start_x + horizontal_step * 7, y, 0)
        )

        # No Maximize / Restore Areas button in Quad View.
        # Keep Frame and Quad View exactly as they are.
        self.maximize.hide = True
        self.frame.hide = False
        self.quad.hide = False
        self.lock.hide = False

        # -------------------------------------------------
        # Lock Rotation
        # -------------------------------------------------

        locked = False

        region_3d = context.region_data

        if region_3d is not None:

            if hasattr(region_3d, "lock_rotation"):
                locked = region_3d.lock_rotation

        self.front.hide = locked
        self.side.hide = locked
        self.top.hide = locked
        self.invert.hide = locked

        # -------------------------------------------------
        # Axis selection state
        # -------------------------------------------------

        if self.front.clicked:
            self.side.clicked = False
            self.top.clicked = False

        elif self.side.clicked:
            self.front.clicked = False
            self.top.clicked = False

        elif self.top.clicked:
            self.front.clicked = False
            self.side.clicked = False



# ---------------------------------------------------------
# TOUCHSCREEN MODULE REGISTER
# ---------------------------------------------------------

classes = (
    NAVIGATION_MAX_GT,
    NAVIGATION_FRAME_GT,
    NAVIGATION_QUAD_GT,
    NAVIGATION_LOCK_GT,
    NAVIGATION_FRONT_GT,
    NAVIGATION_SIDE_GT,
    NAVIGATION_TOP_GT,
    NAVIGATION_INVERT_GT,
    NAVIGATION_CUSTOM_GGT,
)


def _ensure_gizmo_groups():
    wm = bpy.context.window_manager
    for window in wm.windows:
        screen = window.screen
        if screen is None:
            continue
        for area in screen.areas:
            if area.type != 'VIEW_3D':
                continue
            try:
                with bpy.context.temp_override(window=window, area=area):
                    wm.gizmo_group_type_ensure(GROUP_ID)
            except Exception as e:
                print("Touchscreen - Viewport Controls ensure:", e)


def _ensure_gizmo_timer():
    # The addon can be enabled while Blender is rebuilding the screen.
    # Give the VIEW_3D areas one redraw cycle, then ensure the group again.
    _ensure_gizmo_groups()
    return None


def register():
    # Important: the original standalone NewGizmo explicitly unregistered
    # before registering. Keep that behavior for reliable module reloads.
    try:
        unregister()
    except Exception:
        pass

    for cls in classes:
        bpy.utils.register_class(cls)

    _ensure_gizmo_groups()

    # Also retry once after the current registration/update cycle.
    try:
        bpy.app.timers.register(_ensure_gizmo_timer, first_interval=0.1)
    except Exception:
        pass

    print("Touchscreen - Viewport Controls registered")


def unregister():
    try:
        bpy.context.window_manager.gizmo_group_type_unlink_delayed(GROUP_ID)
    except Exception:
        pass

    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass
