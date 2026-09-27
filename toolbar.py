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
import json


# ============================================================
# QUICK FAVORITES DATA
# ============================================================

DEFAULT_OBJECT_FAVORITES = (
    "object.set_origin",
    "object.parent_set",
    "object.parent_clear",
    "object.apply_scale",
    "object.all_transforms",
    "object.visual_geometry_to_mesh",
    "object.visual_geometry_to_objects",
    "object.make_instances_real",
)

DEFAULT_EDIT_FAVORITES = (
    "mesh.select_edge_loop",
    "mesh.select_edge_ring",
    "mesh.shortest_path",
    "mesh.edge_crease",
    "mesh.to_circle",
    "mesh.space_edge_loops_evenly",
    "mesh.symmetrize",
    "mesh.flip_normals",
    "mesh.recalculate_outside",
)


TOUCHSCREEN_OBJECT_FAVORITES = {
    "object.set_origin": (
        "Set Origin",
        "OBJECT_ORIGIN",
    ),

    "object.parent_set": (
        "Set Parent",
        "CONSTRAINT",
    ),

    "object.parent_clear": (
        "Clear Parent",
        "X",
    ),

    "object.apply_scale": (
        "Apply Scale",
        "OBJECT_ORIGIN",
    ),

    "object.all_transforms": (
        "All Transforms",
        "OBJECT_ORIGIN",
    ),

    "object.visual_geometry_to_mesh": (
        "Visual Geometry to Mesh",
        "MESH_DATA",
    ),

    "object.visual_geometry_to_objects": (
        "Visual Geometry to Objects",
        "MESH_DATA",
    ),

    "object.make_instances_real": (
        "Make Instances Real",
        "DUPLICATE",
    ),
}


TOUCHSCREEN_EDIT_FAVORITES = {
    "mesh.select_edge_loop": (
        "Select Edge Loop",
        "EDGESEL",
    ),

    "mesh.select_edge_ring": (
        "Select Edge Ring",
        "EDGESEL",
    ),

    "mesh.shortest_path": (
        "Shortest Path",
        "EDGESEL",
    ),

    "mesh.edge_crease": (
        "Edge Crease",
        "CREASE",
    ),

    "mesh.to_circle": (
        "To Circle",
        "SPHERE",
    ),

    "mesh.space_edge_loops_evenly": (
        "Space Edge Loops Evenly",
        "LOOPSEL",
    ),

    "mesh.symmetrize": (
        "Symmetrize",
        "MOD_MIRROR",
    ),

    "mesh.flip_normals": (
        "Flip Normals",
        "NORMALS_FACE",
    ),

    "mesh.recalculate_outside": (
        "Recalculate Outside",
        "NORMALS_FACE",
    ),
}


# ============================================================
# QUICK FAVORITES HELPERS
# ============================================================

def _get_preferences():

    try:

        addon = bpy.context.preferences.addons.get(
            __package__
        )

        if addon is None:
            return None

        return addon.preferences

    except Exception:
        return None


def _get_favorites(mode):

    prefs = _get_preferences()

    if prefs is None:
        return []

    try:

        if mode == 'OBJECT':
            raw = prefs.touchscreen_object_favorites

        elif mode == 'EDIT_MESH':
            raw = prefs.touchscreen_edit_favorites

        else:
            return []

        if not raw:
            return []

        data = json.loads(raw)

        if isinstance(data, list):
            return data

    except (
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ):
        pass

    return []


def _set_favorites(mode, favorites):

    prefs = _get_preferences()

    if prefs is None:
        return

    value = json.dumps(
        list(favorites)
    )

    if mode == 'OBJECT':
        prefs.touchscreen_object_favorites = value

    elif mode == 'EDIT_MESH':
        prefs.touchscreen_edit_favorites = value


def _favorite_definitions(mode):

    if mode == 'OBJECT':
        return TOUCHSCREEN_OBJECT_FAVORITES

    if mode == 'EDIT_MESH':
        return TOUCHSCREEN_EDIT_FAVORITES

    return {}


# ============================================================
# QUICK FAVORITE OPERATOR
# ============================================================

class VIEW3D_OT_touchscreen_favorite(
    bpy.types.Operator
):

    bl_idname = "view3d.touchscreen_favorite"
    bl_label = "Quick Favorite"

    favorite_id: bpy.props.StringProperty(
        options={'HIDDEN'}
    )

    favorite_mode: bpy.props.StringProperty(
        options={'HIDDEN'}
    )

    def execute(self, context):

        favorite_id = self.favorite_id

        # ----------------------------------------------------
        # OBJECT MODE
        # ----------------------------------------------------

        if favorite_id == "object.set_origin":

            if not bpy.ops.object.origin_set.poll():
                return {'CANCELLED'}

            bpy.ops.object.origin_set(
                'INVOKE_DEFAULT'
            )

            return {'FINISHED'}

        if favorite_id == "object.parent_set":

            if not bpy.ops.object.parent_set.poll():
                return {'CANCELLED'}

            bpy.ops.object.parent_set(
                'INVOKE_DEFAULT'
            )

            return {'FINISHED'}

        if favorite_id == "object.parent_clear":

            if not bpy.ops.object.parent_clear.poll():
                return {'CANCELLED'}

            bpy.ops.object.parent_clear(
                type='CLEAR'
            )

            return {'FINISHED'}

        if favorite_id == "object.apply_scale":

            if not bpy.ops.object.transform_apply.poll():
                return {'CANCELLED'}

            bpy.ops.object.transform_apply(
                location=False,
                rotation=False,
                scale=True
            )

            return {'FINISHED'}

        if favorite_id == "object.all_transforms":

            if not bpy.ops.object.transform_apply.poll():
                return {'CANCELLED'}

            bpy.ops.object.transform_apply(
                location=True,
                rotation=True,
                scale=True
            )

            return {'FINISHED'}

        if favorite_id == "object.visual_geometry_to_mesh":

            if not bpy.ops.object.convert.poll():
                return {'CANCELLED'}

            bpy.ops.object.convert(
                target='MESH',
                keep_original=False
            )

            return {'FINISHED'}

        if favorite_id == "object.visual_geometry_to_objects":

            operator = getattr(
                bpy.ops.object,
                "visual_geometry_to_objects",
                None
            )

            if operator is None:
                self.report(
                    {'ERROR'},
                    "Visual Geometry to Objects is unavailable"
                )
                return {'CANCELLED'}

            if not operator.poll():
                return {'CANCELLED'}

            operator()

            return {'FINISHED'}

        if favorite_id == "object.make_instances_real":

            operator = getattr(
                bpy.ops.object,
                "duplicates_make_real",
                None
            )

            if operator is None:
                self.report(
                    {'ERROR'},
                    "Make Instances Real is unavailable"
                )
                return {'CANCELLED'}

            if not operator.poll():
                return {'CANCELLED'}

            operator()

            return {'FINISHED'}

        # ----------------------------------------------------
        # EDIT MODE
        # ----------------------------------------------------

        if favorite_id == "mesh.select_edge_loop":

            if not bpy.ops.mesh.loop_select.poll():
                return {'CANCELLED'}

            bpy.ops.mesh.loop_select(
                'INVOKE_DEFAULT',
                extend=False,
                deselect=False,
                toggle=False,
                ring=False
            )

            return {'FINISHED'}

        if favorite_id == "mesh.select_edge_ring":

            if not bpy.ops.mesh.loop_select.poll():
                return {'CANCELLED'}

            bpy.ops.mesh.loop_select(
                'INVOKE_DEFAULT',
                extend=False,
                deselect=False,
                toggle=False,
                ring=True
            )

            return {'FINISHED'}

        if favorite_id == "mesh.shortest_path":

            operator = getattr(
                bpy.ops.mesh,
                "shortest_path_pick",
                None
            )

            if operator is None:
                self.report(
                    {'ERROR'},
                    "Shortest Path is unavailable"
                )
                return {'CANCELLED'}

            if not operator.poll():
                return {'CANCELLED'}

            operator(
                'INVOKE_DEFAULT'
            )

            return {'FINISHED'}

        if favorite_id == "mesh.edge_crease":

            operator = getattr(
                bpy.ops.transform,
                "edge_crease",
                None
            )

            if operator is None:
                self.report(
                    {'ERROR'},
                    "Edge Crease is unavailable"
                )
                return {'CANCELLED'}

            if not operator.poll():
                return {'CANCELLED'}

            operator(
                'INVOKE_DEFAULT'
            )

            return {'FINISHED'}

        if favorite_id == "mesh.to_circle":

            operator = getattr(
                bpy.ops.transform,
                "tosphere",
                None
            )

            if operator is None:
                self.report(
                    {'ERROR'},
                    "To Circle is unavailable"
                )
                return {'CANCELLED'}

            if not operator.poll():
                return {'CANCELLED'}

            operator(
                'INVOKE_DEFAULT',
                value=1.0
            )

            return {'FINISHED'}

        if favorite_id == "mesh.space_edge_loops_evenly":

            operator = getattr(
                bpy.ops.mesh,
                "looptools_space",
                None
            )

            if operator is None:
                self.report(
                    {'ERROR'},
                    "Space Edge Loops Evenly is unavailable"
                )
                return {'CANCELLED'}

            if not operator.poll():
                return {'CANCELLED'}

            operator(
                'INVOKE_DEFAULT'
            )

            return {'FINISHED'}

        if favorite_id == "mesh.symmetrize":

            if not bpy.ops.mesh.symmetrize.poll():
                return {'CANCELLED'}

            bpy.ops.mesh.symmetrize(
                'INVOKE_DEFAULT'
            )

            return {'FINISHED'}

        if favorite_id == "mesh.flip_normals":

            if not bpy.ops.mesh.flip_normals.poll():
                return {'CANCELLED'}

            bpy.ops.mesh.flip_normals()

            return {'FINISHED'}

        if favorite_id == "mesh.recalculate_outside":

            if not bpy.ops.mesh.normals_make_consistent.poll():
                return {'CANCELLED'}

            bpy.ops.mesh.normals_make_consistent(
                inside=False
            )

            return {'FINISHED'}

        return {'CANCELLED'}


# ============================================================
# QUICK FAVORITES - REMOVE
# ============================================================

class VIEW3D_OT_touchscreen_remove_favorite(
    bpy.types.Operator
):

    bl_idname = "view3d.touchscreen_remove_favorite"
    bl_label = "Remove from Touchscreen Favorites"

    favorite_id: bpy.props.StringProperty(
        options={'HIDDEN'}
    )

    favorite_mode: bpy.props.StringProperty(
        options={'HIDDEN'}
    )

    def execute(self, context):

        if self.favorite_mode not in {
            'OBJECT',
            'EDIT_MESH',
        }:
            return {'CANCELLED'}

        favorites = _get_favorites(
            self.favorite_mode
        )

        if self.favorite_id in favorites:

            favorites.remove(
                self.favorite_id
            )

            _set_favorites(
                self.favorite_mode,
                favorites
            )

        return {'FINISHED'}


# ============================================================
# QUICK FAVORITES - BUTTON CONTEXT MENU
# ============================================================

def _draw_touchscreen_button_context_menu(
    self,
    context
):

    prefs = _get_preferences()

    if prefs is None:
        return

    # Only Touchscreen's internal favorites can be removed
    # from this menu. Blender's native favorites remain untouched.
    if prefs.favorites_source != 'TOUCHSCREEN':
        return

    button_operator = getattr(
        context,
        "button_operator",
        None
    )

    if button_operator is None:
        return

    favorite_id = getattr(
        button_operator,
        "favorite_id",
        ""
    )

    favorite_mode = getattr(
        button_operator,
        "favorite_mode",
        ""
    )

    if not favorite_id:
        return

    if favorite_mode not in {
        'OBJECT',
        'EDIT_MESH',
    }:
        return

    layout = self.layout

    layout.separator()

    op = layout.operator(
        "view3d.touchscreen_remove_favorite",
        text="Remove from Touchscreen Favorites",
        icon='X'
    )

    op.favorite_id = favorite_id
    op.favorite_mode = favorite_mode


# ============================================================
# DELETE
# ============================================================

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
                bpy.ops.mesh.delete(
                    type='VERT'
                )

            elif context.mode == 'EDIT_CURVE':
                bpy.ops.curve.delete()

            elif context.mode == 'EDIT_ARMATURE':
                bpy.ops.armature.delete()

        except RuntimeError as e:

            self.report(
                {'ERROR'},
                str(e)
            )

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

        menu = menus.get(
            context.mode
        )

        if menu:
            bpy.ops.wm.call_menu(
                name=menu
            )
        else:
            bpy.ops.view3d.simple_delete()

        return {'FINISHED'}


# ============================================================
# DUPLICATE
# ============================================================

class VIEW3D_OT_simple_duplicate(bpy.types.Operator):

    bl_idname = "view3d.simple_duplicate"
    bl_label = "Duplicate"

    def execute(self, context):

        bpy.ops.object.duplicate(
            linked=False
        )

        return {'FINISHED'}


class VIEW3D_OT_simple_duplicate_linked(
    bpy.types.Operator
):

    bl_idname = "view3d.simple_duplicate_linked"
    bl_label = "Duplicate Linked"

    def execute(self, context):

        bpy.ops.object.duplicate(
            linked=True
        )

        return {'FINISHED'}


class VIEW3D_MT_touchscreen_duplicate(
    bpy.types.Menu
):

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


class VIEW3D_OT_duplicate_menu(
    bpy.types.Operator
):

    bl_idname = "view3d.duplicate_menu"
    bl_label = "Duplicate"

    def execute(self, context):

        bpy.ops.wm.call_menu(
            name="VIEW3D_MT_touchscreen_duplicate"
        )

        return {'FINISHED'}


# ============================================================
# QUICK FAVORITES MENU
# ============================================================

class VIEW3D_MT_touchscreen_favorites(
    bpy.types.Menu
):

    bl_idname = "VIEW3D_MT_touchscreen_favorites"
    bl_label = "Quick Favorites"

    def draw(self, context):

        prefs = _get_preferences()

        if prefs is None:
            return

        # ----------------------------------------------------
        # BLENDER FAVORITES
        # ----------------------------------------------------

        if prefs.favorites_source == 'BLENDER':

            self.layout.menu_contents(
                "SCREEN_MT_user_menu"
            )

            return

        # ----------------------------------------------------
        # TOUCHSCREEN FAVORITES
        # ----------------------------------------------------

        mode = context.mode

        if mode not in {
            'OBJECT',
            'EDIT_MESH',
        }:
            return

        favorites = _get_favorites(
            mode
        )

        definitions = _favorite_definitions(
            mode
        )

        layout = self.layout

        for favorite_id in favorites:

            definition = definitions.get(
                favorite_id
            )

            if definition is None:
                continue

            text, icon = definition

            op = layout.operator(
                "view3d.touchscreen_favorite",
                text=text,
                icon=icon
            )

            op.favorite_id = favorite_id
            op.favorite_mode = mode


class VIEW3D_OT_favorites_menu(
    bpy.types.Operator
):

    bl_idname = "view3d.favorites_menu"
    bl_label = "Quick Favorites"

    def execute(self, context):

        bpy.ops.wm.call_menu(
            name="VIEW3D_MT_touchscreen_favorites"
        )

        return {'FINISHED'}


# ============================================================
# JOIN
# ============================================================

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


# ============================================================
# UNDO / REDO / HISTORY
# ============================================================

class VIEW3D_OT_simple_undo(
    bpy.types.Operator
):

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


class VIEW3D_OT_simple_redo(
    bpy.types.Operator
):

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


class VIEW3D_OT_simple_undo_history(
    bpy.types.Operator
):

    bl_idname = "view3d.simple_undo_history"
    bl_label = "History"

    def invoke(self, context, event):

        return bpy.ops.ed.undo_history(
            'INVOKE_DEFAULT'
        )


# ============================================================
# REPEAT LAST
# ============================================================

class VIEW3D_OT_simple_repeat_last(
    bpy.types.Operator
):

    bl_idname = "view3d.simple_repeat_last"
    bl_label = "Repeat Last"

    def execute(self, context):

        try:

            if not bpy.ops.screen.repeat_last.poll():
                return {'CANCELLED'}

            bpy.ops.screen.repeat_last()

        except (
            RuntimeError,
            AttributeError
        ):
            return {'CANCELLED'}

        return {'FINISHED'}


# ============================================================
# FILL
# ============================================================

class VIEW3D_MT_touchscreen_fill(
    bpy.types.Menu
):

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


class VIEW3D_OT_fill_menu(
    bpy.types.Operator
):

    bl_idname = "view3d.fill_menu"
    bl_label = "Fill"

    def execute(self, context):

        bpy.ops.wm.call_menu(
            name="VIEW3D_MT_touchscreen_fill"
        )

        return {'FINISHED'}


# ============================================================
# SEPARATE
# ============================================================

class VIEW3D_MT_touchscreen_separate(
    bpy.types.Menu
):

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


class VIEW3D_OT_separate_menu(
    bpy.types.Operator
):

    bl_idname = "view3d.separate_menu"
    bl_label = "Separate"

    def execute(self, context):

        bpy.ops.wm.call_menu(
            name="VIEW3D_MT_touchscreen_separate"
        )

        return {'FINISHED'}


# ============================================================
# SHOW / HIDE
# ============================================================

class VIEW3D_MT_touchscreen_show_hide(
    bpy.types.Menu
):

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


class VIEW3D_OT_show_hide_menu(
    bpy.types.Operator
):

    bl_idname = "view3d.show_hide_menu"
    bl_label = "Show/Hide"

    def execute(self, context):

        bpy.ops.wm.call_menu(
            name="VIEW3D_MT_touchscreen_show_hide"
        )

        return {'FINISHED'}


# ============================================================
# CLEAR SEAM
# ============================================================

class VIEW3D_OT_touchscreen_clear_seam(
    bpy.types.Operator
):

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

            bpy.ops.mesh.mark_seam(
                clear=True
            )

        except (
            RuntimeError,
            AttributeError
        ):

            return {'CANCELLED'}

        return {'FINISHED'}


# ============================================================
# UNWRAP
# ============================================================

class VIEW3D_MT_touchscreen_unwrap(
    bpy.types.Menu
):

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


# ============================================================
# UV MENU
# ============================================================

class VIEW3D_MT_touchscreen_uv(
    bpy.types.Menu
):

    bl_idname = "VIEW3D_MT_touchscreen_uv"
    bl_label = "UV"

    def draw(self, context):

        layout = self.layout

        # ----------------------------------------------------
        # MARK SEAM
        # ----------------------------------------------------

        layout.operator(
            "uv.mark_seam",
            text="Mark Seam"
        )

        # ----------------------------------------------------
        # CLEAR SEAM
        # ----------------------------------------------------

        layout.operator(
            "view3d.touchscreen_clear_seam",
            text="Clear Seam"
        )

        # ----------------------------------------------------
        # UNWRAP
        # ----------------------------------------------------

        layout.menu(
            "VIEW3D_MT_touchscreen_unwrap",
            text="Unwrap"
        )


class VIEW3D_OT_uv_menu(
    bpy.types.Operator
):

    bl_idname = "view3d.uv_menu"
    bl_label = "UV"

    def execute(self, context):

        bpy.ops.wm.call_menu(
            name="VIEW3D_MT_touchscreen_uv"
        )

        return {'FINISHED'}


# ============================================================
# POSE MODE
# ============================================================

class VIEW3D_MT_touchscreen_pose_copy(
    bpy.types.Menu
):

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


class VIEW3D_OT_pose_copy_menu(
    bpy.types.Operator
):

    bl_idname = "view3d.pose_copy_menu"
    bl_label = "Copy"

    def execute(self, context):

        bpy.ops.wm.call_menu(
            name="VIEW3D_MT_touchscreen_pose_copy"
        )

        return {'FINISHED'}


class VIEW3D_MT_touchscreen_pose_paste(
    bpy.types.Menu
):

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


class VIEW3D_OT_pose_paste_menu(
    bpy.types.Operator
):

    bl_idname = "view3d.pose_paste_menu"
    bl_label = "Paste"

    def execute(self, context):

        bpy.ops.wm.call_menu(
            name="VIEW3D_MT_touchscreen_pose_paste"
        )

        return {'FINISHED'}


class VIEW3D_MT_touchscreen_pose_show_hide(
    bpy.types.Menu
):

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


class VIEW3D_OT_pose_show_hide_menu(
    bpy.types.Operator
):

    bl_idname = "view3d.pose_show_hide_menu"
    bl_label = "Show/Hide"

    def execute(self, context):

        bpy.ops.wm.call_menu(
            name="VIEW3D_MT_touchscreen_pose_show_hide"
        )

        return {'FINISHED'}


class VIEW3D_OT_pose_insert_keyframe(
    bpy.types.Operator
):

    bl_idname = "view3d.pose_insert_keyframe"
    bl_label = "Insert Keyframe"

    def execute(self, context):

        try:

            bpy.ops.anim.keyframe_insert_menu(
                'INVOKE_DEFAULT',
                always_prompt=True
            )

        except (
            RuntimeError,
            AttributeError
        ):

            return {'CANCELLED'}

        return {'FINISHED'}


# ============================================================
# TOOLBAR LAYOUT
# ============================================================

def _toolbar_layout_mode(context):

    try:

        system = bpy.context.preferences.system
        region = context.region
        view2d = region.view2d

        view2d_scale = (
            view2d.region_to_view(
                1.0,
                0.0
            )[0]
            -
            view2d.region_to_view(
                0.0,
                0.0
            )[0]
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

        width_scale = context.region.width

    if width_scale > 120.0:
        return 1, True

    if width_scale > 80.0:
        return 2, False

    return 1, False


def _draw_button(
    layout,
    item,
    show_text
):

    operator, icon, text, props = item

    button = layout.operator(
        operator,
        text=text if show_text else '',
        icon=icon
    )

    for key, value in props.items():
        setattr(
            button,
            key,
            value
        )


def _draw_group(
    layout,
    items,
    columns,
    show_text
):

    if columns == 2 and not show_text:

        row = layout.row(
            align=True
        )

        row.scale_x = 2.0
        row.scale_y = 2.0

        for item in items:

            _draw_button(
                row,
                item,
                False
            )

    else:

        column = layout.column(
            align=True
        )

        column.scale_y = 2.0

        for item in items:

            _draw_button(
                column,
                item,
                show_text
            )


# ============================================================
# MAIN TOOLBAR
# ============================================================

def draw_toolbar(
    self,
    context
):

    layout = self.layout
    mode = context.mode

    columns, show_text = _toolbar_layout_mode(
        context
    )

    # --------------------------------------------------------
    # OBJECT MODE
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # EDIT MESH
    # --------------------------------------------------------

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
                    'mesh.select_all',
                    'SCENE_DATA',
                    'Select All',
                    {'action': 'SELECT'}
                ),
            ],

            [
                (
                    'view3d.uv_menu',
                    'MOD_UVPROJECT',
                    'UV',
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
                    'view3d.fill_menu',
                    'MESH_GRID',
                    'Fill',
                    {}
                ),
                (
                    'view3d.separate_menu',
                    'RESTRICT_COLOR_OFF',
                    'Separate',
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

    # --------------------------------------------------------
    # EDIT CURVE / ARMATURE
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # POSE MODE
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # DRAW MODE
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # SCULPT / PAINT
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # DRAW GROUPS
    # --------------------------------------------------------

    if columns == 2 and not show_text:

        grid = layout.grid_flow(
            row_major=True,
            columns=2,
            even_columns=True,
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
                    show_text
                )


# ============================================================
# REGISTER
# ============================================================

CLASSES = (
    # Quick Favorites
    VIEW3D_OT_touchscreen_favorite,
    VIEW3D_OT_touchscreen_remove_favorite,

    # Delete
    VIEW3D_OT_simple_delete,
    VIEW3D_OT_delete_menu,

    # Duplicate
    VIEW3D_OT_simple_duplicate,
    VIEW3D_OT_simple_duplicate_linked,
    VIEW3D_MT_touchscreen_duplicate,
    VIEW3D_OT_duplicate_menu,

    # Favorites menu
    VIEW3D_MT_touchscreen_favorites,
    VIEW3D_OT_favorites_menu,

    # Join
    VIEW3D_OT_simple_join,

    # Undo / Redo / History
    VIEW3D_OT_simple_undo,
    VIEW3D_OT_simple_redo,
    VIEW3D_OT_simple_undo_history,
    VIEW3D_OT_simple_repeat_last,

    # Pose
    VIEW3D_MT_touchscreen_pose_copy,
    VIEW3D_OT_pose_copy_menu,
    VIEW3D_MT_touchscreen_pose_paste,
    VIEW3D_OT_pose_paste_menu,
    VIEW3D_MT_touchscreen_pose_show_hide,
    VIEW3D_OT_pose_show_hide_menu,
    VIEW3D_OT_pose_insert_keyframe,

    # Fill
    VIEW3D_MT_touchscreen_fill,
    VIEW3D_OT_fill_menu,

    # Separate
    VIEW3D_MT_touchscreen_separate,
    VIEW3D_OT_separate_menu,

    # Show / Hide
    VIEW3D_MT_touchscreen_show_hide,
    VIEW3D_OT_show_hide_menu,

    # UV
    VIEW3D_OT_touchscreen_clear_seam,
    VIEW3D_MT_touchscreen_unwrap,
    VIEW3D_MT_touchscreen_uv,
    VIEW3D_OT_uv_menu,
)


# ============================================================
# REGISTER / UNREGISTER
# ============================================================

def register():

    for cls in CLASSES:

        try:
            bpy.utils.register_class(
                cls
            )

        except ValueError:
            pass

    try:

        bpy.types.UI_MT_button_context_menu.append(
            _draw_touchscreen_button_context_menu
        )

    except Exception:
        pass

    try:

        bpy.types.VIEW3D_PT_tools_active.append(
            draw_toolbar
        )

    except Exception:
        pass


def unregister():

    try:

        bpy.types.VIEW3D_PT_tools_active.remove(
            draw_toolbar
        )

    except Exception:
        pass

    try:

        bpy.types.UI_MT_button_context_menu.remove(
            _draw_touchscreen_button_context_menu
        )

    except Exception:
        pass

    for cls in reversed(CLASSES):

        try:
            bpy.utils.unregister_class(
                cls
            )

        except Exception:
            pass