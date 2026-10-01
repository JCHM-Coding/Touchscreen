# SPDX-License-Identifier: GPL-3.0-or-later
#
# Touchscreen - Toolbar
# Copyright (C) 2026
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import bpy
import bmesh

from bl_ui.space_toolsystem_common import ToolSelectPanelHelper


_ORIGINAL_LAYOUT_DETECT = None
_PATCH_INSTALLED = False
_PATCH_MARKER = "_touchscreen_original_layout_detect"


# ------------------------------------------------------------------------
# PREFERENCES
# ------------------------------------------------------------------------

def _get_preferences():
    try:
        addon_name = __package__.split(".")[0]
        addon = bpy.context.preferences.addons.get(addon_name)

        if addon is None:
            return None

        return addon.preferences

    except Exception:
        return None


# ------------------------------------------------------------------------
# NATIVE BLENDER TOOLBAR LAYOUT
# ------------------------------------------------------------------------

def _native_toolbar_layout_detect(layout, region, scale_y):
    try:
        space = bpy.context.space_data

        if (
            space is None
            or space.type != 'VIEW_3D'
        ):
            return _ORIGINAL_LAYOUT_DETECT.__get__(
                None,
                ToolSelectPanelHelper
            )(layout, region, scale_y)

    except Exception:
        return _ORIGINAL_LAYOUT_DETECT.__get__(
            None,
            ToolSelectPanelHelper
        )(layout, region, scale_y)

    prefs = _get_preferences()

    if (
        prefs is None
        or getattr(
            prefs,
            "native_toolbar_layout",
            "BLENDER"
        ) != '4_COLUMNS'
    ):
        return _ORIGINAL_LAYOUT_DETECT.__get__(
            None,
            ToolSelectPanelHelper
        )(layout, region, scale_y)

    try:
        system = bpy.context.preferences.system
        view2d = region.view2d

        view2d_scale = (
            view2d.region_to_view(1.0, 0.0)[0]
            -
            view2d.region_to_view(0.0, 0.0)[0]
        )

        width_scale = (
            region.width *
            view2d_scale /
            system.ui_scale
        )

    except (
        AttributeError,
        RuntimeError,
        ZeroDivisionError
    ):
        width_scale = region.width

    # Touchscreen automatic layout:
    #
    # 1 column
    # 2 columns
    # 3 columns
    # 4 columns
    # 1 column + text
    #
    if width_scale <= 80.0:
        column_count = 1
        show_text = False

    elif width_scale <= 120.0:
        column_count = 2
        show_text = False

    elif width_scale <= 160.0:
        column_count = 3
        show_text = False

    elif width_scale <= 185.0:
        column_count = 4
        show_text = False

    else:
        column_count = 1
        show_text = True

    if column_count == 1:
        ui_gen = (
            ToolSelectPanelHelper
            ._layout_generator_single_column(
                layout,
                scale_y=scale_y
            )
        )

    else:
        ui_gen = (
            ToolSelectPanelHelper
            ._layout_generator_multi_columns(
                layout,
                column_count=column_count,
                scale_y=scale_y
            )
        )

    return ui_gen, show_text


def _install_native_toolbar_patch():
    global _ORIGINAL_LAYOUT_DETECT
    global _PATCH_INSTALLED

    if _PATCH_INSTALLED:
        return

    existing_original = (
        ToolSelectPanelHelper.__dict__.get(
            _PATCH_MARKER
        )
    )

    if existing_original is not None:
        _ORIGINAL_LAYOUT_DETECT = existing_original

    else:
        _ORIGINAL_LAYOUT_DETECT = (
            ToolSelectPanelHelper.__dict__.get(
                "_layout_generator_detect_from_region"
            )
        )

        if _ORIGINAL_LAYOUT_DETECT is None:
            return

        setattr(
            ToolSelectPanelHelper,
            _PATCH_MARKER,
            _ORIGINAL_LAYOUT_DETECT
        )

    ToolSelectPanelHelper._layout_generator_detect_from_region = (
        staticmethod(
            _native_toolbar_layout_detect
        )
    )

    _PATCH_INSTALLED = True


def _remove_native_toolbar_patch():
    global _ORIGINAL_LAYOUT_DETECT
    global _PATCH_INSTALLED

    existing_original = (
        ToolSelectPanelHelper.__dict__.get(
            _PATCH_MARKER
        )
    )

    if existing_original is not None:
        ToolSelectPanelHelper._layout_generator_detect_from_region = (
            existing_original
        )

        try:
            delattr(
                ToolSelectPanelHelper,
                _PATCH_MARKER
            )
        except AttributeError:
            pass

    elif _ORIGINAL_LAYOUT_DETECT is not None:
        ToolSelectPanelHelper._layout_generator_detect_from_region = (
            _ORIGINAL_LAYOUT_DETECT
        )

    _ORIGINAL_LAYOUT_DETECT = None
    _PATCH_INSTALLED = False


def update_native_toolbar_layout():
    prefs = _get_preferences()

    if prefs is None:
        return

    if (
        getattr(
            prefs,
            "toolbar",
            True
        )
        and
        prefs.native_toolbar_layout == '4_COLUMNS'
    ):
        _install_native_toolbar_patch()

    else:
        _remove_native_toolbar_patch()

    try:
        for screen in bpy.data.screens:
            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()

    except Exception:
        pass


# ------------------------------------------------------------------------
# DELETE
# ------------------------------------------------------------------------

class VIEW3D_OT_simple_delete(bpy.types.Operator):
    bl_idname = "view3d.simple_delete"
    bl_label = "Delete"

    @classmethod
    def poll(cls, context):
        return context.mode in {
            'OBJECT',
            'EDIT_MESH',
            'EDIT_CURVE',
            'EDIT_ARMATURE'
        }

    def execute(self, context):
        try:
            if context.mode == 'OBJECT':
                bpy.ops.object.delete()

            elif context.mode == 'EDIT_MESH':
                bpy.ops.mesh.delete(type='VERT')

            elif context.mode == 'EDIT_CURVE':
                bpy.ops.curve.delete()

            elif context.mode == 'EDIT_ARMATURE':
                bpy.ops.armature.delete()

        except RuntimeError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        return {'FINISHED'}


class VIEW3D_OT_delete_menu(bpy.types.Operator):
    bl_idname = "view3d.delete_menu"
    bl_label = "Delete"

    def execute(self, context):
        menus = {
            'EDIT_MESH': 'VIEW3D_MT_edit_mesh_delete',
            'EDIT_CURVE': 'VIEW3D_MT_edit_curve_delete',
            'EDIT_ARMATURE': 'VIEW3D_MT_edit_armature_delete',
        }

        menu = menus.get(context.mode)

        if menu:
            bpy.ops.wm.call_menu(name=menu)

        else:
            bpy.ops.view3d.simple_delete()

        return {'FINISHED'}


# ------------------------------------------------------------------------
# DUPLICATE
# ------------------------------------------------------------------------

class VIEW3D_OT_simple_duplicate(bpy.types.Operator):
    bl_idname = "view3d.simple_duplicate"
    bl_label = "Duplicate"

    def execute(self, context):
        bpy.ops.object.duplicate(linked=False)
        return {'FINISHED'}


class VIEW3D_OT_simple_duplicate_linked(bpy.types.Operator):
    bl_idname = "view3d.simple_duplicate_linked"
    bl_label = "Duplicate Linked"

    def execute(self, context):
        bpy.ops.object.duplicate(linked=True)
        return {'FINISHED'}


class VIEW3D_MT_touchscreen_duplicate(bpy.types.Menu):
    bl_idname = "VIEW3D_MT_touchscreen_duplicate"
    bl_label = "Duplicate"

    def draw(self, context):
        layout = self.layout

        layout.operator(
            "view3d.simple_duplicate",
            text="Duplicate",
            icon='ONIONSKIN_ON'
        )

        layout.operator(
            "view3d.simple_duplicate_linked",
            text="Duplicate Linked",
            icon='ONIONSKIN_ON'
        )


class VIEW3D_OT_duplicate_menu(bpy.types.Operator):
    bl_idname = "view3d.duplicate_menu"
    bl_label = "Duplicate"

    def execute(self, context):
        bpy.ops.wm.call_menu(
            name="VIEW3D_MT_touchscreen_duplicate"
        )

        return {'FINISHED'}


# ------------------------------------------------------------------------
# QUICK FAVORITES
# ------------------------------------------------------------------------

class VIEW3D_MT_touchscreen_favorites(bpy.types.Menu):
    bl_idname = "VIEW3D_MT_touchscreen_favorites"
    bl_label = "Quick Favorites"

    def draw(self, context):
        self.layout.menu_contents(
            "SCREEN_MT_user_menu"
        )


class VIEW3D_OT_favorites_menu(bpy.types.Operator):
    bl_idname = "view3d.favorites_menu"
    bl_label = "Quick Favorites"

    def execute(self, context):
        bpy.ops.wm.call_menu(
            name="VIEW3D_MT_touchscreen_favorites"
        )

        return {'FINISHED'}


# ------------------------------------------------------------------------
# JOIN
# ------------------------------------------------------------------------

class VIEW3D_OT_simple_join(bpy.types.Operator):
    bl_idname = "view3d.simple_join"
    bl_label = "Join"

    @classmethod
    def poll(cls, context):
        return (
            context.mode == 'OBJECT'
            and context.active_object is not None
            and len(context.selected_objects) >= 2
        )

    def execute(self, context):
        bpy.ops.object.join()
        return {'FINISHED'}


# ------------------------------------------------------------------------
# UNDO / REDO / HISTORY
# ------------------------------------------------------------------------

class VIEW3D_OT_simple_undo(bpy.types.Operator):
    bl_idname = "view3d.simple_undo"
    bl_label = "Undo"

    @classmethod
    def poll(cls, context):
        try:
            return bpy.ops.ed.undo.poll()
        except RuntimeError:
            return False

    def execute(self, context):
        try:
            if not bpy.ops.ed.undo.poll():
                return {'CANCELLED'}

            bpy.ops.ed.undo()

        except RuntimeError:
            return {'CANCELLED'}

        return {'FINISHED'}


class VIEW3D_OT_simple_redo(bpy.types.Operator):
    bl_idname = "view3d.simple_redo"
    bl_label = "Redo"

    @classmethod
    def poll(cls, context):
        try:
            return bpy.ops.ed.redo.poll()
        except RuntimeError:
            return False

    def execute(self, context):
        try:
            if not bpy.ops.ed.redo.poll():
                return {'CANCELLED'}

            bpy.ops.ed.redo()

        except RuntimeError:
            return {'CANCELLED'}

        return {'FINISHED'}


class VIEW3D_OT_simple_undo_history(bpy.types.Operator):
    bl_idname = "view3d.simple_undo_history"
    bl_label = "History"

    def invoke(self, context, event):
        return bpy.ops.ed.undo_history(
            'INVOKE_DEFAULT'
        )


# ------------------------------------------------------------------------
# REPEAT LAST
# ------------------------------------------------------------------------

class VIEW3D_OT_simple_repeat_last(bpy.types.Operator):
    bl_idname = "view3d.simple_repeat_last"
    bl_label = "Repeat Last"

    def execute(self, context):
        try:
            if not bpy.ops.screen.repeat_last.poll():
                return {'CANCELLED'}

            bpy.ops.screen.repeat_last()

        except (RuntimeError, AttributeError):
            return {'CANCELLED'}

        return {'FINISHED'}


# ------------------------------------------------------------------------
# FILL
# ------------------------------------------------------------------------

class VIEW3D_MT_touchscreen_fill(bpy.types.Menu):
    bl_idname = "VIEW3D_MT_touchscreen_fill"
    bl_label = "Fill"

    def draw(self, context):
        layout = self.layout

        layout.operator(
            "mesh.fill",
            text="Fill"
        )

        layout.operator(
            "mesh.fill_grid",
            text="Grid Fill"
        )

        layout.operator(
            "mesh.bridge_edge_loops",
            text="Bridge Edge Loops"
        )


class VIEW3D_OT_fill_menu(bpy.types.Operator):
    bl_idname = "view3d.fill_menu"
    bl_label = "Fill"

    def execute(self, context):
        bpy.ops.wm.call_menu(
            name="VIEW3D_MT_touchscreen_fill"
        )

        return {'FINISHED'}


# ------------------------------------------------------------------------
# SEPARATE
# ------------------------------------------------------------------------

class VIEW3D_MT_touchscreen_separate(bpy.types.Menu):
    bl_idname = "VIEW3D_MT_touchscreen_separate"
    bl_label = "Separate"

    def draw(self, context):
        layout = self.layout

        op = layout.operator(
            "mesh.separate",
            text="Selection"
        )
        op.type = 'SELECTED'

        op = layout.operator(
            "mesh.separate",
            text="Material"
        )
        op.type = 'MATERIAL'

        op = layout.operator(
            "mesh.separate",
            text="Loose Parts"
        )
        op.type = 'LOOSE'


class VIEW3D_OT_separate_menu(bpy.types.Operator):
    bl_idname = "view3d.separate_menu"
    bl_label = "Separate"

    def execute(self, context):
        bpy.ops.wm.call_menu(
            name="VIEW3D_MT_touchscreen_separate"
        )

        return {'FINISHED'}


# ------------------------------------------------------------------------
# SHOW / HIDE
# ------------------------------------------------------------------------

class VIEW3D_MT_touchscreen_show_hide(bpy.types.Menu):
    bl_idname = "VIEW3D_MT_touchscreen_show_hide"
    bl_label = "Show/Hide"

    def draw(self, context):
        layout = self.layout

        op = layout.operator(
            "object.hide_view_set",
            text="Hide Selected"
        )
        op.unselected = False

        op = layout.operator(
            "object.hide_view_set",
            text="Hide Unselected"
        )
        op.unselected = True

        layout.operator(
            "object.hide_view_clear",
            text="Show All"
        )


class VIEW3D_OT_show_hide_menu(bpy.types.Operator):
    bl_idname = "view3d.show_hide_menu"
    bl_label = "Show/Hide"

    def execute(self, context):
        bpy.ops.wm.call_menu(
            name="VIEW3D_MT_touchscreen_show_hide"
        )

        return {'FINISHED'}


# ------------------------------------------------------------------------
# CLEAR SEAM
# ------------------------------------------------------------------------

class VIEW3D_OT_touchscreen_clear_seam(bpy.types.Operator):
    bl_idname = "view3d.touchscreen_clear_seam"
    bl_label = "Clear Seam"

    @classmethod
    def poll(cls, context):
        return (
            context.mode == 'EDIT_MESH'
            and context.active_object is not None
        )

    def execute(self, context):
        try:
            bpy.ops.mesh.mark_seam(clear=True)

        except (RuntimeError, AttributeError):
            return {'CANCELLED'}

        return {'FINISHED'}


# ------------------------------------------------------------------------
# UNWRAP
# ------------------------------------------------------------------------

class VIEW3D_MT_touchscreen_unwrap(bpy.types.Menu):
    bl_idname = "VIEW3D_MT_touchscreen_unwrap"
    bl_label = "Unwrap"

    def draw(self, context):
        layout = self.layout

        layout.operator(
            "uv.unwrap",
            text="Unwrap"
        )

        layout.operator(
            "uv.smart_project",
            text="Smart UV Project"
        )

        layout.operator(
            "uv.project_from_view",
            text="Project From View"
        )


# ------------------------------------------------------------------------
# UV MENU
# ------------------------------------------------------------------------

class VIEW3D_MT_touchscreen_uv(bpy.types.Menu):
    bl_idname = "VIEW3D_MT_touchscreen_uv"
    bl_label = "UV"

    def draw(self, context):
        layout = self.layout

        layout.operator(
            "uv.mark_seam",
            text="Mark Seam"
        )

        layout.operator(
            "view3d.touchscreen_clear_seam",
            text="Clear Seam"
        )

        layout.menu(
            "VIEW3D_MT_touchscreen_unwrap",
            text="Unwrap"
        )


class VIEW3D_OT_uv_menu(bpy.types.Operator):
    bl_idname = "view3d.uv_menu"
    bl_label = "UV"

    def execute(self, context):
        bpy.ops.wm.call_menu(
            name="VIEW3D_MT_touchscreen_uv"
        )

        return {'FINISHED'}


# ------------------------------------------------------------------------
# EDIT MODE - SELECT
# ------------------------------------------------------------------------

class VIEW3D_MT_touchscreen_edit_select(bpy.types.Menu):
    bl_idname = "VIEW3D_MT_touchscreen_edit_select"
    bl_label = "Select"

    def draw(self, context):
        layout = self.layout

        # Select All
        op = layout.operator(
            "mesh.select_all",
            text="Select All"
        )
        op.action = 'SELECT'

        # Select More / Less
        layout.operator(
            "mesh.select_more",
            text="Select More"
        )

        layout.operator(
            "mesh.select_less",
            text="Select Less"
        )

        layout.separator()

        # Edge Loops
        layout.operator(
            "mesh.select_edge_loop_multi",
            text="Edge Loops"
        )

        # Edge Rings
        layout.operator(
            "mesh.select_edge_ring_multi",
            text="Edge Rings"
        )

        # Shortest Path
        op = layout.operator(
            "mesh.shortest_path_select",
            text="Shortest Path"
        )
        op.edge_mode = 'SELECT'

        layout.separator()

        # Region to Loop
        layout.operator(
            "mesh.region_to_loop",
            text="Region to Loop"
        )

        # Loop to Region
        layout.operator(
            "mesh.loop_to_region",
            text="Loop to Region"
        )

        layout.separator()

        # Select Linked
        op = layout.operator(
            "mesh.select_linked",
            text="Select Linked"
        )
        op.delimit = set()


# ------------------------------------------------------------------------
# EDIT MODE - SELECT MENU OPERATOR
# ------------------------------------------------------------------------

class VIEW3D_OT_edit_select_menu(bpy.types.Operator):
    bl_idname = "view3d.edit_select_menu"
    bl_label = "Select"

    @classmethod
    def poll(cls, context):
        return (
            context.mode == 'EDIT_MESH'
            and context.active_object is not None
        )

    def execute(self, context):
        bpy.ops.wm.call_menu(
            name="VIEW3D_MT_touchscreen_edit_select"
        )

        return {'FINISHED'}


# ------------------------------------------------------------------------
# EDIT MODE - SHORTEST PATH
# ------------------------------------------------------------------------

class VIEW3D_OT_touchscreen_shortest_path(bpy.types.Operator):
    bl_idname = "view3d.touchscreen_shortest_path"
    bl_label = "Shortest Path"

    @classmethod
    def poll(cls, context):
        return (
            context.mode == 'EDIT_MESH'
            and context.active_object is not None
            and context.active_object.type == 'MESH'
        )

    def execute(self, context):
        obj = context.active_object

        if obj is None or obj.type != 'MESH':
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(obj.data)

        select_mode = tuple(
            context.tool_settings.mesh_select_mode
        )

        # --------------------------------------------------------------
        # Vertex mode
        # --------------------------------------------------------------

        if select_mode == (True, False, False):
            elements = [
                vert
                for vert in bm.verts
                if vert.select
            ]

            if len(elements) != 2:
                return {'CANCELLED'}

            first, second = elements

            connected = any(
                edge.other_vert(first) == second
                for edge in first.link_edges
            )

        # --------------------------------------------------------------
        # Edge mode
        # --------------------------------------------------------------

        elif select_mode == (False, True, False):
            elements = [
                edge
                for edge in bm.edges
                if edge.select
            ]

            if len(elements) != 2:
                return {'CANCELLED'}

            first, second = elements

            connected = bool(
                set(first.verts) &
                set(second.verts)
            )

        # --------------------------------------------------------------
        # Face mode
        # --------------------------------------------------------------

        elif select_mode == (False, False, True):
            elements = [
                face
                for face in bm.faces
                if face.select
            ]

            if len(elements) != 2:
                return {'CANCELLED'}

            first, second = elements

            connected = bool(
                set(first.edges) &
                set(second.edges)
            )

        else:
            return {'CANCELLED'}

        # --------------------------------------------------------------
        # Don't run if the two elements are already connected.
        # --------------------------------------------------------------

        if connected:
            return {'CANCELLED'}

        # --------------------------------------------------------------
        # Establish the first element as the active/source element.
        # --------------------------------------------------------------

        for vert in bm.verts:
            vert.select_set(False)

        for edge in bm.edges:
            edge.select_set(False)

        for face in bm.faces:
            face.select_set(False)

        first.select_set(True)

        bm.select_history.clear()
        bm.select_history.add(first)

        bmesh.update_edit_mesh(
            obj.data,
            loop_triangles=False,
            destructive=False
        )

        # --------------------------------------------------------------
        # Execute Blender's Shortest Path operator.
        # --------------------------------------------------------------

        try:
            result = bpy.ops.mesh.shortest_path_pick(
                edge_mode='SELECT',
                use_face_step=False,
                use_topology_distance=False,
                use_fill=False,
                index=second.index
            )

        except (RuntimeError, AttributeError):
            return {'CANCELLED'}

        if 'FINISHED' not in result:
            return {'CANCELLED'}

        return {'FINISHED'}


# ------------------------------------------------------------------------
# POSE MODE
# ------------------------------------------------------------------------

class VIEW3D_MT_touchscreen_pose_copy(bpy.types.Menu):
    bl_idname = "VIEW3D_MT_touchscreen_pose_copy"
    bl_label = "Copy"

    def draw(self, context):
        layout = self.layout

        layout.operator(
            "pose.copy",
            text="Copy Selected",
            icon='COPYDOWN'
        )

        layout.operator(
            "poselib.copy_as_asset",
            text="Copy as Asset",
            icon='ASSET_MANAGER'
        )


class VIEW3D_OT_pose_copy_menu(bpy.types.Operator):
    bl_idname = "view3d.pose_copy_menu"
    bl_label = "Copy"

    def execute(self, context):
        bpy.ops.wm.call_menu(
            name="VIEW3D_MT_touchscreen_pose_copy"
        )

        return {'FINISHED'}


class VIEW3D_MT_touchscreen_pose_paste(bpy.types.Menu):
    bl_idname = "VIEW3D_MT_touchscreen_pose_paste"
    bl_label = "Paste"

    def draw(self, context):
        layout = self.layout

        layout.operator(
            "pose.paste",
            text="Paste Pose",
            icon='PASTEDOWN'
        )

        op = layout.operator(
            "pose.paste",
            text="Paste Pose Flipped",
            icon='PASTEFLIPDOWN'
        )

        op.flipped = True


class VIEW3D_OT_pose_paste_menu(bpy.types.Operator):
    bl_idname = "view3d.pose_paste_menu"
    bl_label = "Paste"

    def execute(self, context):
        bpy.ops.wm.call_menu(
            name="VIEW3D_MT_touchscreen_pose_paste"
        )

        return {'FINISHED'}


class VIEW3D_MT_touchscreen_pose_show_hide(bpy.types.Menu):
    bl_idname = "VIEW3D_MT_touchscreen_pose_show_hide"
    bl_label = "Show/Hide"

    def draw(self, context):
        layout = self.layout

        op = layout.operator(
            "pose.hide",
            text="Hide Selected"
        )
        op.unselected = False

        op = layout.operator(
            "pose.hide",
            text="Hide Unselected"
        )
        op.unselected = True

        layout.operator(
            "pose.reveal",
            text="Show All"
        )


class VIEW3D_OT_pose_show_hide_menu(bpy.types.Operator):
    bl_idname = "view3d.pose_show_hide_menu"
    bl_label = "Show/Hide"

    def execute(self, context):
        bpy.ops.wm.call_menu(
            name="VIEW3D_MT_touchscreen_pose_show_hide"
        )

        return {'FINISHED'}


class VIEW3D_OT_pose_insert_keyframe(bpy.types.Operator):
    bl_idname = "view3d.pose_insert_keyframe"
    bl_label = "Insert Keyframe"

    def execute(self, context):
        try:
            bpy.ops.anim.keyframe_insert_menu(
                'INVOKE_DEFAULT',
                always_prompt=True
            )

        except (RuntimeError, AttributeError):
            return {'CANCELLED'}

        return {'FINISHED'}


# ------------------------------------------------------------------------
# TOOLBAR WIDTH
# ------------------------------------------------------------------------

def _toolbar_width_scale(context):
    try:
        system = bpy.context.preferences.system
        region = context.region
        view2d = region.view2d

        view2d_scale = (
            view2d.region_to_view(1.0, 0.0)[0]
            -
            view2d.region_to_view(0.0, 0.0)[0]
        )

        width_scale = (
            region.width *
            view2d_scale /
            system.ui_scale
        )

    except (
        AttributeError,
        RuntimeError,
        ZeroDivisionError
    ):
        try:
            width_scale = context.region.width

        except AttributeError:
            width_scale = 0.0

    return width_scale


def _toolbar_layout_mode(context):
    prefs = _get_preferences()

    # Blender Default
    if (
        prefs is None
        or getattr(
            prefs,
            "native_toolbar_layout",
            "BLENDER"
        ) == 'BLENDER'
    ):
        width_scale = _toolbar_width_scale(context)

        if width_scale <= 80.0:
            return 1, False

        elif width_scale <= 120.0:
            return 2, False

        else:
            return 1, True

    # Touchscreen automatic layout
    width_scale = _toolbar_width_scale(context)

    if width_scale <= 80.0:
        return 1, False

    elif width_scale <= 120.0:
        return 2, False

    elif width_scale <= 160.0:
        return 3, False

    elif width_scale <= 185.0:
        return 4, False

    else:
        return 1, True


# ------------------------------------------------------------------------
# BUTTON DRAWING
# ------------------------------------------------------------------------

def _draw_button(layout, item, show_text):
    operator, icon, text, props = item

    button = layout.operator(
        operator,
        text=text if show_text else '',
        icon=icon
    )

    for key, value in props.items():
        setattr(button, key, value)


# ------------------------------------------------------------------------
# MAIN TOOLBAR
# ------------------------------------------------------------------------

def draw_toolbar(self, context):
    layout = self.layout
    mode = context.mode

    columns, show_text = _toolbar_layout_mode(
        context
    )

    # --------------------------------------------------------------------
    # OBJECT MODE
    # --------------------------------------------------------------------

    if mode == 'OBJECT':
        groups = [
            [
                (
                    'view3d.delete_menu',
                    'TRASH',
                    'Delete',
                    {}
                ),
                (
                    'object.select_all',
                    'SCENE_DATA',
                    'Select All',
                    {'action': 'SELECT'}
                ),
            ],
            [
                (
                    'view3d.duplicate_menu',
                    'ONIONSKIN_ON',
                    'Duplicate',
                    {}
                ),
                (
                    'view3d.favorites_menu',
                    'SOLO_OFF',
                    'Quick Favorites',
                    {}
                ),
            ],
            [
                (
                    'view3d.simple_join',
                    'ADD',
                    'Join',
                    {}
                ),
                (
                    'view3d.show_hide_menu',
                    'HIDE_OFF',
                    'Show/Hide',
                    {}
                ),
            ],
            [
                (
                    'view3d.simple_undo',
                    'LOOP_BACK',
                    'Undo',
                    {}
                ),
                (
                    'view3d.simple_redo',
                    'LOOP_FORWARDS',
                    'Redo',
                    {}
                ),
            ],
            [
                (
                    'view3d.simple_repeat_last',
                    'RECOVER_LAST',
                    'Repeat Last',
                    {}
                ),
                (
                    'view3d.simple_undo_history',
                    'HELP',
                    'History',
                    {}
                ),
            ],
        ]

    # --------------------------------------------------------------------
    # EDIT MESH
    # --------------------------------------------------------------------

    elif mode == 'EDIT_MESH':
        groups = [
            [
                (
                    'view3d.delete_menu',
                    'TRASH',
                    'Delete',
                    {}
                ),
                (
                    'view3d.edit_select_menu',
                    'SCENE_DATA',
                    'Select',
                    {}
                ),
            ],
            [
                (
                    'view3d.uv_menu',
                    'MOD_UVPROJECT',
                    'UV',
                    {}
                ),
            ],
            [
                (
                    'view3d.favorites_menu',
                    'SOLO_OFF',
                    'Quick Favorites',
                    {}
                ),
                (
                    'view3d.fill_menu',
                    'MESH_GRID',
                    'Fill',
                    {}
                ),
            ],
            [
                (
                    'view3d.separate_menu',
                    'RESTRICT_COLOR_OFF',
                    'Separate',
                    {}
                ),
                (
                    'view3d.simple_undo',
                    'LOOP_BACK',
                    'Undo',
                    {}
                ),
            ],
            [
                (
                    'view3d.simple_redo',
                    'LOOP_FORWARDS',
                    'Redo',
                    {}
                ),
                (
                    'view3d.simple_repeat_last',
                    'RECOVER_LAST',
                    'Repeat Last',
                    {}
                ),
            ],
            [
                (
                    'view3d.simple_undo_history',
                    'HELP',
                    'History',
                    {}
                ),
            ],
        ]

    # --------------------------------------------------------------------
    # EDIT CURVE / EDIT ARMATURE
    # --------------------------------------------------------------------

    elif mode in {
        'EDIT_CURVE',
        'EDIT_ARMATURE'
    }:
        select = (
            'curve.select_all'
            if mode == 'EDIT_CURVE'
            else 'armature.select_all'
        )

        groups = [
            [
                (
                    'view3d.delete_menu',
                    'TRASH',
                    'Delete',
                    {}
                ),
                (
                    select,
                    'SCENE_DATA',
                    'Select All',
                    {'action': 'SELECT'}
                ),
            ],
            [
                (
                    'view3d.simple_undo',
                    'LOOP_BACK',
                    'Undo',
                    {}
                ),
                (
                    'view3d.simple_redo',
                    'LOOP_FORWARDS',
                    'Redo',
                    {}
                ),
            ],
            [
                (
                    'view3d.simple_repeat_last',
                    'RECOVER_LAST',
                    'Repeat Last',
                    {}
                ),
                (
                    'view3d.simple_undo_history',
                    'HELP',
                    'History',
                    {}
                ),
            ],
        ]

    # --------------------------------------------------------------------
    # POSE MODE
    # --------------------------------------------------------------------

    elif mode == 'POSE':
        groups = [
            [
                (
                    'view3d.pose_copy_menu',
                    'COPYDOWN',
                    'Copy',
                    {}
                ),
                (
                    'view3d.pose_paste_menu',
                    'PASTEDOWN',
                    'Paste',
                    {}
                ),
            ],
            [
                (
                    'view3d.pose_insert_keyframe',
                    'KEY_HLT',
                    'Insert Keyframe',
                    {}
                ),
                (
                    'view3d.pose_show_hide_menu',
                    'HIDE_OFF',
                    'Show/Hide',
                    {}
                ),
            ],
            [
                (
                    'view3d.simple_undo',
                    'LOOP_BACK',
                    'Undo',
                    {}
                ),
                (
                    'view3d.simple_redo',
                    'LOOP_FORWARDS',
                    'Redo',
                    {}
                ),
            ],
            [
                (
                    'view3d.simple_repeat_last',
                    'RECOVER_LAST',
                    'Repeat Last',
                    {}
                ),
                (
                    'view3d.simple_undo_history',
                    'HELP',
                    'History',
                    {}
                ),
            ],
        ]

    # --------------------------------------------------------------------
    # GREASE PENCIL DRAW
    # --------------------------------------------------------------------

    elif mode == 'PAINT_GREASE_PENCIL':
        groups = [
            [
                (
                    'view3d.simple_undo',
                    'LOOP_BACK',
                    'Undo',
                    {}
                ),
                (
                    'view3d.simple_redo',
                    'LOOP_FORWARDS',
                    'Redo',
                    {}
                ),
            ],
            [
                (
                    'view3d.simple_undo_history',
                    'HELP',
                    'History',
                    {}
                ),
            ],
        ]

    # --------------------------------------------------------------------
    # SCULPT / PAINT
    # --------------------------------------------------------------------

    elif mode in {
        'SCULPT',
        'PAINT_VERTEX',
        'PAINT_WEIGHT',
        'PAINT_TEXTURE'
    }:
        groups = [
            [
                (
                    'view3d.simple_undo',
                    'LOOP_BACK',
                    'Undo',
                    {}
                ),
                (
                    'view3d.simple_redo',
                    'LOOP_FORWARDS',
                    'Redo',
                    {}
                ),
            ],
            [
                (
                    'view3d.simple_undo_history',
                    'HELP',
                    'History',
                    {}
                ),
            ],
        ]

    else:
        return

    # --------------------------------------------------------------------
    # ICON-ONLY RESPONSIVE LAYOUT
    # --------------------------------------------------------------------

    if not show_text:
        grid = layout.grid_flow(
            row_major=True,
            columns=columns,
            even_columns=False,
            even_rows=False,
            align=True
        )

        grid.scale_y = 2.0

        for group in groups:
            for item in group:
                _draw_button(
                    grid,
                    item,
                    False
                )

    # --------------------------------------------------------------------
    # TEXT LAYOUT
    # --------------------------------------------------------------------

    else:
        column = layout.column(
            align=True
        )

        column.scale_y = 2.0

        for group in groups:
            for item in group:
                _draw_button(
                    column,
                    item,
                    True
                )


# ------------------------------------------------------------------------
# REGISTER
# ------------------------------------------------------------------------

CLASSES = (
    VIEW3D_OT_simple_delete,
    VIEW3D_OT_delete_menu,

    VIEW3D_OT_simple_duplicate,
    VIEW3D_OT_simple_duplicate_linked,
    VIEW3D_MT_touchscreen_duplicate,
    VIEW3D_OT_duplicate_menu,

    VIEW3D_MT_touchscreen_favorites,
    VIEW3D_OT_favorites_menu,

    VIEW3D_OT_simple_join,

    VIEW3D_OT_simple_undo,
    VIEW3D_OT_simple_redo,
    VIEW3D_OT_simple_undo_history,

    VIEW3D_OT_simple_repeat_last,

    VIEW3D_MT_touchscreen_pose_copy,
    VIEW3D_OT_pose_copy_menu,

    VIEW3D_MT_touchscreen_pose_paste,
    VIEW3D_OT_pose_paste_menu,

    VIEW3D_MT_touchscreen_pose_show_hide,
    VIEW3D_OT_pose_show_hide_menu,

    VIEW3D_OT_pose_insert_keyframe,

    VIEW3D_MT_touchscreen_fill,
    VIEW3D_OT_fill_menu,

    VIEW3D_MT_touchscreen_separate,
    VIEW3D_OT_separate_menu,

    VIEW3D_MT_touchscreen_show_hide,
    VIEW3D_OT_show_hide_menu,

    VIEW3D_OT_touchscreen_clear_seam,

    VIEW3D_MT_touchscreen_unwrap,
    VIEW3D_MT_touchscreen_uv,
    VIEW3D_OT_uv_menu,

    VIEW3D_MT_touchscreen_edit_select,
    VIEW3D_OT_edit_select_menu,
    VIEW3D_OT_touchscreen_shortest_path,
)


def register():
    for cls in CLASSES:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            pass

    try:
        bpy.types.VIEW3D_PT_tools_active.append(
            draw_toolbar
        )
    except Exception:
        pass

    update_native_toolbar_layout()


def unregister():
    _remove_native_toolbar_patch()

    try:
        bpy.types.VIEW3D_PT_tools_active.remove(
            draw_toolbar
        )
    except Exception:
        pass

    for cls in reversed(CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass