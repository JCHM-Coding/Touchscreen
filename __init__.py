# SPDX-License-Identifier: GPL-3.0-or-later
# Touchscreen - modular touch-screen helpers
# Copyright (C) 2026 JCHM

bl_info = {
    "name": "Touchscreen",
    "author": "JCHM",
    "version": (1, 0, 1),
    "blender": (5, 3, 0),
    "location": "Edit > Preferences > Add-ons",
    "description": "Touch-screen helpers organized into independently enabled modules.",
    "category": "3D View",
    "license": "GPL-3.0-or-later",
}

import bpy
import importlib


# ============================================================
# MODULES
# ============================================================

_MODULE_NAMES = (
    ("toolbar", "Toolbar"),
    ("selection_others", "Selection Others"),
    ("viewport_controls", "Viewport Controls"),
    ("edit_mode", "Edit Mode"),
    ("sculpt_mode", "Sculpt Mode"),
    ("modifiers", "Modifiers"),
)

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
# MODULE HELPERS
# ============================================================

def _set_module(name, enabled):

    mod = next(
        m
        for k, _l, m in MODULES
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
# TOOLBAR LAYOUT UPDATE
# ============================================================

def _update_toolbar_layout(self, context):

    toolbar_module = next(
        (
            mod
            for name, _label, mod in MODULES
            if name == "toolbar"
        ),
        None
    )

    if toolbar_module is None:
        return

    try:

        toolbar_module.update_native_toolbar_layout()

    except Exception as e:

        print(
            f"Touchscreen - Toolbar Layout: {e}"
        )


# ============================================================
# PREFERENCES
# ============================================================

class TOUCHSCREEN_Preferences(
    bpy.types.AddonPreferences
):

    bl_idname = __package__

    # --------------------------------------------------------
    # MODULES
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # TOOLBAR LAYOUT
    # --------------------------------------------------------

    native_toolbar_layout: bpy.props.EnumProperty(
        name="Toolbar",
        description="Choose the layout used by the native Blender toolbar",
        items=[
            (
                "BLENDER",
                "Blender Default",
                "Use Blender's default toolbar layout"
            ),
            (
                "4_COLUMNS",
                "4 Columns",
                "Use the Touchscreen automatic 1, 2, 3, 4 columns and text layout"
            ),
        ],
        default="BLENDER",
        update=_update_toolbar_layout,
    )

    # --------------------------------------------------------
    # DRAW
    # --------------------------------------------------------

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
        # TOOLBAR
        # ----------------------------------------------------

        box = layout.box()

        box.label(
            text="Toolbar"
        )

        row = box.row(
            align=True
        )

        row.prop(
            self,
            "native_toolbar_layout",
            expand=True
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


# ============================================================
# REGISTER
# ============================================================

CLASSES = (
    TOUCHSCREEN_Preferences,
)


def register():

    for cls in CLASSES:

        bpy.utils.register_class(
            cls
        )

    prefs = bpy.context.preferences.addons[
        __package__
    ].preferences

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


# ============================================================
# UNREGISTER
# ============================================================

def unregister():

    for _prop, _label, mod in reversed(MODULES):

        try:

            mod.unregister()

        except Exception:
            pass

    for cls in reversed(CLASSES):

        try:

            bpy.utils.unregister_class(
                cls
            )

        except Exception:
            pass