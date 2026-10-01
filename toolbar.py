# SPDX-License-Identifier: GPL-3.0-or-later

import bpy
import bmesh

from bpy.types import Operator, Menu
from bl_ui.space_toolsystem_common import ToolSelectPanelHelper


# =========================================================
# NATIVE BLENDER TOOLBAR LAYOUT
# =========================================================

_ORIGINAL_LAYOUT_GENERATOR = None


def _get_preferences():
    addon = bpy.context.preferences.addons.get(__package__)
    if addon is None:
        return None
    return addon.preferences


def _toolbar_layout_mode(context):
    prefs = _get_preferences()

    if prefs is None or prefs.native_toolbar_layout == 'BLENDER':
        width = context.region.width

        if width <= 80:
            return 1, False
        elif width <= 120:
            return 2, False
        else:
            return 1, True

    width = context.region.width

    if width <= 80:
        return 1, False
    elif width <= 120:
        return 2, False
    elif width <= 160:
        return 3, False
    elif width <= 185:
        return 4, False
    else:
        return 1, True


def _patched_layout_generator(self, context, region):
    if _ORIGINAL_LAYOUT_GENERATOR is None:
        return

    prefs = _get_preferences()

    if prefs is None or prefs.native_toolbar_layout == 'BLENDER':
        yield from _ORIGINAL_LAYOUT_GENERATOR(self, context, region)
        return

    yield from _ORIGINAL_LAYOUT_GENERATOR(self, context, region)


def update_native_toolbar_layout():
    global _ORIGINAL_LAYOUT_GENERATOR

    if _ORIGINAL_LAYOUT_GENERATOR is None:
        return

    # Force Blender to rebuild the toolbar.
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        if screen is None:
            continue

        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


# =========================================================
# BASIC OPERATORS
# =========================================================

class VIEW3D_OT_delete_menu(Operator):
    bl_idname = "view3d.delete_menu"
    bl_label = "Delete"

    def execute(self, context):
        bpy.ops.view3d.view_selected()
        return {'FINISHED'}


class VIEW3D_OT_favorites_menu(Operator):
    bl_idname = "view3d.favorites_menu"
    bl_label = "Quick Favorites"

    def execute(self, context):
        bpy.ops.wm.call_menu(name="VIEW3D_MT_favorites")
        return {'FINISHED'}


class VIEW3D_OT_simple_undo(Operator):
    bl_idname = "view3d.simple_undo"
    bl_label = "Undo"

    def execute(self, context):
        bpy.ops.ed.undo()
        return {'FINISHED'}


class VIEW3D_OT_simple_redo(Operator):
    bl_idname = "view3d.simple_redo"
    bl_label = "Redo"

    def execute(self, context):
        bpy.ops.ed.redo()
        return {'FINISHED'}


class VIEW3D_OT_simple_repeat_last(Operator):
    bl_idname = "view3d.simple_repeat_last"
    bl_label = "Repeat Last"

    def execute(self, context):
        bpy.ops.screen.repeat_last()
        return {'FINISHED'}


class VIEW3D_OT_simple_undo_history(Operator):
    bl_idname = "view3d.simple_undo_history"
    bl_label = "History"

    def execute(self, context):
        bpy.ops.ed.undo_history()
        return {'FINISHED'}


# =========================================================
# EDIT MODE MENUS
# =========================================================

class VIEW3D_MT_touchscreen_edit_select(Menu):
    bl_label = "Select"

    def draw(self, context):
        layout = self.layout

        layout.operator(
            "mesh.select_all",
            text="Select All",
            icon='SELECT_SET'
        )

        layout.separator()

        layout.operator(
            "mesh.loop_multi_select",
            text="Edge Loops",
            icon='EDGESEL'
        ).ring = False

        layout.operator(
            "mesh.loop_multi_select",
            text="Edge Rings",
            icon='EDGESEL'
        ).ring = True

        layout.operator(
            "mesh.region_to_loop",
            text="Boundary of Selected",
            icon='EDGESEL'
        )

        layout.operator(
            "view3d.touchscreen_shortest_path",
            text="Shortest Path",
            icon='EDGESEL'
        )

        layout.operator(
            "mesh.select_mirror",
            text="Select Mirror",
            icon='MOD_MIRROR'
        )

        layout.operator(
            "mesh.select_nth",
            text="Inner Region",
            icon='SELECT_EXTEND'
        )

        layout.operator(
            "mesh.select_linked",
            text="Select Linked",
            icon='LINKED'
        )


class VIEW3D_OT_edit_select_menu(Operator):
    bl_idname = "view3d.edit_select_menu"
    bl_label = "Select"

    def execute(self, context):
        bpy.ops.wm.call_menu(
            name="VIEW3D_MT_touchscreen_edit_select"
        )
        return {'FINISHED'}


# =========================================================
# SHORTEST PATH
# =========================================================

class VIEW3D_OT_touchscreen_shortest_path(Operator):
    bl_idname = "view3d.touchscreen_shortest_path"
    bl_label = "Shortest Path"

    @classmethod
    def poll(cls, context):
        obj = context.active_object

        return (
            obj is not None
            and obj.type == 'MESH'
            and context.mode == 'EDIT_MESH'
        )

    def execute(self, context):
        obj = context.active_object

        if obj is None or obj.type != 'MESH':
            return {'CANCELLED'}

        mesh = obj.data

        bm = bmesh.from_edit_mesh(mesh)

        selected_verts = [v for v in bm.verts if v.select]
        selected_edges = [e for e in bm.edges if e.select]
        selected_faces = [f for f in bm.faces if f.select]

        # Exactly two vertices.
        if len(selected_verts) == 2:
            a, b = selected_verts

            if a == b:
                return {'CANCELLED'}

            # Already directly connected.
            if bm.edges.get((a, b)) is not None:
                return {'CANCELLED'}

            bpy.ops.mesh.shortest_path_select()
            return {'FINISHED'}

        # Exactly two edges.
        if len(selected_edges) == 2:
            a, b = selected_edges

            if a == b:
                return {'CANCELLED'}

            # Edges sharing a vertex are already connected.
            if (
                a.verts[0] in b.verts
                or a.verts[1] in b.verts
            ):
                return {'CANCELLED'}

            bpy.ops.mesh.shortest_path_select()
            return {'FINISHED'}

        # Exactly two faces.
        if len(selected_faces) == 2:
            a, b = selected_faces

            if a == b:
                return {'CANCELLED'}

            # Faces sharing an edge are already connected.
            if any(edge in b.edges for edge in a.edges):
                return {'CANCELLED'}

            bpy.ops.mesh.shortest_path_select()
            return {'FINISHED'}

        # Anything else: do nothing.
        return {'CANCELLED'}


# =========================================================
# UV
# =========================================================

class VIEW3D_MT_touchscreen_uv(Menu):
    bl_label = "UV"

    def draw(self, context):
        layout = self.layout

        layout.operator(
            "uv.unwrap",
            text="Unwrap",
            icon='MOD_UVPROJECT'
        )

        layout.operator(
            "uv.smart_project",
            text="Smart UV Project",
            icon='UV'
        )


class VIEW3D_OT_uv_menu(Operator):
    bl_idname = "view3d.uv_menu"
    bl_label = "UV"

    def execute(self, context):
        bpy.ops.wm.call_menu(
            name="VIEW3D_MT_touchscreen_uv"
        )
        return {'FINISHED'}


# =========================================================
# FILL
# =========================================================

class VIEW3D_MT_touchscreen_fill(Menu):
    bl_label = "Fill"

    def draw(self, context):
        layout = self.layout

        layout.operator(
            "mesh.edge_face_add",
            text="Make Face",
            icon='MESH_FACE'
        )

        layout.operator(
            "mesh.fill",
            text="Fill",
            icon='MESH_GRID'
        )

        layout.operator(
            "mesh.fill_grid",
            text="Grid Fill",
            icon='MESH_GRID'
        )

        layout.operator(
            "mesh.fill_holes",
            text="Fill Holes",
            icon='MESH_GRID'
        )


class VIEW3D_OT_fill_menu(Operator):
    bl_idname = "view3d.fill_menu"
    bl_label = "Fill"

    def execute(self, context):
        bpy.ops.wm.call_menu(
            name="VIEW3D_MT_touchscreen_fill"
        )
        return {'FINISHED'}


# =========================================================
# SEPARATE
# =========================================================

class VIEW3D_MT_touchscreen_separate(Menu):
    bl_label = "Separate"

    def draw(self, context):
        layout = self.layout

        layout.operator(
            "mesh.separate",
            text="Selection",
            icon='RESTRICT_COLOR_OFF'
        ).type = 'SELECTED'

        layout.operator(
            "mesh.separate",
            text="By Material",
            icon='MATERIAL'
        ).type = 'MATERIAL'

        layout.operator(
            "mesh.separate",
            text="By Loose Parts",
            icon='MESH_DATA'
        ).type = 'LOOSE'


class VIEW3D_OT_separate_menu(Operator):
    bl_idname = "view3d.separate_menu"
    bl_label = "Separate"

    def execute(self, context):
        bpy.ops.wm.call_menu(
            name="VIEW3D_MT_touchscreen_separate"
        )
        return {'FINISHED'}


# =========================================================
# POSE MODE
# =========================================================

class VIEW3D_MT_touchscreen_pose_copy(Menu):
    bl_label = "Copy"

    def draw(self, context):
        layout = self.layout

        layout.operator(
            "pose.copy",
            text="Copy Selected",
            icon='COPYDOWN'
        )

        layout.operator(
            "pose.copy",
            text="Copy as Asset",
            icon='ASSET_MANAGER'
        )


class VIEW3D_OT_pose_copy_menu(Operator):
    bl_idname = "view3d.pose_copy_menu"
    bl_label = "Copy"

    def execute(self, context):
        bpy.ops.wm.call_menu(
            name="VIEW3D_MT_touchscreen_pose_copy"
        )
        return {'FINISHED'}


class VIEW3D_MT_touchscreen_pose_paste(Menu):
    bl_label = "Paste"

    def draw(self, context):
        layout = self.layout

        layout.operator(
            "pose.paste",
            text="Paste Pose",
            icon='PASTEDOWN'
        )

        layout.operator(
            "pose.paste",
            text="Paste Pose Flipped",
            icon='PASTEDOWN'
        ).flipped = True

        layout.operator(
            "pose.paste",
            text="Paste Pose Relative",
            icon='PASTEDOWN'
        ).relative = True


class VIEW3D_OT_pose_paste_menu(Operator):
    bl_idname = "view3d.pose_paste_menu"
    bl_label = "Paste"

    def execute(self, context):
        bpy.ops.wm.call_menu(
            name="VIEW3D_MT_touchscreen_pose_paste"
        )
        return {'FINISHED'}


# =========================================================
# TOOLBAR DRAW
# =========================================================

def _draw_button(layout, item, show_text=False):
    operator_id, icon, label, properties = item

    if operator_id.startswith("view3d."):
        op = layout.operator(
            operator_id,
            text=label if show_text else "",
            icon=icon
        )
    else:
        op = layout.operator(
            operator_id,
            text=label if show_text else "",
            icon=icon
        )

    for prop, value in properties.items():
        try:
            setattr(op, prop, value)
        except Exception:
            pass


def _draw_toolbar_items(layout, groups, columns, show_text):
    if show_text:
        column = layout.column(align=True)
        column.scale_y = 2.0

        for group in groups:
            for item in group:
                _draw_button(column, item, True)

        return

    # Explicit rows instead of grid_flow.
    #
    # This prevents Blender from distributing extra width
    # between buttons when using 3 or 4 columns.
    items = [
        item
        for group in groups
        for item in group
    ]

    for start in range(0, len(items), columns):
        row = layout.row(align=True)
        row.alignment = 'LEFT'
        row.scale_y = 2.0

        for item in items[start:start + columns]:
            _draw_button(row, item, False)


def draw_toolbar(context, layout):
    mode = context.mode
    columns, show_text = _toolbar_layout_mode(context)

    # -----------------------------------------------------
    # OBJECT MODE
    # -----------------------------------------------------

    if mode == 'OBJECT':
        groups = [
            [
                ('object.delete', 'TRASH', 'Delete', {}),
                ('object.duplicate', 'DUPLICATE', 'Duplicate', {}),
            ],
            [
                ('view3d.favorites_menu', 'SOLO_OFF', 'Quick Favorites', {}),
                ('view3d.simple_undo', 'LOOP_BACK', 'Undo', {}),
            ],
            [
                ('view3d.simple_redo', 'LOOP_FORWARDS', 'Redo', {}),
                ('view3d.simple_repeat_last', 'RECOVER_LAST', 'Repeat Last', {}),
            ],
            [
                ('view3d.simple_undo_history', 'HELP', 'History', {}),
            ],
        ]

    # -----------------------------------------------------
    # EDIT MESH
    # -----------------------------------------------------

    elif mode == 'EDIT_MESH':
        groups = [
            [
                ('view3d.delete_menu', 'TRASH', 'Delete', {}),
                (
                    'view3d.edit_select_menu',
                    'SELECT_SET',
                    'Select',
                    {}
                ),
            ],
            [
                ('view3d.uv_menu', 'MOD_UVPROJECT', 'UV', {}),
            ],
            [
                ('view3d.favorites_menu', 'SOLO_OFF', 'Quick Favorites', {}),
                ('view3d.fill_menu', 'MESH_GRID', 'Fill', {}),
            ],
            [
                ('view3d.separate_menu', 'RESTRICT_COLOR_OFF', 'Separate', {}),
                ('view3d.simple_undo', 'LOOP_BACK', 'Undo', {}),
            ],
            [
                ('view3d.simple_redo', 'LOOP_FORWARDS', 'Redo', {}),
                ('view3d.simple_repeat_last', 'RECOVER_LAST', 'Repeat Last', {}),
            ],
            [
                ('view3d.simple_undo_history', 'HELP', 'History', {}),
            ],
        ]

    # -----------------------------------------------------
    # POSE
    # -----------------------------------------------------

    elif mode == 'POSE':
        groups = [
            [
                ('view3d.simple_undo', 'LOOP_BACK', 'Undo', {}),
                ('view3d.simple_redo', 'LOOP_FORWARDS', 'Redo', {}),
            ],
            [
                ('view3d.pose_copy_menu', 'COPYDOWN', 'Copy', {}),
                ('view3d.pose_paste_menu', 'PASTEDOWN', 'Paste', {}),
            ],
            [
                ('view3d.simple_repeat_last', 'RECOVER_LAST', 'Repeat Last', {}),
            ],
            [
                ('view3d.simple_undo_history', 'HELP', 'History', {}),
            ],
        ]

    # -----------------------------------------------------
    # OTHER MODES
    # -----------------------------------------------------

    else:
        groups = [
            [
                ('view3d.favorites_menu', 'SOLO_OFF', 'Quick Favorites', {}),
                ('view3d.simple_undo', 'LOOP_BACK', 'Undo', {}),
            ],
            [
                ('view3d.simple_redo', 'LOOP_FORWARDS', 'Redo', {}),
                ('view3d.simple_repeat_last', 'RECOVER_LAST', 'Repeat Last', {}),
            ],
            [
                ('view3d.simple_undo_history', 'HELP', 'History', {}),
            ],
        ]

    _draw_toolbar_items(
        layout,
        groups,
        columns,
        show_text
    )


# =========================================================
# TOOL SYSTEM PATCH
# =========================================================

def _touchscreen_toolbar_draw(self, context):
    layout = self.layout
    draw_toolbar(context, layout)


# =========================================================
# REGISTRATION
# =========================================================

CLASSES = (
    VIEW3D_OT_delete_menu,
    VIEW3D_OT_favorites_menu,
    VIEW3D_OT_simple_undo,
    VIEW3D_OT_simple_redo,
    VIEW3D_OT_simple_repeat_last,
    VIEW3D_OT_simple_undo_history,

    VIEW3D_MT_touchscreen_edit_select,
    VIEW3D_OT_edit_select_menu,
    VIEW3D_OT_touchscreen_shortest_path,

    VIEW3D_MT_touchscreen_uv,
    VIEW3D_OT_uv_menu,

    VIEW3D_MT_touchscreen_fill,
    VIEW3D_OT_fill_menu,

    VIEW3D_MT_touchscreen_separate,
    VIEW3D_OT_separate_menu,

    VIEW3D_MT_touchscreen_pose_copy,
    VIEW3D_OT_pose_copy_menu,

    VIEW3D_MT_touchscreen_pose_paste,
    VIEW3D_OT_pose_paste_menu,
)


def register():
    global _ORIGINAL_LAYOUT_GENERATOR

    for cls in CLASSES:
        bpy.utils.register_class(cls)

    if _ORIGINAL_LAYOUT_GENERATOR is None:
        _ORIGINAL_LAYOUT_GENERATOR = (
            ToolSelectPanelHelper._layout_generator_detect_from_region
        )

        ToolSelectPanelHelper._layout_generator_detect_from_region = (
            _patched_layout_generator
        )

    for window in bpy.context.window_manager.windows:
        screen = window.screen

        if screen is None:
            continue

        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


def unregister():
    global _ORIGINAL_LAYOUT_GENERATOR

    if _ORIGINAL_LAYOUT_GENERATOR is not None:
        ToolSelectPanelHelper._layout_generator_detect_from_region = (
            _ORIGINAL_LAYOUT_GENERATOR
        )

        _ORIGINAL_LAYOUT_GENERATOR = None

    for cls in reversed(CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass