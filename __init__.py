# SPDX-License-Identifier: GPL-3.0-or-later
# Touchscreen - modular touch-screen helpers
# Copyright (C) 2026 OpenAI

bl_info = {
    "name": "Touchscreen",
    "author": "OpenAI",
    "version": (1, 0, 0),
    "blender": (5, 3, 0),
    "location": "Edit > Preferences > Add-ons",
    "description": "Touch-screen helpers organized into independently enabled modules.",
    "category": "3D View",
    "license": "GPL-3.0-or-later",
}

import bpy
import importlib
import sys


_MODULE_NAMES = (
    ("toolbar", "Toolbar"),
    ("selection_others", "Selection Others"),
    ("viewport_controls", "Viewport Controls"),
    ("edit_mode", "Edit Mode"),
    ("sculpt_mode", "Sculpt Mode"),
    ("modifiers", "Modifiers"),
)


# ============================================================
# TOUCHSCREEN QUICK FAVORITES
#
# These are NOT a separate favorites system.
#
# They are only the predefined items that Touchscreen can add
# to Blender's native Quick Favorites menu.
# ============================================================

TOUCHSCREEN_OBJECT_FAVORITES = (
    {
        "name": "Set Origin",
        "operator": "object.origin_set",
    },
    {
        "name": "Set Parent",
        "operator": "object.parent_set",
    },
    {
        "name": "Clear Parent",
        "operator": "object.parent_clear",
    },
    {
        "name": "Apply Scale",
        "operator": "object.transform_apply",
        "properties": {
            "location": False,
            "rotation": False,
            "scale": True,
        },
    },
    {
        "name": "All Transforms",
        "operator": "object.transform_apply",
        "properties": {
            "location": True,
            "rotation": True,
            "scale": True,
        },
    },
    {
        "name": "Visual Geometry to Mesh",
        "operator": "object.convert",
        "properties": {
            "target": "MESH",
            "keep_original": False,
        },
    },
    {
        "name": "Visual Geometry to Objects",
        "operator": "object.visual_geometry_to_objects",
    },
    {
        "name": "Make Instances Real",
        "operator": "object.duplicates_make_real",
    },
)


TOUCHSCREEN_EDIT_FAVORITES = (
    {
        "name": "Select Edge Loop",
        "operator": "mesh.loop_select",
        "properties": {
            "ring": False,
        },
    },
    {
        "name": "Select Edge Ring",
        "operator": "mesh.loop_select",
        "properties": {
            "ring": True,
        },
    },
    {
        "name": "Shortest Path",
        "operator": "mesh.shortest_path_pick",
    },
    {
        "name": "Edge Crease",
        "operator": "transform.edge_crease",
    },
    {
        "name": "To Circle",
        "operator": "mesh.loop_to_circle",
    },
    {
        "name": "Space Edge Loops Evenly",
        "operator": "mesh.looptools_space",
    },
    {
        "name": "Symmetrize",
        "operator": "mesh.symmetrize",
    },
    {
        "name": "Flip Normals",
        "operator": "mesh.flip_normals",
    },
    {
        "name": "Recalculate Outside",
        "operator": "mesh.normals_make_consistent",
        "properties": {
            "inside": False,
        },
    },
)


# ============================================================
# MODULE IMPORT
# ============================================================

MODULES = []

for _name, _label in _MODULE_NAMES:
    _module = importlib.import_module(
        f".{_name}",
        __package__
    )
    MODULES.append(
        (_name, _label, _module)
    )

MODULES = tuple(MODULES)


# ============================================================
# MODULE ENABLE / DISABLE
# ============================================================

def _set_module(name, enabled):

    mod = next(
        m for k, _l, m in MODULES
        if k == name
    )

    try:
        if enabled:
            mod.register()
        else:
            mod.unregister()

    except Exception as e:
        print(
            f"Touchscreen - {name}: {e}"
        )


def _u(name):
    return lambda self, context: _set_module(
        name,
        getattr(self, name)
    )


# ============================================================
# QUICK FAVORITES HELPERS
# ============================================================

def _wm_user_menu_add_operator(
    name,
    operator,
    properties=None,
):
    """
    Add one operator to Blender's native Quick Favorites.

    This deliberately uses Blender's own wm.user_menu_add
    operator instead of creating a second Touchscreen favorites
    menu.
    """

    properties = properties or {}

    try:
        user_menu_add = bpy.ops.wm.user_menu_add

    except AttributeError:
        print(
            "Touchscreen: bpy.ops.wm.user_menu_add "
            "is not available in this Blender build."
        )
        return False

    try:
        rna = user_menu_add.get_rna_type()
        available = {
            prop.identifier
            for prop in rna.properties
            if prop.identifier != "rna_type"
        }
    except Exception:
        available = set()

    kwargs = {}

    # Main item information.
    if "type" in available:
        kwargs["type"] = 'OPERATOR'

    if "name" in available:
        kwargs["name"] = name

    if "op_idname" in available:
        kwargs["op_idname"] = operator

    # Some Blender versions expose the operator enum
    # property separately.
    if "op_prop_enum" in available:
        kwargs["op_prop_enum"] = ""

    # Some versions use menu_idname as an optional target.
    # Leave it unset when Blender can determine the current
    # user-menu from the current context.
    #
    # This is important because Quick Favorites are context
    # specific in Blender.
    #
    # We intentionally do not create our own menu here.

    # --------------------------------------------------------
    # Operator properties
    # --------------------------------------------------------
    #
    # Blender's native user-menu operator stores operator
    # properties as part of the user-menu item. Different
    # Blender builds expose this through slightly different
    # RNA layouts, so we first try the explicit property
    # container if present.
    # --------------------------------------------------------

    if properties:

        if "properties" in available:
            kwargs["properties"] = str(properties)

        elif "prop" in available:
            kwargs["prop"] = str(properties)

        elif "prop_value" in available:
            kwargs["prop_value"] = str(properties)

    try:
        result = user_menu_add(
            'EXEC_DEFAULT',
            **kwargs
        )

        return 'FINISHED' in result

    except TypeError:
        # Fall back to the minimal operator form.
        # This keeps the simple favorites usable on builds
        # where the property-storage interface differs.
        try:
            minimal = {}

            if "type" in available:
                minimal["type"] = 'OPERATOR'

            if "name" in available:
                minimal["name"] = name

            if "op_idname" in available:
                minimal["op_idname"] = operator

            result = user_menu_add(
                'EXEC_DEFAULT',
                **minimal
            )

            return 'FINISHED' in result

        except Exception as e:
            print(
                f"Touchscreen: could not add "
                f"'{name}' ({operator}): {e}"
            )
            return False

    except Exception as e:
        print(
            f"Touchscreen: could not add "
            f"'{name}' ({operator}): {e}"
        )
        return False


def _load_favorites_for_current_mode(items):
    """
    Add the supplied predefined items to Blender's native
    Quick Favorites for the current context.
    """

    added = 0

    for item in items:

        if _wm_user_menu_add_operator(
            item["name"],
            item["operator"],
            item.get("properties"),
        ):
            added += 1

    return added


def _find_view3d_context():
    """
    Find a VIEW_3D context to use while populating native
    Quick Favorites.
    """

    wm = bpy.context.window_manager

    for window in wm.windows:

        screen = window.screen

        for area in screen.areas:

            if area.type != 'VIEW_3D':
                continue

            region = next(
                (
                    region
                    for region in area.regions
                    if region.type == 'WINDOW'
                ),
                None
            )

            if region is not None:
                return window, area, region

    return None


# ============================================================
# LOAD TOUCHSCREEN FAVORITES
# ============================================================

class TOUCHSCREEN_OT_load_favorites(bpy.types.Operator):

    bl_idname = "touchscreen.load_favorites"
    bl_label = "Load Touchscreen Favorites"
    bl_description = (
        "Add the predefined Touchscreen favorites "
        "to Blender's native Quick Favorites"
    )

    def invoke(self, context, event):

        return context.window_manager.invoke_confirm(
            self,
            event
        )

    def execute(self, context):

        context_info = _find_view3d_context()

        if context_info is None:
            self.report(
                {'ERROR'},
                "A 3D Viewport is required to load Quick Favorites"
            )
            return {'CANCELLED'}

        window, area, region = context_info

        original_object = None

        try:
            original_object = context.view_layer.objects.active
        except Exception:
            pass

        added_object = 0
        added_edit = 0

        # ----------------------------------------------------
        # OBJECT FAVORITES
        # ----------------------------------------------------

        try:

            with context.temp_override(
                window=window,
                area=area,
                region=region,
            ):

                # Object mode is required because Blender's
                # native user menu is context-specific.
                if context.mode != 'OBJECT':

                    if (
                        context.active_object is not None
                        and context.active_object.mode != 'OBJECT'
                    ):
                        bpy.ops.object.mode_set(
                            mode='OBJECT'
                        )

                added_object = _load_favorites_for_current_mode(
                    TOUCHSCREEN_OBJECT_FAVORITES
                )

                # ------------------------------------------------
                # EDIT MESH FAVORITES
                # ------------------------------------------------

                active = context.view_layer.objects.active

                if (
                    active is not None
                    and active.type == 'MESH'
                ):

                    bpy.ops.object.mode_set(
                        mode='EDIT'
                    )

                    added_edit = _load_favorites_for_current_mode(
                        TOUCHSCREEN_EDIT_FAVORITES
                    )

                    # Return to Object Mode so that the user's
                    # original mode can be restored below.
                    bpy.ops.object.mode_set(
                        mode='OBJECT'
                    )

        except Exception as e:

            self.report(
                {'ERROR'},
                f"Could not load Touchscreen Favorites: {e}"
            )

            return {'CANCELLED'}

        finally:

            # ------------------------------------------------
            # Restore the active object's original mode.
            # ------------------------------------------------

            try:

                if (
                    original_object is not None
                    and original_object.name in
                    bpy.context.view_layer.objects
                ):

                    bpy.context.view_layer.objects.active = (
                        original_object
                    )

                    original_object.select_set(True)

            except Exception:
                pass

        total = added_object + added_edit

        self.report(
            {'INFO'},
            f"Touchscreen Favorites loaded: {total}"
        )

        return {'FINISHED'}


# ============================================================
# ADDON PREFERENCES
# ============================================================

class TOUCHSCREEN_Preferences(
    bpy.types.AddonPreferences
):

    bl_idname = __package__

    toolbar: bpy.props.BoolProperty(
        name="Toolbar",
        default=True,
        update=_u("toolbar")
    )

    selection_others: bpy.props.BoolProperty(
        name="Selection Others",
        default=True,
        update=_u("selection_others")
    )

    viewport_controls: bpy.props.BoolProperty(
        name="Viewport Controls",
        default=True,
        update=_u("viewport_controls")
    )

    viewport_controls_2x: bpy.props.BoolProperty(
        name="Viewport Controls 2x",
        description="Scale the Viewport Controls to 2x size",
        default=True,
    )

    edit_mode: bpy.props.BoolProperty(
        name="Edit Mode",
        default=True,
        update=_u("edit_mode")
    )

    sculpt_mode: bpy.props.BoolProperty(
        name="Sculpt Mode",
        default=True,
        update=_u("sculpt_mode")
    )

    modifiers: bpy.props.BoolProperty(
        name="Modifiers",
        default=True,
        update=_u("modifiers")
    )

    def draw(self, context):

        layout = self.layout

        # ----------------------------------------------------
        # MODULES
        # ----------------------------------------------------

        box = layout.box()

        box.label(
            text="Modules"
        )

        for prop, label, _ in MODULES:

            box.prop(
                self,
                prop,
                text=label
            )

        # ----------------------------------------------------
        # VIEWPORT CONTROLS SIZE
        # ----------------------------------------------------

        box = layout.box()

        box.label(
            text="Viewport Controls Size"
        )

        row = box.row(
            align=True
        )

        row.prop(
            self,
            "viewport_controls_2x",
            text="2x Size",
            toggle=True
        )

        # ----------------------------------------------------
        # QUICK FAVORITES
        # ----------------------------------------------------

        box = layout.box()

        box.label(
            text="Quick Favorites"
        )

        box.label(
            text=(
                "Add Touchscreen's predefined favorites "
                "to Blender's Quick Favorites."
            ),
            icon='INFO'
        )

        box.operator(
            TOUCHSCREEN_OT_load_favorites.bl_idname,
            text="Load Touchscreen Favorites",
            icon='SOLO_OFF'
        )


# ============================================================
# REGISTER
# ============================================================

CLASSES = (
    TOUCHSCREEN_OT_load_favorites,
    TOUCHSCREEN_Preferences,
)


def register():

    # Preferences must be registered first.
    for cls in CLASSES:

        try:
            bpy.utils.register_class(cls)

        except ValueError:
            pass

    prefs = bpy.context.preferences.addons[
        __package__
    ].preferences

    # Register enabled modules.
    for prop, _label, mod in MODULES:

        if getattr(
            prefs,
            prop,
            True
        ):

            try:
                mod.register()

            except Exception as e:

                print(
                    f"Touchscreen - {prop}: {e}"
                )


def unregister():

    # Unregister modules first.
    for _prop, _label, mod in reversed(MODULES):

        try:
            mod.unregister()

        except Exception:
            pass

    # Then unregister preferences/operators.
    for cls in reversed(CLASSES):

        try:
            bpy.utils.unregister_class(cls)

        except Exception:
            pass