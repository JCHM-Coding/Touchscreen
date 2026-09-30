import bpy
from bl_ui.space_toolsystem_common import ToolSelectPanelHelper


# ------------------------------------------------------------
# Touchscreen Toolbar
# ------------------------------------------------------------

_ORIGINAL_LAYOUT_DETECT = None
_PATCH_INSTALLED = False


# ------------------------------------------------------------
# Shared layout calculation
# ------------------------------------------------------------

def _get_toolbar_layout(context):

    region = context.region

    if region is None:
        return 1, False

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

    except (AttributeError, TypeError, ZeroDivisionError):
        return 1, False

    if width_scale <= 80.0:
        columns = 1
        show_text = False

    elif width_scale <= 120.0:
        columns = 2
        show_text = False

    elif width_scale <= 160.0:
        columns = 3
        show_text = False

    elif width_scale <= 185.0:
        columns = 4
        show_text = False

    else:
        columns = 1
        show_text = True

    return columns, show_text


# ------------------------------------------------------------
# Native Blender toolbar patch
# ------------------------------------------------------------

def _native_toolbar_patch(cls, layout, region, scale_y):

    # --------------------------------------------------------
    # Only modify VIEW_3D
    # --------------------------------------------------------

    space = bpy.context.space_data

    if (
        space is None
        or space.type != 'VIEW_3D'
    ):
        return _ORIGINAL_LAYOUT_DETECT(
            layout,
            region,
            scale_y,
        )

    # --------------------------------------------------------
    # Check Touchscreen preference
    # --------------------------------------------------------

    try:
        prefs = bpy.context.preferences.addons[
            __package__.split(".")[0]
        ].preferences
    except Exception:
        prefs = None

    if (
        prefs is None
        or prefs.native_toolbar_layout != "TOUCHSCREEN"
    ):
        return _ORIGINAL_LAYOUT_DETECT(
            layout,
            region,
            scale_y,
        )

    # --------------------------------------------------------
    # Calculate Touchscreen layout
    # --------------------------------------------------------

    columns, show_text = _get_toolbar_layout(
        bpy.context
    )

    # --------------------------------------------------------
    # Build Blender's native generator
    # --------------------------------------------------------

    if columns == 1:
        ui_gen = cls._layout_generator_single_column(
            layout,
            scale_y=scale_y,
        )
    else:
        ui_gen = cls._layout_generator_multi_columns(
            layout,
            column_count=columns,
            scale_y=scale_y,
        )

    return ui_gen, show_text


def _install_native_toolbar_patch():

    global _ORIGINAL_LAYOUT_DETECT
    global _PATCH_INSTALLED

    if _PATCH_INSTALLED:
        return

    # Store the actual classmethod descriptor
    _ORIGINAL_LAYOUT_DETECT = (
        ToolSelectPanelHelper
        .__dict__
        .get("_layout_generator_detect_from_region")
    )

    if _ORIGINAL_LAYOUT_DETECT is None:
        print(
            "Touchscreen - Could not find Blender "
            "toolbar layout function"
        )
        return

    ToolSelectPanelHelper._layout_generator_detect_from_region = (
        classmethod(
            _native_toolbar_patch
        )
    )

    _PATCH_INSTALLED = True

    print(
        "Touchscreen - Native VIEW_3D "
        "toolbar patch installed"
    )


def _remove_native_toolbar_patch():

    global _ORIGINAL_LAYOUT_DETECT
    global _PATCH_INSTALLED

    if not _PATCH_INSTALLED:
        return

    if _ORIGINAL_LAYOUT_DETECT is not None:

        ToolSelectPanelHelper._layout_generator_detect_from_region = (
            _ORIGINAL_LAYOUT_DETECT
        )

    _ORIGINAL_LAYOUT_DETECT = None
    _PATCH_INSTALLED = False

    print(
        "Touchscreen - Native VIEW_3D "
        "toolbar patch removed"
    )


# ------------------------------------------------------------
# Your Touchscreen toolbar
# ------------------------------------------------------------

def _draw_button(layout, item, show_text):

    try:
        op = layout.operator(
            item.operator,
            text=item.label if show_text else "",
            icon=item.icon,
        )

        for prop_name, prop_value in item.properties.items():
            try:
                setattr(
                    op,
                    prop_name,
                    prop_value,
                )
            except Exception:
                pass

    except Exception as e:
        print(
            f"Touchscreen - toolbar button error: {e}"
        )


def _draw_group(layout, items, show_text):

    if not items:
        return

    if show_text:
        for item in items:
            _draw_button(
                layout,
                item,
                True,
            )

    else:
        for item in items:
            _draw_button(
                layout,
                item,
                False,
            )


# ------------------------------------------------------------
# Main Touchscreen toolbar
# ------------------------------------------------------------

def draw_toolbar(self, context):

    columns, show_text = _get_toolbar_layout(
        context
    )

    layout = self.layout

    grid = layout.grid_flow(
        row_major=True,
        columns=columns,
        even_columns=True,
        even_rows=False,
        align=True,
    )

    grid.scale_y = 2.0

    # --------------------------------------------------------
    # Existing Touchscreen toolbar groups
    #
    # Keep your existing mode/group construction here.
    # --------------------------------------------------------

    # Example:
    #
    # for group in groups:
    #     _draw_group(
    #         grid,
    #         group,
    #         show_text,
    #     )


# ------------------------------------------------------------
# Register / Unregister
# ------------------------------------------------------------

def register():

    _install_native_toolbar_patch()

    bpy.types.VIEW3D_PT_tools_active.append(
        draw_toolbar
    )


def unregister():

    try:
        bpy.types.VIEW3D_PT_tools_active.remove(
            draw_toolbar
        )
    except Exception:
        pass

    _remove_native_toolbar_patch()