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

        layout.operator("mesh.fill", text="Fill")
        layout.operator("mesh.fill_grid", text="Grid Fill")
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
# UNWRAP
# ============================================================

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


# ============================================================
# UV MENU
# ============================================================

class VIEW3D_MT_touchscreen_uv(bpy.types.Menu):
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


class VIEW3D_OT_uv_menu(bpy.types.Operator):
    bl_idname = "view3d.uv_menu"
    bl_label = "UV"

    def execute(self, context):
        bpy.ops.wm.call_menu(
            name="VIEW3D_MT_touchscreen_uv"
        )
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
        width_scale = context.region.width

    if width_scale > 120.0:
        return 1, True

    if width_scale > 80.0:
        return 2, False

    return 1, False


def _draw_button(layout, item, show_text):

    operator, icon, text, props = item

    button = layout.operator(
        operator,
        text=text if show_text else '',
        icon=icon
    )

    for key, value in props.items():
        setattr(button, key, value)


def _draw_group(layout, items, columns, show_text):

    if columns == 2 and not show_text:

        row = layout.row(align=True)
        row.scale_x = 2.0
        row.scale_y = 2.0

        for item in items:
            _draw_button(
                row,
                item,
                False
            )

    else:

        column = layout.column(align=True)
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

def draw_toolbar(self, context):

    layout = self.layout
    mode = context.mode

    columns, show_text = _toolbar_layout_mode(context)

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

        # One continuous 2-column grid for the whole toolbar.
        # This removes the gaps between individual group rows.
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

        for group in groups:

            if len(group) == 1:

                column = layout.column(
                    align=True
                )

                column.scale_y = 2.0

                _draw_button(
                    column,
                    group[0],
                    show_text
                )

            else:

                _draw_group(
                    layout,
                    group,
                    columns,
                    show_text
                )


# ============================================================
# REGISTER
# ============================================================

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
)


# ============================================================
# REGISTER / UNREGISTER
# ============================================================

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


def unregister():

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

