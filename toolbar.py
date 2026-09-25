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


# ============================================================
# DUPLICATE
# ============================================================

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


# ============================================================
# QUICK FAVORITES
# ============================================================

class VIEW3D_MT_touchscreen_favorites(bpy.types.Menu):
    bl_idname = "VIEW3D_MT_touchscreen_favorites"
    bl_label = "Quick Favorites"

    def draw(self, context):
        self.layout.menu_contents("SCREEN_MT_user_menu")


class VIEW3D_OT_favorites_menu(bpy.types.Operator):
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
        return bpy.ops.ed.undo_history('INVOKE_DEFAULT')


# ============================================================
# REPEAT LAST
# ============================================================

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


# ============================================================
# FILL
# ============================================================

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


# ============================================================
# SEPARATE
# ============================================================

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


# ============================================================
# SHOW / HIDE
# ============================================================

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


# ============================================================
# CLEAR SEAM
# ============================================================

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


# ============================================================
# SHORTEST PATH
# ============================================================

class VIEW3D_OT_touchscreen_shortest_path(bpy.types.Operator):
    bl_idname = "view3d.touchscreen_shortest_path"
    bl_label = "Shortest Path"

    @classmethod
    def poll(cls, context):
        return (
            context.mode == 'EDIT_MESH'
            and context.active_object is not None
        )

    def execute(self, context):

        if not context.scene.touchscreen_shortest_path:
            return {'CANCELLED'}

        try:
            return bpy.ops.mesh.shortest_path_pick(
                'INVOKE_DEFAULT',
                edge_mode='SELECT'
            )

        except (RuntimeError, AttributeError):
            return {'CANCELLED'}


# ============================================================
# SHORTEST PATH BOOLEAN UPDATE
# ============================================================

def touchscreen_shortest_path_update(self, context):

    # When enabled, immediately activate Blender's
    # native Shortest Path operator.
    if self.touchscreen_shortest_path:

        if (
            context.mode == 'EDIT_MESH'
            and context.active_object is not None
        ):
            try:
                bpy.ops.mesh.shortest_path_pick(
                    'INVOKE_DEFAULT',
                    edge_mode='SELECT'
                )
            except (RuntimeError, AttributeError):
                pass


# =====================================================

