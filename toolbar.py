# ============================================================
# QUICK FAVORITES
# ============================================================

import json


# ------------------------------------------------------------
# DEFAULT TOUCHSCREEN FAVORITES
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# FAVORITE DEFINITIONS
# ------------------------------------------------------------

TOUCHSCREEN_OBJECT_FAVORITES = {
    "object.set_origin": (
        "Set Origin",
        'OBJECT_ORIGIN'
    ),

    "object.parent_set": (
        "Set Parent",
        'CONSTRAINT'
    ),

    "object.parent_clear": (
        "Clear Parent",
        'X'
    ),

    "object.apply_scale": (
        "Apply Scale",
        'OBJECT_ORIGIN'
    ),

    "object.all_transforms": (
        "All Transforms",
        'OBJECT_ORIGIN'
    ),

    "object.visual_geometry_to_mesh": (
        "Visual Geometry to Mesh",
        'MESH_DATA'
    ),

    "object.visual_geometry_to_objects": (
        "Visual Geometry to Objects",
        'MESH_DATA'
    ),

    "object.make_instances_real": (
        "Make Instances Real",
        'DUPLICATE'
    ),
}


TOUCHSCREEN_EDIT_FAVORITES = {
    "mesh.select_edge_loop": (
        "Select Edge Loop",
        'EDGESEL'
    ),

    "mesh.select_edge_ring": (
        "Select Edge Ring",
        'EDGESEL'
    ),

    "mesh.shortest_path": (
        "Shortest Path",
        'EDGESEL'
    ),

    "mesh.edge_crease": (
        "Edge Crease",
        'CREASE'
    ),

    "mesh.to_circle": (
        "To Circle",
        'SPHERE'
    ),

    "mesh.space_edge_loops_evenly": (
        "Space Edge Loops Evenly",
        'LOOPSEL'
    ),

    "mesh.symmetrize": (
        "Symmetrize",
        'MOD_MIRROR'
    ),

    "mesh.flip_normals": (
        "Flip Normals",
        'NORMALS_FACE'
    ),

    "mesh.recalculate_outside": (
        "Recalculate Outside",
        'NORMALS_FACE'
    ),
}


def _get_touchscreen_preferences():

    try:
        addon = bpy.context.preferences.addons.get(
            __package__
        )

        if addon is None:
            return None

        return addon.preferences

    except Exception:
        return None


def _get_favorite_list(mode):

    prefs = _get_touchscreen_preferences()

    if prefs is None:
        return []

    try:
        if mode == 'OBJECT':
            raw = prefs.touchscreen_object_favorites
        else:
            raw = prefs.touchscreen_edit_favorites

        if not raw:
            return []

        result = json.loads(raw)

        if isinstance(result, list):
            return result

    except (
        TypeError,
        ValueError,
        json.JSONDecodeError
    ):
        pass

    return []


def _set_favorite_list(mode, favorites):

    prefs = _get_touchscreen_preferences()

    if prefs is None:
        return

    value = json.dumps(
        list(favorites)
    )

    if mode == 'OBJECT':
        prefs.touchscreen_object_favorites = value
    else:
        prefs.touchscreen_edit_favorites = value


def _favorite_definitions(mode):

    if mode == 'OBJECT':
        return TOUCHSCREEN_OBJECT_FAVORITES

    if mode == 'EDIT_MESH':
        return TOUCHSCREEN_EDIT_FAVORITES

    return {}


def _favorite_operator(favorite_id, context):

    # --------------------------------------------------------
    # OBJECT MODE
    # --------------------------------------------------------

    if favorite_id == "object.set_origin":
        return bpy.ops.object.origin_set(
            'INVOKE_DEFAULT'
        )

    if favorite_id == "object.parent_set":
        return bpy.ops.object.parent_set(
            'INVOKE_DEFAULT'
        )

    if favorite_id == "object.parent_clear":
        return bpy.ops.object.parent_clear(
            type='CLEAR'
        )

    if favorite_id == "object.apply_scale":
        return bpy.ops.object.transform_apply(
            location=False,
            rotation=False,
            scale=True
        )

    if favorite_id == "object.all_transforms":
        return bpy.ops.object.transform_apply(
            location=True,
            rotation=True,
            scale=True
        )

    if favorite_id == "object.visual_geometry_to_mesh":
        return bpy.ops.object.convert(
            target='MESH',
            keep_original=False
        )

    if favorite_id == "object.visual_geometry_to_objects":
        return bpy.ops.object.visual_geometry_to_objects()

    if favorite_id == "object.make_instances_real":
        return bpy.ops.object.duplicates_make_real()

    # --------------------------------------------------------
    # EDIT MODE
    # --------------------------------------------------------

    if favorite_id == "mesh.select_edge_loop":
        return bpy.ops.mesh.loop_select(
            'INVOKE_DEFAULT',
            extend=False,
            deselect=False,
            toggle=False,
            ring=False
        )

    if favorite_id == "mesh.select_edge_ring":
        return bpy.ops.mesh.loop_select(
            'INVOKE_DEFAULT',
            extend=False,
            deselect=False,
            toggle=False,
            ring=True
        )

    if favorite_id == "mesh.shortest_path":
        return bpy.ops.mesh.shortest_path_pick(
            'INVOKE_DEFAULT'
        )

    if favorite_id == "mesh.edge_crease":
        return bpy.ops.transform.edge_crease(
            'INVOKE_DEFAULT'
        )

    if favorite_id == "mesh.to_circle":
        return bpy.ops.transform.tosphere(
            'INVOKE_DEFAULT',
            value=1.0
        )

    if favorite_id == "mesh.space_edge_loops_evenly":
        return bpy.ops.mesh.looptools_space(
            'INVOKE_DEFAULT'
        )

    if favorite_id == "mesh.symmetrize":
        return bpy.ops.mesh.symmetrize(
            'INVOKE_DEFAULT'
        )

    if favorite_id == "mesh.flip_normals":
        return bpy.ops.mesh.flip_normals()

    if favorite_id == "mesh.recalculate_outside":
        return bpy.ops.mesh.normals_make_consistent(
            inside=False
        )

    return {'CANCELLED'}


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

        if not self.favorite_id:
            return {'CANCELLED'}

        try:
            result = _favorite_operator(
                self.favorite_id,
                context
            )

        except (
            RuntimeError,
            AttributeError
        ) as e:

            self.report(
                {'ERROR'},
                str(e)
            )

            return {'CANCELLED'}

        return result


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
            'EDIT_MESH'
        }:
            return {'CANCELLED'}

        favorites = _get_favorite_list(
            self.favorite_mode
        )

        if self.favorite_id in favorites:
            favorites.remove(
                self.favorite_id
            )

            _set_favorite_list(
                self.favorite_mode,
                favorites
            )

        return {'FINISHED'}


class VIEW3D_OT_touchscreen_load_default_favorites(
    bpy.types.Operator
):
    bl_idname = "view3d.touchscreen_load_default_favorites"
    bl_label = "Load Default"

    def execute(self, context):

        prefs = _get_touchscreen_preferences()

        if prefs is None:
            return {'CANCELLED'}

        prefs.touchscreen_object_favorites = json.dumps(
            list(DEFAULT_OBJECT_FAVORITES)
        )

        prefs.touchscreen_edit_favorites = json.dumps(
            list(DEFAULT_EDIT_FAVORITES)
        )

        prefs.favorites_source = 'TOUCHSCREEN'

        return {'FINISHED'}


def _draw_touchscreen_favorite_context_menu(
    self,
    context
):

    favorite_id = getattr(
        context,
        "touchscreen_favorite_id",
        ""
    )

    favorite_mode = getattr(
        context,
        "touchscreen_favorite_mode",
        ""
    )

    if not favorite_id:
        return

    if favorite_mode not in {
        'OBJECT',
        'EDIT_MESH'
    }:
        return

    prefs = _get_touchscreen_preferences()

    if prefs is None:
        return

    if prefs.favorites_source != 'TOUCHSCREEN':
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


class VIEW3D_MT_touchscreen_favorites(
    bpy.types.Menu
):

    bl_idname = "VIEW3D_MT_touchscreen_favorites"
    bl_label = "Quick Favorites"

    def draw(self, context):

        prefs = _get_touchscreen_preferences()

        if prefs is None:
            return

        # ----------------------------------------------------
        # NATIVE BLENDER FAVORITES
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
            'EDIT_MESH'
        }:
            return

        favorites = _get_favorite_list(
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

            # Store the identity of this button in the
            # context used by Blender's right-click menu.
            layout.context_pointer_set(
                "touchscreen_favorite_id",
                favorite_id
            )

            layout.context_pointer_set(
                "touchscreen_favorite_mode",
                mode
            )

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