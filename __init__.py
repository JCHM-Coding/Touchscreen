# SPDX-License-Identifier: GPL-3.0-or-later
# Touchscreen - modular touch-screen helpers
# Copyright (C) 2026 OpenAI

bl_info={"name":"Touchscreen","author":"OpenAI","version":(1,0,0),"blender":(5,3,0),"location":"Edit > Preferences > Add-ons","description":"Touch-screen helpers organized into independently enabled modules.","category":"3D View","license":"GPL-3.0-or-later"}

import bpy
import importlib
import sys

_MODULE_NAMES=(
    ("toolbar","Toolbar"),
    ("selection_others","Selection Others"),
    ("viewport_controls","Viewport Controls"),
    ("edit_mode","Edit Mode"),
    ("sculpt_mode","Sculpt Mode"),
    ("modifiers","Modifiers"),
)

# Import modules one at a time. This avoids package-level circular-import
# failures while Blender is enabling the add-on.
MODULES=[]
for _name,_label in _MODULE_NAMES:
    _module=importlib.import_module(f".{_name}", __package__)
    MODULES.append((_name,_label,_module))
MODULES=tuple(MODULES)

# Lista por defecto solicitada
DEFAULT_FAVORITES = [
    {"label": "Set Origin", "op_type": "EXEC_OPERATOR", "target": "object.origin_set"},
    {"label": "Shade Smooth", "op_type": "EXEC_OPERATOR", "target": "object.shade_smooth"},
    {"label": "Shade Flat", "op_type": "EXEC_OPERATOR", "target": "object.shade_flat"},
    {"label": "Set Parent", "op_type": "EXEC_OPERATOR", "target": "object.parent_set"},
    {"label": "Clear Parent", "op_type": "EXEC_OPERATOR", "target": "object.parent_clear"},
    {"label": "Apply Scale", "op_type": "EXEC_OPERATOR", "target": "object.transform_apply", "properties": "apply_scale=True"},
    {"label": "All Transforms", "op_type": "EXEC_OPERATOR", "target": "object.transform_apply", "properties": "location=True, rotation=True, scale=True"},
    {"label": "Visual Geometry to Mesh", "op_type": "EXEC_OPERATOR", "target": "object.convert", "properties": "target='MESH'"},
    {"label": "Visual Geometry to Objects", "op_type": "EXEC_OPERATOR", "target": "object.visual_transform_apply"},
    {"label": "Make Instances Real", "op_type": "EXEC_OPERATOR", "target": "object.duplicates_make_real"},
    {"label": "Edit Mode — Quick Favorites", "op_type": "CALL_MENU", "target": "SCREEN_MT_user_menu"},
    {"label": "Select Edge Loop", "op_type": "EXEC_OPERATOR", "target": "mesh.loop_multi_select", "properties": "ring=False"},
    {"label": "Select Edge Ring", "op_type": "EXEC_OPERATOR", "target": "mesh.loop_multi_select", "properties": "ring=True"},
    {"label": "Shortest Path", "op_type": "EXEC_OPERATOR", "target": "mesh.shortest_path_select"},
    {"label": "Edge Crease", "op_type": "EXEC_OPERATOR", "target": "transform.crease"},
    {"label": "To Circle", "op_type": "EXEC_OPERATOR", "target": "mesh.loop_to_region"},
    {"label": "Space Edge Loops Evenly", "op_type": "EXEC_OPERATOR", "target": "mesh.vertices_smooth"},
    {"label": "Symmetrize", "op_type": "EXEC_OPERATOR", "target": "mesh.symmetrize"},
    {"label": "Flip Normals", "op_type": "EXEC_OPERATOR", "target": "mesh.flip_normals"},
    {"label": "Recalculate Outside", "op_type": "EXEC_OPERATOR", "target": "mesh.normals_make_consistent", "properties": "inside=False"},
]

class TOUCHSCREEN_PG_favorite_item(bpy.types.PropertyGroup):
    label: bpy.props.StringProperty(name="Label", default="Custom Action")
    op_type: bpy.props.EnumProperty(
        name="Type",
        items=[
            ('EXEC_OPERATOR', "Operator", "Execute a Blender operator"),
            ('CALL_MENU', "Menu", "Call a Blender menu"),
        ],
        default='EXEC_OPERATOR'
    )
    target: bpy.props.StringProperty(name="Target ID", default="")
    properties: bpy.props.StringProperty(name="Properties", default="", description="e.g. location=True, scale=True")


class TOUCHSCREEN_OT_reset_favorites(bpy.types.Operator):
    bl_idname = "touchscreen.reset_favorites"
    bl_label = "Reset Favorites to Default"
    bl_description = "Restore the default list of quick favorites"

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        prefs.favorites.clear()
        for item in DEFAULT_FAVORITES:
            entry = prefs.favorites.add()
            entry.label = item["label"]
            entry.op_type = item["op_type"]
            entry.target = item["target"]
            entry.properties = item.get("properties", "")
        self.report({'INFO'}, "Favorites reset to default")
        return {'FINISHED'}


class TOUCHSCREEN_OT_add_favorite(bpy.types.Operator):
    bl_idname = "touchscreen.add_favorite"
    bl_label = "Add Favorite Item"

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        item = prefs.favorites.add()
        item.label = "New Item"
        return {'FINISHED'}


class TOUCHSCREEN_OT_remove_favorite(bpy.types.Operator):
    bl_idname = "touchscreen.remove_favorite"
    bl_label = "Remove Favorite Item"
    index: bpy.props.IntProperty()

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        prefs.favorites.remove(self.index)
        return {'FINISHED'}


class TOUCHSCREEN_OT_move_favorite(bpy.types.Operator):
    bl_idname = "touchscreen.move_favorite"
    bl_label = "Move Favorite Item"
    index: bpy.props.IntProperty()
    direction: bpy.props.EnumProperty(items=[('UP', "Up", ""), ('DOWN', "Down", "")])

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        favs = prefs.favorites
        idx = self.index
        new_idx = idx - 1 if self.direction == 'UP' else idx + 1
        if 0 <= new_idx < len(favs):
            favs.move(idx, new_idx)
        return {'FINISHED'}


def _set_module(name,enabled):
    mod=next(m for k,_l,m in MODULES if k==name)
    try:
        mod.register() if enabled else mod.unregister()
    except Exception as e:
        print(f"Touchscreen - {name}: {e}")

def _u(name):
    return lambda self,context: _set_module(name,getattr(self,name))

class TOUCHSCREEN_Preferences(bpy.types.AddonPreferences):
    bl_idname=__package__
    toolbar:bpy.props.BoolProperty(name="Toolbar",default=True,update=_u("toolbar"))
    selection_others:bpy.props.BoolProperty(name="Selection Others",default=True,update=_u("selection_others"))
    viewport_controls:bpy.props.BoolProperty(name="Viewport Controls",default=True,update=_u("viewport_controls"))
    viewport_controls_2x:bpy.props.BoolProperty(
        name="Viewport Controls 2x",
        description="Scale the Viewport Controls to 2x size",
        default=True,
    )
    edit_mode:bpy.props.BoolProperty(name="Edit Mode",default=True,update=_u("edit_mode"))
    sculpt_mode:bpy.props.BoolProperty(name="Sculpt Mode",default=True,update=_u("sculpt_mode"))
    modifiers:bpy.props.BoolProperty(name="Modifiers",default=True,update=_u("modifiers"))
    
    favorites: bpy.props.CollectionProperty(type=TOUCHSCREEN_PG_favorite_item)

    def draw(self,context):
        box=self.layout.box(); box.label(text="Modules")
        for prop,label,_ in MODULES: box.prop(self,prop,text=label)

        box=self.layout.box()
        box.label(text="Viewport Controls Size")
        row=box.row(align=True)
        row.prop(self,"viewport_controls_2x",text="2x Size",toggle=True)

        box = self.layout.box()
        box.label(text="Quick Favorites Config")
        row = box.row()
        row.operator("touchscreen.reset_favorites", text="Reset to Default Favorites", icon='FILE_REFRESH')
        row.operator("touchscreen.add_favorite", text="Add New Item", icon='ADD')

        for i, item in enumerate(self.favorites):
            r = box.row(align=True)
            r.prop(item, "label", text="")
            r.prop(item, "op_type", text="")
            r.prop(item, "target", text="")
            r.prop(item, "properties", text="Props")
            
            up = r.operator("touchscreen.move_favorite", text="", icon='TRIA_UP')
            up.index = i
            up.direction = 'UP'
            
            down = r.operator("touchscreen.move_favorite", text="", icon='TRIA_DOWN')
            down.index = i
            down.direction = 'DOWN'

            rem = r.operator("touchscreen.remove_favorite", text="", icon='X')
            rem.index = i

CLASSES=(
    TOUCHSCREEN_PG_favorite_item,
    TOUCHSCREEN_OT_reset_favorites,
    TOUCHSCREEN_OT_add_favorite,
    TOUCHSCREEN_OT_remove_favorite,
    TOUCHSCREEN_OT_move_favorite,
    TOUCHSCREEN_Preferences,
)

def register():
    for cls in CLASSES: bpy.utils.register_class(cls)
    prefs=bpy.context.preferences.addons[__package__].preferences
    
    # Si no existen favoritos guardados, inicializa los valores por defecto
    if len(prefs.favorites) == 0:
        bpy.ops.touchscreen.reset_favorites()

    for prop,_label,mod in MODULES:
        if getattr(prefs,prop,True):
            try: mod.register()
            except Exception as e: print(f"Touchscreen - {prop}: {e}")

def unregister():
    for _prop,_label,mod in reversed(MODULES):
        try: mod.unregister()
        except Exception: pass
    for cls in reversed(CLASSES):
        try: bpy.utils.unregister_class(cls)
        except Exception: pass