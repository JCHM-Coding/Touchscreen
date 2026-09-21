# SPDX-License-Identifier: GPL-3.0-or-later
#
# Touchscreen - Edit Mode
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

def get_knife_properties(context):
    if context.mode != 'EDIT_MESH':
        return None

    if not context.workspace:
        return None

    try:
        tool = context.workspace.tools.from_space_view3d_mode(
            'EDIT_MESH'
        )
    except Exception:
        return None

    if not tool:
        return None

    if tool.idname != "builtin.knife":
        return None

    try:
        # IMPORTANT:
        # The actual operator is mesh.knife_tool
        return tool.operator_properties("mesh.knife_tool")
    except Exception as e:
        print("Knife +:", e)
        return None

def apply_double_click_confirm():

    wm = bpy.context.window_manager

    keyconfigs = []

    if wm.keyconfigs.active:
        keyconfigs.append(wm.keyconfigs.active)

    if wm.keyconfigs.user:
        keyconfigs.append(wm.keyconfigs.user)

    for kc in keyconfigs:

        km = kc.keymaps.get("Knife Tool Modal Map")

        if not km:
            continue

        for kmi in km.keymap_items:

            if (
                kmi.type == 'LEFTMOUSE'
                and kmi.value == 'DOUBLE_CLICK'
            ):

                try:
                    if bpy.context.scene.knife_double_click_confirm:
                        kmi.propvalue = 'CONFIRM'
                    else:
                        kmi.propvalue = 'ADD_CUT_CLOSED'

                except Exception:
                    pass

def update_double_click(self, context):
    apply_double_click_confirm()

def update_cut_through(self, context):

    props = get_knife_properties(context)

    if props is None:
        print("Knife +: Knife properties not found")
        return

    try:

        # Cut Through ON
        # = Occlude Geometry OFF
        props.use_occlude_geometry = not self.knife_cut_through

        print(
            "Knife +:",
            "Cut Through =", self.knife_cut_through,
            "| use_occlude_geometry =",
            props.use_occlude_geometry
        )

    except Exception as e:

        print(
            "Knife + Cut Through ERROR:",
            e
        )

class VIEW3D_PT_knife_plus(bpy.types.Panel):

    bl_label = "Knife +"
    bl_idname = "VIEW3D_PT_knife_plus"

    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

    bl_category = "Tool"

    @classmethod
    def poll(cls, context):

        if context.mode != 'EDIT_MESH':
            return False

        if not context.workspace:
            return False

        try:
            tool = context.workspace.tools.from_space_view3d_mode(
                'EDIT_MESH'
            )
        except Exception:
            return False

        if not tool:
            return False

        return tool.idname == "builtin.knife"

    def draw(self, context):

        layout = self.layout

        layout.prop(
            context.scene,
            "knife_double_click_confirm",
            text="Double Click Confirm"
        )

        layout.prop(
            context.scene,
            "knife_cut_through",
            text="Cut Through"
        )

CLASSES=(
    VIEW3D_PT_knife_plus,
)

def register():
    for cls in CLASSES:
        try: bpy.utils.register_class(cls)
        except ValueError: pass
    bpy.types.Scene.knife_double_click_confirm=bpy.props.BoolProperty(name="Confirm on Double Click Outside",default=False,update=update_double_click)
    bpy.types.Scene.knife_cut_through=bpy.props.BoolProperty(name="Cut Through",default=False,update=update_cut_through)
    # Do not access bpy.context.scene here: Blender can call module
    # registration with a restricted context. The update callbacks apply
    # the settings when the properties are changed in the UI.
    try:
        apply_double_click_confirm()
    except Exception:
        pass

def unregister():
    try: apply_double_click_confirm(False)
    except Exception: pass
    for p in ('knife_double_click_confirm','knife_cut_through'):
        try: delattr(bpy.types.Scene,p)
        except Exception: pass
    for cls in reversed(CLASSES):
        try: bpy.utils.unregister_class(cls)
        except Exception: pass
