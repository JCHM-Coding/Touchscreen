# SPDX-License-Identifier: GPL-3.0-or-later
#
# Touchscreen - Selection Others
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

def _area_and_window_region(context, space_type):
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type == space_type:
                region = next((r for r in area.regions if r.type == 'WINDOW'), None)
                if region:
                    return window, area, region
    return None, None, None

def _run_context_operator(context, space_type, operator):
    window, area, region = _area_and_window_region(context, space_type)
    if not area or not region:
        return {'CANCELLED'}
    with bpy.context.temp_override(
        window=window,
        area=area,
        region=region,
    ):
        return operator()

class TOUCHSCREEN_OT_file_box_select(bpy.types.Operator):
    bl_idname = "touchscreen.file_box_select"
    bl_label = "Box Select"
    bl_options = {'REGISTER', 'UNDO'}

    mode: bpy.props.EnumProperty(
        items=[
            ('SET', "Select Set", ""),
            ('SUB', "Select Subtract", ""),
        ],
        default='SET',
    )

    def execute(self, context):
        try:
            result = _run_context_operator(
                context,
                'FILE_BROWSER',
                lambda: bpy.ops.file.select_box(
                    wait_for_input=True,
                    mode=self.mode,
                )
            )
            return result if result else {'FINISHED'}
        except RuntimeError as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}

class TOUCHSCREEN_OT_outliner_box_select(bpy.types.Operator):
    bl_idname = "touchscreen.outliner_box_select"
    bl_label = "Box Select"
    bl_options = {'REGISTER', 'UNDO'}

    mode: bpy.props.EnumProperty(
        items=[
            ('SET', "Select Set", ""),
            ('SUB', "Select Subtract", ""),
        ],
        default='SET',
    )

    def execute(self, context):
        try:
            result = _run_context_operator(
                context,
                'OUTLINER',
                lambda: bpy.ops.outliner.select_box(
                    wait_for_input=True,
                    mode=self.mode,
                )
            )
            return result if result else {'FINISHED'}
        except RuntimeError as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}

class TOUCHSCREEN_MT_selection(bpy.types.Menu):
    bl_idname = "TOUCHSCREEN_MT_selection"
    bl_label = "Selection"

    def draw(self, context):
        layout = self.layout
        area_type = context.area.type if context.area else ''

        row = layout.row(align=True)

        # Select / Left Click: native Blender behavior.
        op = row.operator(
            "touchscreen.selection_hint",
            text="",
            icon='RESTRICT_SELECT_OFF',
        )
        op.hint = "Left Click — Select"

        if area_type == 'FILE_BROWSER':
            op = row.operator(
                "touchscreen.file_box_select",
                text="",
                icon='BORDER_RECT',
            )
            op.mode = 'SET'
            op = row.operator(
                "touchscreen.file_box_select",
                text="",
                icon='SELECT_SUBTRACT',
            )
            op.mode = 'SUB'
        elif area_type == 'OUTLINER':
            op = row.operator(
                "touchscreen.outliner_box_select",
                text="",
                icon='BORDER_RECT',
            )
            op.mode = 'SET'
            op = row.operator(
                "touchscreen.outliner_box_select",
                text="",
                icon='SELECT_SUBTRACT',
            )
            op.mode = 'SUB'

        # Shift/Ctrl are native click modifiers in Blender's selectors.
        row = layout.row(align=True)
        op = row.operator(
            "touchscreen.selection_hint",
            text="",
            icon='LINKED',
        )
        op.hint = "Shift-click — Continuous Range"
        op = row.operator(
            "touchscreen.selection_hint",
            text="",
            icon='SELECT_EXTEND',
        )
        op.hint = "Ctrl-click — Individual Toggle"

class TOUCHSCREEN_OT_selection_hint(bpy.types.Operator):
    bl_idname = "touchscreen.selection_hint"
    bl_label = "Select"
    bl_description = "Use Left Click to select"

    hint: bpy.props.StringProperty(default="Left Click — Select")

    def execute(self, context):
        self.report({'INFO'}, self.hint)
        return {'FINISHED'}

def draw_filebrowser_selection(self, context):
    if context.area and context.area.type == 'FILE_BROWSER':
        self.layout.menu(
            TOUCHSCREEN_MT_selection.bl_idname,
            text="",
            icon='DOWNARROW_HLT',
        )

def draw_outliner_selection(self, context):
    if context.area and context.area.type == 'OUTLINER':
        self.layout.menu(
            TOUCHSCREEN_MT_selection.bl_idname,
            text="",
            icon='DOWNARROW_HLT',
        )

class FILEBROWSER_PT_custom_select(bpy.types.Panel):
    bl_label = "Select"
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOLS'
    bl_category = "Select"

    def draw(self, context):
        layout = self.layout

        # All
        layout.operator(
            "file.select_all",
            text="All"
        ).action = 'SELECT'

        # None
        layout.operator(
            "file.select_all",
            text="None"
        ).action = 'DESELECT'

        # Invert
        layout.operator(
            "file.select_all",
            text="Invert"
        ).action = 'INVERT'

        layout.separator()

        # Box
        layout.operator(
            "file.select_box",
            text="Box"
        )

class TOUCHSCREEN_MT_outliner_select(bpy.types.Menu):
    bl_idname = "TOUCHSCREEN_MT_outliner_select"
    bl_label = "Select"

    def draw(self, _context):
        layout = self.layout

        # Delete
        layout.operator(
            "outliner.id_operation",
            text="Delete"
        ).type = 'DELETE'

        # New Collection
        layout.operator(
            "outliner.collection_new",
            text="New Collection"
        )

        # Mark as Asset
        layout.operator(
            "asset.mark",
            text="Mark as Asset"
        )

        # Select Objects Inside Collection
        layout.operator(
            "outliner.collection_objects_select",
            text="Select Objects Inside Collection"
        )

        # Deselect Objects Inside Collection
        layout.operator(
            "outliner.collection_objects_deselect",
            text="Deselect Objects Inside Collection"
        )

        # Clear Asset
        layout.operator(
            "asset.clear",
            text="Clear Asset"
        ).set_fake_user = False

        # Clear Asset (Set Fake User)
        layout.operator(
            "asset.clear",
            text="Clear Asset (Set Fake User)"
        ).set_fake_user = True

        layout.separator()

        # Existing options
        layout.operator(
            "outliner.select_all",
            text="All"
        ).action = 'SELECT'

        layout.operator(
            "outliner.select_all",
            text="None"
        ).action = 'DESELECT'

        layout.operator(
            "outliner.select_all",
            text="Invert"
        ).action = 'INVERT'

        layout.separator()

        layout.operator(
            "outliner.select_box",
            text="Box"
        )

def draw_outliner_select(self, _context):
    self.layout.menu(
        "TOUCHSCREEN_MT_outliner_select",
        text="",
        icon='RESTRICT_SELECT_OFF'
    )

CLASSES=(
    TOUCHSCREEN_OT_file_box_select,
    TOUCHSCREEN_OT_outliner_box_select,
    TOUCHSCREEN_MT_selection,
    TOUCHSCREEN_OT_selection_hint,
    FILEBROWSER_PT_custom_select,
    TOUCHSCREEN_MT_outliner_select,
)

def register():
    for cls in CLASSES:
        try: bpy.utils.register_class(cls)
        except ValueError: pass
    for cb,typ in ((draw_filebrowser_selection,'FILEBROWSER_HT_header'),(draw_outliner_selection,'OUTLINER_HT_header'),(draw_outliner_select,'OUTLINER_HT_header')):
        try: getattr(bpy.types,typ).append(cb)
        except Exception: pass

def unregister():
    for cb,typ in ((draw_filebrowser_selection,'FILEBROWSER_HT_header'),(draw_outliner_selection,'OUTLINER_HT_header'),(draw_outliner_select,'OUTLINER_HT_header')):
        try: getattr(bpy.types,typ).remove(cb)
        except Exception: pass
    for cls in reversed(CLASSES):
        try: bpy.utils.unregister_class(cls)
        except Exception: pass
