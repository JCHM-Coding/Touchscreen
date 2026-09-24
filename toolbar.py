# SPDX-License-Identifier: GPL-3.0-or-later
#
# Touchscreen - Toolbar
# Copyright (C) 2026 OpenAI
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import bpy

import math

REAL_MODIFIERS = {
    'MIRROR',
    'SUBSURF',
    'MULTIRES',
    'REMESH',
    'BOOLEAN',
    'BEVEL',
    'SOLIDIFY',
    'ARRAY',
    'CURVE',
    'HOOK',
    'SCREW',
    'LATTICE',
    'SHRINKWRAP',
    'SKIN',
    'DISPLACE',
    'SIMPLE_DEFORM',
    'ARMATURE',
    'DECIMATE',
    'DATA_TRANSFER',
    'NODES',
    'CAST',
    'CORRECTIVE_SMOOTH',
    'BUILD',
    'CLOTH',
    'COLLISION',
    'EXPLODE',
    'FLUID',
    'LAPLACIANDEFORM',
    'LAPLACIANSMOOTH',
    'MASK',
    'MESH_CACHE',
    'MESH_DEFORM',
    'MESH_SEQUENCE_CACHE',
    'NORMAL_EDIT',
    'PARTICLE_INSTANCE',
    'PARTICLE_SYSTEM',
    'SMOOTH',
    'SURFACE_DEFORM',
    'SOFT_BODY',
    'TRIANGULATE',
    'UV_WARP',
    'VERTEX_WEIGHT_EDIT',
    'VERTEX_WEIGHT_MIX',
    'VERTEX_WEIGHT_PROXIMITY',
    'WARP',
    'WAVE',
    'WELD',
    'WIREFRAME',
    'WEIGHTED_NORMAL',
}

EDIT_REPEAT_LAST_TOOLS = {
    'builtin.extrude_region',
    'builtin.inset_faces',
    'builtin.bevel',
    'builtin.spin',
    'builtin.poly_build',
    'builtin.move',
    'builtin.rotate',
    'builtin.scale',
    'builtin.transform',
}

class VIEW3D_OT_simple_delete(bpy.types.Operator):
    bl_idname = "view3d.simple_delete"
    bl_label = "Delete"
    @classmethod
    def poll(cls, context):
        return context.mode in {'OBJECT','EDIT_MESH','EDIT_CURVE','EDIT_ARMATURE'}
    def execute(self, context):
        try:
            if context.mode == 'OBJECT': bpy.ops.object.delete()
            elif context.mode == 'EDIT_MESH': bpy.ops.mesh.delete(type='VERT')
            elif context.mode == 'EDIT_CURVE': bpy.ops.curve.delete()
            elif context.mode == 'EDIT_ARMATURE': bpy.ops.armature.delete()
        except RuntimeError as e:
            self.report({'ERROR'}, str(e)); return {'CANCELLED'}
        return {'FINISHED'}

class VIEW3D_OT_delete_menu(bpy.types.Operator):
    bl_idname = "view3d.delete_menu"
    bl_label = "Delete"
    def execute(self, context):
        menus={'EDIT_MESH':'VIEW3D_MT_edit_mesh_delete','EDIT_CURVE':'VIEW3D_MT_edit_curve_delete','EDIT_ARMATURE':'VIEW3D_MT_edit_armature_delete'}
        menu=menus.get(context.mode)
        if menu: bpy.ops.wm.call_menu(name=menu)
        else: bpy.ops.view3d.simple_delete()
        return {'FINISHED'}

class VIEW3D_OT_simple_duplicate(bpy.types.Operator):
    bl_idname="view3d.simple_duplicate"; bl_label="Duplicate"
    def execute(self,context): bpy.ops.object.duplicate(linked=False); return {'FINISHED'}

class VIEW3D_OT_simple_duplicate_linked(bpy.types.Operator):
    bl_idname="view3d.simple_duplicate_linked"; bl_label="Duplicate Linked"
    def execute(self,context): bpy.ops.object.duplicate(linked=True); return {'FINISHED'}

class VIEW3D_OT_simple_join(bpy.types.Operator):
    bl_idname="view3d.simple_join"; bl_label="Join"
    @classmethod
    def poll(cls,context):
        return context.mode=='OBJECT' and context.active_object is not None and len(context.selected_objects)>=2
    def execute(self,context): bpy.ops.object.join(); return {'FINISHED'}

class VIEW3D_OT_simple_undo(bpy.types.Operator):
    bl_idname="view3d.simple_undo"; bl_label="Undo"

    @classmethod
    def poll(cls, context):
        # Disable the button when Blender has no undo step available.
        return bpy.ops.ed.undo.poll()

    def execute(self, context):
        # The extra poll guard keeps the operator safe even if the undo
        # state changes between drawing the button and pressing it.
        if not bpy.ops.ed.undo.poll():
            return {'CANCELLED'}
        bpy.ops.ed.undo()
        return {'FINISHED'}


class VIEW3D_OT_simple_redo(bpy.types.Operator):
    bl_idname="view3d.simple_redo"; bl_label="Redo"

    @classmethod
    def poll(cls, context):
        # Disable the button when Blender has no redo step available.
        return bpy.ops.ed.redo.poll()

    def execute(self, context):
        # The extra poll guard keeps the operator safe even if the redo
        # state changes between drawing the button and pressing it.
        if not bpy.ops.ed.redo.poll():
            return {'CANCELLED'}
        bpy.ops.ed.redo()
        return {'FINISHED'}

class VIEW3D_OT_simple_undo_history(bpy.types.Operator):
    bl_idname="view3d.simple_undo_history"; bl_label="History"

    def invoke(self, context, event):
        # Use the same invocation mode as Blender's Edit > Undo History.
        # This opens the native Undo History popup instead of executing it
        # silently through the wrapper operator.
        return bpy.ops.ed.undo_history('INVOKE_DEFAULT')


class VIEW3D_OT_simple_repeat_last(bpy.types.Operator):
    bl_idname="view3d.simple_repeat_last"; bl_label="Repeat Last"

    @classmethod
    def poll(cls, context):
        # Keep the existing mode/tool restriction, but also use Blender's
        # native poll as a null-condition guard. This prevents the button
        # from trying to run Repeat Last when Blender has no repeatable
        # operation available.
        if not _repeat_last_supported(context):
            return False
        try:
            return bpy.ops.screen.repeat_last.poll()
        except (AttributeError, RuntimeError):
            return False

    def execute(self, context):
        # The repeat state can change between drawing and clicking.
        # Guard it again so an empty Repeat Last state is simply cancelled
        # instead of producing an operator error.
        try:
            if not bpy.ops.screen.repeat_last.poll():
                return {'CANCELLED'}
            bpy.ops.screen.repeat_last()
        except (AttributeError, RuntimeError):
            return {'CANCELLED'}
        return {'FINISHED'}

class VIEW3D_MT_touchscreen_fill(bpy.types.Menu):
    bl_idname="VIEW3D_MT_touchscreen_fill"; bl_label="Fill"
    def draw(self,context):
        self.layout.operator("mesh.fill",text="Fill")
        self.layout.operator("mesh.fill_grid",text="Grid Fill")

class VIEW3D_OT_fill_menu(bpy.types.Operator):
    bl_idname="view3d.fill_menu"; bl_label="Fill"
    def execute(self,context): bpy.ops.wm.call_menu(name="VIEW3D_MT_touchscreen_fill"); return {'FINISHED'}

class VIEW3D_MT_touchscreen_separate(bpy.types.Menu):
    bl_idname="VIEW3D_MT_touchscreen_separate"; bl_label="Separate"
    def draw(self,context):
        l=self.layout
        op=l.operator("mesh.separate",text="Selection"); op.type='SELECTED'
        op=l.operator("mesh.separate",text="Material"); op.type='MATERIAL'
        op=l.operator("mesh.separate",text="Loose Parts"); op.type='LOOSE'

class VIEW3D_OT_separate_menu(bpy.types.Operator):
    bl_idname="view3d.separate_menu"; bl_label="Separate"
    def execute(self,context): bpy.ops.wm.call_menu(name="VIEW3D_MT_touchscreen_separate"); return {'FINISHED'}

class VIEW3D_MT_touchscreen_show_hide(bpy.types.Menu):
    bl_idname="VIEW3D_MT_touchscreen_show_hide"; bl_label="Show/Hide"
    def draw(self,context):
        l=self.layout
        l.operator("object.hide_view_set", text="Hide Selected").unselected=False
        l.operator("object.hide_view_set", text="Hide Unselected").unselected=True
        l.operator("object.hide_view_clear", text="Show All")

class VIEW3D_OT_show_hide_menu(bpy.types.Operator):
    bl_idname="view3d.show_hide_menu"; bl_label="Show/Hide"
    def execute(self,context): bpy.ops.wm.call_menu(name="VIEW3D_MT_touchscreen_show_hide"); return {'FINISHED'}

EDIT_REPEAT_LAST_TOOLS = {
    'builtin.extrude_region','builtin.inset_faces','builtin.bevel','builtin.spin','builtin.poly_build'
}
def _active_view3d_tool_id(context):
    try:
        tools=context.workspace.tools.from_space_view3d_mode(context.mode)
        return tools.active.idname if tools and tools.active else None
    except (AttributeError,RuntimeError): return None

def _repeat_last_supported(context):
    if context.mode=='OBJECT': return True
    if context.mode=='EDIT_MESH': return _active_view3d_tool_id(context) in EDIT_REPEAT_LAST_TOOLS
    return False

def _toolbar_layout_mode(context):
    """Use the same width break-points as Blender's native tool bar.

    Narrow: one column, icons only.
    Medium: two columns, icons only.
    Wide: one column, icons + text.
    """
    try:
        system = bpy.context.preferences.system
        region = context.region
        view2d = region.view2d
        view2d_scale = (
            view2d.region_to_view(1.0, 0.0)[0] -
            view2d.region_to_view(0.0, 0.0)[0]
        )
        width_scale = region.width * view2d_scale / system.ui_scale
    except (AttributeError, RuntimeError, ZeroDivisionError):
        width_scale = context.region.width

    if width_scale > 120.0:
        return 1, True
    if width_scale > 80.0:
        return 2, False
    return 1, False


def _draw_button(layout, item, show_text):
    operator, icon, text, props = item
    p = layout.operator(operator, text=text if show_text else '', icon=icon)
    for k, v in props.items():
        setattr(p, k, v)


def _draw_group(layout, items, columns, show_text):
    if columns == 2 and not show_text:
        row = layout.row(align=True)
        row.scale_x = 2.0
        row.scale_y = 2.0
        _draw_button(row, items[0], False)
        _draw_button(row, items[1], False)
    else:
        col = layout.column(align=True)
        col.scale_y = 2.0
        for item in items:
            _draw_button(col, item, show_text)


def _separator(layout):
    layout.separator()


def draw_toolbar(self, context):
    layout = self.layout
    mode = context.mode
    columns, show_text = _toolbar_layout_mode(context)

    if mode == 'OBJECT':
        groups = [
            [('view3d.delete_menu', 'TRASH', 'Delete', {}),
             ('object.select_all', 'SCENE_DATA', 'Select All', {'action': 'SELECT'})],
            [('view3d.simple_duplicate', 'ONIONSKIN_ON', 'Duplicate', {}),
             ('view3d.simple_duplicate_linked', 'ONIONSKIN_ON', 'Duplicate Linked', {})],
            [('view3d.simple_join', 'ADD', 'Join', {}),
             ('view3d.show_hide_menu', 'HIDE_OFF', 'Show/Hide', {})],
            [('view3d.simple_undo', 'LOOP_BACK', 'Undo', {}),
             ('view3d.simple_redo', 'LOOP_FORWARDS', 'Redo', {})],
            [('view3d.simple_repeat_last', 'RECOVER_LAST', 'Repeat Last', {}),
             ('view3d.simple_undo_history', 'HELP', 'History', {})],
        ]
    elif mode == 'EDIT_MESH':
        groups = [
            [('view3d.delete_menu', 'TRASH', 'Delete', {}),
             ('mesh.select_all', 'SCENE_DATA', 'Select All', {'action': 'SELECT'})],
            [('view3d.fill_menu', 'MESH_GRID', 'Fill', {}),
             ('view3d.separate_menu', 'RESTRICT_COLOR_OFF', 'Separate', {})],
            [('view3d.simple_undo', 'LOOP_BACK', 'Undo', {}),
             ('view3d.simple_redo', 'LOOP_FORWARDS', 'Redo', {})],
            [('view3d.simple_repeat_last', 'RECOVER_LAST', 'Repeat Last', {}),
             ('view3d.simple_undo_history', 'HELP', 'History', {})],
        ]
    elif mode in {'EDIT_CURVE', 'EDIT_ARMATURE'}:
        select = 'curve.select_all' if mode == 'EDIT_CURVE' else 'armature.select_all'
        groups = [
            [('view3d.delete_menu', 'TRASH', 'Delete', {}),
             (select, 'SCENE_DATA', 'Select All', {'action': 'SELECT'})],
            [('view3d.simple_undo', 'LOOP_BACK', 'Undo', {}),
             ('view3d.simple_redo', 'LOOP_FORWARDS', 'Redo', {})],
            [('view3d.simple_repeat_last', 'RECOVER_LAST', 'Repeat Last', {}),
             ('view3d.simple_undo_history', 'HELP', 'History', {})],
        ]
    elif mode in {'SCULPT', 'PAINT_VERTEX', 'PAINT_WEIGHT', 'PAINT_TEXTURE'}:
        groups = [
            [('view3d.simple_undo', 'LOOP_BACK', 'Undo', {}),
             ('view3d.simple_redo', 'LOOP_FORWARDS', 'Redo', {})],
            [('view3d.simple_undo_history', 'HELP', 'History', {})],
        ]
    else:
        return

    for index, group in enumerate(groups):
        if len(group) == 1:
            if columns == 2 and not show_text:
                # Keep a single button the same cell width as a button in a pair.
                # Do not scale the button itself horizontally: grid_flow provides
                # the half-width cell while preserving the native icon size.
                grid = layout.grid_flow(row_major=True, columns=2, even_columns=True, even_rows=False, align=True)
                grid.scale_y = 2.0
                _draw_button(grid, group[0], False)
            else:
                col = layout.column(align=True)
                col.scale_y = 2.0
                _draw_button(col, group[0], show_text)
        else:
            _draw_group(layout, group, columns, show_text)
        if index != len(groups) - 1:
            _separator(layout)

CLASSES=(VIEW3D_OT_simple_delete,VIEW3D_OT_delete_menu,VIEW3D_OT_simple_duplicate,VIEW3D_OT_simple_duplicate_linked,VIEW3D_OT_simple_join,VIEW3D_OT_simple_undo,VIEW3D_OT_simple_redo,VIEW3D_OT_simple_undo_history,VIEW3D_OT_simple_repeat_last,VIEW3D_MT_touchscreen_fill,VIEW3D_OT_fill_menu,VIEW3D_MT_touchscreen_separate,VIEW3D_OT_separate_menu,VIEW3D_MT_touchscreen_show_hide,VIEW3D_OT_show_hide_menu)

def register():
    for cls in CLASSES:
        try:bpy.utils.register_class(cls)
        except ValueError:pass
    try:bpy.types.VIEW3D_PT_tools_active.append(draw_toolbar)
    except Exception:pass

def unregister():
    try:bpy.types.VIEW3D_PT_tools_active.remove(draw_toolbar)
    except Exception:pass
    for cls in reversed(CLASSES):
        try:bpy.utils.unregister_class(cls)
        except Exception:pass
