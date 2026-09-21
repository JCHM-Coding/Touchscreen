# SPDX-License-Identifier: GPL-3.0-or-later
#
# Touchscreen - Modifiers
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

def get_active_object(context):

    obj = context.active_object

    if obj is None:
        return None

    if obj.type not in {'MESH', 'CURVE'}:
        return None

    return obj

def get_modifier(obj, index):

    if obj is None:
        return None

    if index < 0:
        return None

    if index >= len(obj.modifiers):
        return None

    return obj.modifiers[index]

def safe_prop(obj, name):

    return hasattr(obj, name)

def save_context(context):

    obj = context.active_object

    if obj is None:
        return None

    return {
        "object": obj,
        "mode": context.mode,
        "selected": list(context.selected_objects),
    }

def enter_object_mode(context):

    state = save_context(context)

    if state is None:
        return None

    if context.mode != 'OBJECT':

        try:

            bpy.ops.object.mode_set(
                mode='OBJECT'
            )

        except RuntimeError:

            return None

    return state

def restore_context(context, state):

    if state is None:
        return

    obj = state["object"]

    if obj is None:
        return

    if obj.name not in bpy.data.objects:
        return

    if context.mode != 'OBJECT':

        try:

            bpy.ops.object.mode_set(
                mode='OBJECT'
            )

        except RuntimeError:

            pass

    try:

        for selected in context.selected_objects:
            selected.select_set(False)

        for selected in state["selected"]:

            if selected.name in bpy.data.objects:
                selected.select_set(True)

        bpy.context.view_layer.objects.active = obj

    except RuntimeError:

        pass

    original_mode = state["mode"]

    if original_mode == 'OBJECT':
        return

    if original_mode.startswith('EDIT_'):
        target_mode = 'EDIT'

    elif original_mode == 'POSE':
        target_mode = 'POSE'

    else:
        target_mode = original_mode

    try:

        bpy.ops.object.mode_set(
            mode=target_mode
        )

    except RuntimeError:

        pass

def set_active_only(context, obj):

    bpy.context.view_layer.objects.active = obj

    for selected in context.selected_objects:
        selected.select_set(False)

    obj.select_set(True)

def add_modern_array(context, obj):

    set_active_only(context, obj)

    before = set(obj.modifiers)

    try:

        result = bpy.ops.object.modifier_add_node_group(
            asset_library_type='ESSENTIALS',
            asset_library_identifier='',
            relative_asset_identifier=(
                "nodes/geometry_nodes_essentials.blend/"
                "NodeTree/Array"
            ),
            use_selected_objects=False
        )

    except Exception as error:

        raise RuntimeError(
            f"Could not add Blender Array: {error}"
        )

    if 'FINISHED' not in result:

        raise RuntimeError(
            "Blender could not add the Array modifier"
        )

    modifier = None

    for candidate in obj.modifiers:

        if candidate not in before:
            modifier = candidate
            break

    if modifier is None and obj.modifiers:
        modifier = obj.modifiers[-1]

    if modifier is None:
        raise RuntimeError(
            "Array modifier was not created"
        )

    modifier.name = "Array +"

    return modifier

def add_scatter_on_surface(context, obj):

    set_active_only(
        context,
        obj
    )

    before = set(obj.modifiers)

    try:

        result = bpy.ops.object.modifier_add_node_group(
            asset_library_type='ESSENTIALS',
            asset_library_identifier='',
            relative_asset_identifier=(
                "nodes/geometry_nodes_essentials.blend/"
                "NodeTree/Scatter on Surface"
            ),
            use_selected_objects=False
        )

    except Exception as error:

        raise RuntimeError(
            f"Could not add Scatter on Surface: {error}"
        )

    if 'FINISHED' not in result:

        raise RuntimeError(
            "Blender could not add Scatter on Surface"
        )

    modifier = None

    for candidate in obj.modifiers:

        if candidate not in before:
            modifier = candidate
            break

    if modifier is None and obj.modifiers:
        modifier = obj.modifiers[-1]

    if modifier is None:

        raise RuntimeError(
            "Scatter on Surface modifier was not created"
        )

    modifier.name = "Scatter"

    return modifier

def draw_node_group_inputs(layout, modifier):

    if modifier is None:
        return

    if not safe_prop(modifier, "node_group"):
        return

    node_group = modifier.node_group

    if node_group is None:
        return

    interface = node_group.interface

    if interface is None:
        return

    try:

        items = interface.items_tree

    except AttributeError:

        return

    for item in items:

        if getattr(item, "item_type", None) != 'SOCKET':
            continue

        if getattr(item, "in_out", None) != 'INPUT':
            continue

        identifier = getattr(
            item,
            "identifier",
            ""
        )

        if not identifier:
            continue

        try:

            layout.prop(
                modifier,
                f'["{identifier}"]',
                text=item.name
            )

        except Exception:

            pass

def build_boolean_plus(context, obj):
    # ADVANCED BOOLEAN
    # Blender 5.3
    #
    # BASIC OPERATIONS
    #
    # Difference
    # Union
    # Intersect
    # Slice
    # Deboss
    # Emboss
    # =========================================================


    GROUP_NAME = "Boolean +"


    # =========================================================
    # UTILIDADES
    # =========================================================

    def get_input(node, name):

        for socket in node.inputs:

            if socket.name == name:
                return socket

        return None


    def get_output(node, name):

        for socket in node.outputs:

            if socket.name == name:
                return socket

        return None


    def link(links, output_socket, input_socket):

        if output_socket is None:

            print("Missing socket")
            return

        if input_socket is None:

            print("Missing socket")
            return

        try:

            links.new(
                output_socket,
                input_socket
            )

        except Exception as error:

            print(
                "Link error:",
                error
            )


    # =========================================================
    # ELIMINAR GRUPO ANTERIOR
    # =========================================================

    old_group = bpy.data.node_groups.get(
        GROUP_NAME
    )

    if old_group:

        bpy.data.node_groups.remove(
            old_group,
            do_unlink=True
        )


    # =========================================================
    # CREAR NODE GROUP
    # =========================================================

    ng = bpy.data.node_groups.new(
        GROUP_NAME,
        'GeometryNodeTree'
    )

    ng.is_modifier = True
    ng.is_type_mesh = True

    interface = ng.interface


    # =========================================================
    # INTERFACE
    # =========================================================


    # ---------------------------------------------------------
    # GEOMETRY
    # ---------------------------------------------------------

    interface.new_socket(
        name="Geometry",
        in_out='INPUT',
        socket_type='NodeSocketGeometry'
    )


    # ---------------------------------------------------------
    # BOOLEAN
    # ---------------------------------------------------------

    interface.new_socket(
        name="Boolean",
        in_out='INPUT',
        socket_type='NodeSocketMenu'
    )


    # ---------------------------------------------------------
    # OBJ / COLL
    # ---------------------------------------------------------

    interface.new_socket(
        name="Obj / Coll",
        in_out='INPUT',
        socket_type='NodeSocketBool'
    )


    # ---------------------------------------------------------
    # OBJECT
    # ---------------------------------------------------------

    interface.new_socket(
        name="Object",
        in_out='INPUT',
        socket_type='NodeSocketObject'
    )


    # ---------------------------------------------------------
    # COLLECTION
    # ---------------------------------------------------------

    interface.new_socket(
        name="Collection",
        in_out='INPUT',
        socket_type='NodeSocketCollection'
    )


    # ---------------------------------------------------------
    # BEVEL
    # ---------------------------------------------------------

    offset_socket = interface.new_socket(
        name="Bevel",
        in_out='INPUT',
        socket_type='NodeSocketFloat'
    )

    offset_socket.default_value = 0.1
    offset_socket.min_value = 0.0
    offset_socket.max_value = 1000.0



    # ---------------------------------------------------------
    # SEGMENTS
    # ---------------------------------------------------------

    segments_socket = interface.new_socket(
        name="Segments",
        in_out='INPUT',
        socket_type='NodeSocketInt'
    )

    segments_socket.default_value = 2
    segments_socket.min_value = 1
    segments_socket.max_value = 100


    # ---------------------------------------------------------
    # SHAPE
    # ---------------------------------------------------------

    shape_socket = interface.new_socket(
        name="Shape",
        in_out='INPUT',
        socket_type='NodeSocketFloat'
    )

    shape_socket.default_value = 0.5
    shape_socket.min_value = 0.0
    shape_socket.max_value = 1.0


    # ---------------------------------------------------------
    # OFFSET 1
    # ---------------------------------------------------------

    offset_1_socket = interface.new_socket(
        name="Offset 1",
        in_out='INPUT',
        socket_type='NodeSocketFloat'
    )

    offset_1_socket.default_value = 0.1
    offset_1_socket.min_value = 0.0
    offset_1_socket.max_value = 1000.0


    # ---------------------------------------------------------
    # OFFSET 2
    # ---------------------------------------------------------

    offset_2_socket = interface.new_socket(
        name="Offset 2",
        in_out='INPUT',
        socket_type='NodeSocketFloat'
    )

    offset_2_socket.default_value = 0.1
    offset_2_socket.min_value = 0.0
    offset_2_socket.max_value = 1000.0


    # ---------------------------------------------------------
    # BEVEL SELECTION
    # Separate menu input used ONLY by the bevel Selection switches.
    # The final Boolean menu remains independent.
    # ---------------------------------------------------------

    bevel_selection_socket = interface.new_socket(
        name="Bevel Selection",
        in_out='INPUT',
        socket_type='NodeSocketMenu'
    )
    bevel_selection_socket.menu_expanded = False


    # ---------------------------------------------------------
    # OUTPUT
    # ---------------------------------------------------------

    interface.new_socket(
        name="Geometry",
        in_out='OUTPUT',
        socket_type='NodeSocketGeometry'
    )


    # =========================================================
    # NODES / LINKS
    # =========================================================

    nodes = ng.nodes
    links = ng.links


    # =========================================================
    # GROUP INPUT
    # =========================================================

    group_input = nodes.new(
        "NodeGroupInput"
    )

    group_input.name = "Group Input"
    group_input.location = (
        -1500,
        100
    )


    # =========================================================
    # GROUP OUTPUT
    # =========================================================

    group_output = nodes.new(
        "NodeGroupOutput"
    )

    group_output.name = "Group Output"
    group_output.location = (
        1200,
        100
    )


    # =========================================================
    # OBJECT INFO
    # =========================================================

    object_info = nodes.new(
        "GeometryNodeObjectInfo"
    )

    object_info.name = "Object Info"
    object_info.label = "Object Info"

    object_info.location = (
        -1500,
        -500
    )


    try:

        object_info.transform_space = 'RELATIVE'

    except Exception as error:

        print(
            "Object Info Relative error:",
            error
        )


    object_instance_socket = get_input(
        object_info,
        "As Instance"
    )

    if object_instance_socket is not None:

        object_instance_socket.default_value = False


    # =========================================================
    # COLLECTION INFO
    # =========================================================

    collection_info = nodes.new(
        "GeometryNodeCollectionInfo"
    )

    collection_info.name = "Collection Info"
    collection_info.label = "Collection Info"

    collection_info.location = (
        -1500,
        -750
    )


    try:

        collection_info.transform_space = 'RELATIVE'

    except Exception as error:

        print(
            "Collection Info Relative error:",
            error
        )


    collection_instance_socket = get_input(
        collection_info,
        "As Instance"
    )

    if collection_instance_socket is not None:

        collection_instance_socket.default_value = False


    # =========================================================
    # OBJECT / COLLECTION SWITCH
    # =========================================================

    secondary_switch = nodes.new(
        "GeometryNodeSwitch"
    )

    secondary_switch.name = "Object Collection Switch"
    secondary_switch.label = "Obj / Coll"

    secondary_switch.location = (
        -1200,
        -500
    )

    secondary_switch.input_type = 'GEOMETRY'


    # =========================================================
    # OBJECT → OBJECT INFO
    # =========================================================

    link(
        links,
        get_output(
            group_input,
            "Object"
        ),
        get_input(
            object_info,
            "Object"
        )
    )


    # =========================================================
    # COLLECTION → COLLECTION INFO
    # =========================================================

    link(
        links,
        get_output(
            group_input,
            "Collection"
        ),
        get_input(
            collection_info,
            "Collection"
        )
    )


    # =========================================================
    # OBJECT INFO → SWITCH FALSE
    # =========================================================

    link(
        links,
        get_output(
            object_info,
            "Geometry"
        ),
        get_input(
            secondary_switch,
            "False"
        )
    )


    # =========================================================
    # REALIZE COLLECTION INSTANCES
    # =========================================================

    realize_collection = nodes.new(
        "GeometryNodeRealizeInstances"
    )

    realize_collection.name = "Realize Collection Instances"
    realize_collection.label = "Realize All"
    realize_collection.location = (
        -1350,
        -750
    )

    realize_all_socket = get_input(
        realize_collection,
        "Realize All"
    )

    if realize_all_socket is not None:
        realize_all_socket.default_value = True


    # =========================================================
    # COLLECTION INFO → REALIZE INSTANCES
    # =========================================================

    link(
        links,
        get_output(
            collection_info,
            "Instances"
        ),
        get_input(
            realize_collection,
            "Geometry"
        )
    )


    # =========================================================
    # REALIZE INSTANCES → SWITCH TRUE
    # =========================================================

    link(
        links,
        get_output(
            realize_collection,
            "Geometry"
        ),
        get_input(
            secondary_switch,
            "True"
        )
    )


    # =========================================================
    # OBJ / COLL → SWITCH
    # =========================================================

    link(
        links,
        get_output(
            group_input,
            "Obj / Coll"
        ),
        get_input(
            secondary_switch,
            "Switch"
        )
    )


    # =========================================================
    # BOOLEAN DIFFERENCE
    # =========================================================

    boolean_difference = nodes.new(
        "GeometryNodeMeshBoolean"
    )

    boolean_difference.name = "Boolean Difference"
    boolean_difference.label = "Difference"

    boolean_difference.location = (
        -800,
        500
    )

    boolean_difference.operation = 'DIFFERENCE'
    boolean_difference.solver = 'EXACT'


    # =========================================================
    # BOOLEAN UNION
    # =========================================================

    boolean_union = nodes.new(
        "GeometryNodeMeshBoolean"
    )

    boolean_union.name = "Boolean Union"
    boolean_union.label = "Union"

    boolean_union.location = (
        -800,
        100
    )

    boolean_union.operation = 'UNION'
    boolean_union.solver = 'EXACT'


    # =========================================================
    # BOOLEAN INTERSECT
    # =========================================================

    boolean_intersect = nodes.new(
        "GeometryNodeMeshBoolean"
    )

    boolean_intersect.name = "Boolean Intersect"
    boolean_intersect.label = "Intersect"

    boolean_intersect.location = (
        -800,
        -300
    )

    boolean_intersect.operation = 'INTERSECT'
    boolean_intersect.solver = 'EXACT'


    # =========================================================
    # GEOMETRY OUTPUTS
    # =========================================================

    geometry_output = get_output(
        group_input,
        "Geometry"
    )

    secondary_geometry = get_output(
        secondary_switch,
        "Output"
    )


    # =========================================================
    # DIFFERENCE
    #
    # 0 = Mesh 1
    # 1 = Mesh 2
    # =========================================================

    link(
        links,
        geometry_output,
        boolean_difference.inputs[0]
    )

    link(
        links,
        secondary_geometry,
        boolean_difference.inputs[1]
    )


    # =========================================================
    # UNION
    #
    # Blender 5.3:
    # socket 1 = multi-input
    #
    # AMBAS GEOMETRÍAS VAN AL SOCKET 1
    # =========================================================

    link(
        links,
        geometry_output,
        boolean_union.inputs[1]
    )

    link(
        links,
        secondary_geometry,
        boolean_union.inputs[1]
    )


    # =========================================================
    # INTERSECT
    #
    # Blender 5.3:
    # socket 1 = multi-input
    #
    # AMBAS GEOMETRÍAS VAN AL SOCKET 1
    # =========================================================

    link(
        links,
        geometry_output,
        boolean_intersect.inputs[1]
    )

    link(
        links,
        secondary_geometry,
        boolean_intersect.inputs[1]
    )


    # =========================================================
    # BEVEL DIFFERENCE
    # =========================================================

    bevel_difference = nodes.new(
        "GeometryNodeMeshBevel"
    )

    bevel_difference.name = "Bevel Difference"
    bevel_difference.label = "Bevel Difference"

    bevel_difference.location = (
        -300,
        500
    )


    # =========================================================
    # BEVEL UNION
    # =========================================================

    bevel_union = nodes.new(
        "GeometryNodeMeshBevel"
    )

    bevel_union.name = "Bevel Union"
    bevel_union.label = "Bevel Union"

    bevel_union.location = (
        -300,
        100
    )


    # =========================================================
    # BEVEL INTERSECT
    # =========================================================

    bevel_intersect = nodes.new(
        "GeometryNodeMeshBevel"
    )

    bevel_intersect.name = "Bevel Intersect"
    bevel_intersect.label = "Bevel Intersect"

    bevel_intersect.location = (
        -300,
        -300
    )


    # =========================================================
    # DIFFERENCE → BEVEL
    # =========================================================

    link(
        links,
        get_output(
            boolean_difference,
            "Mesh"
        ),
        get_input(
            bevel_difference,
            "Mesh"
        )
    )

    link(
        links,
        get_output(
            boolean_difference,
            "Intersecting Edges"
        ),
        get_input(
            bevel_difference,
            "Selection"
        )
    )


    # =========================================================
    # UNION → BEVEL
    # =========================================================

    link(
        links,
        get_output(
            boolean_union,
            "Mesh"
        ),
        get_input(
            bevel_union,
            "Mesh"
        )
    )

    link(
        links,
        get_output(
            boolean_union,
            "Intersecting Edges"
        ),
        get_input(
            bevel_union,
            "Selection"
        )
    )


    # =========================================================
    # INTERSECT → BEVEL
    # =========================================================

    link(
        links,
        get_output(
            boolean_intersect,
            "Mesh"
        ),
        get_input(
            bevel_intersect,
            "Mesh"
        )
    )

    link(
        links,
        get_output(
            boolean_intersect,
            "Intersecting Edges"
        ),
        get_input(
            bevel_intersect,
            "Selection"
        )
    )


    # =========================================================
    # SHARED OFFSET
    # =========================================================

    offset_output = get_output(
        group_input,
        "Bevel"
    )


    for bevel in (
        bevel_difference,
        bevel_union,
        bevel_intersect
    ):

        for socket_name in (
            "Start Left Offset",
            "Start Right Offset",
            "End Left Offset",
            "End Right Offset"
        ):

            link(
                links,
                offset_output,
                get_input(
                    bevel,
                    socket_name
                )
            )


    # =========================================================
    # SHARED SEGMENTS
    # =========================================================

    segments_output = get_output(
        group_input,
        "Segments"
    )


    for bevel in (
        bevel_difference,
        bevel_union,
        bevel_intersect
    ):

        link(
            links,
            segments_output,
            get_input(
                bevel,
                "Segments"
            )
        )


    # =========================================================
    # SHARED SHAPE / PROFILE
    # =========================================================

    shape_output = get_output(
        group_input,
        "Shape"
    )


    for bevel in (
        bevel_difference,
        bevel_union,
        bevel_intersect
    ):

        shape_input = get_input(
            bevel,
            "Shape"
        )

        if shape_input is None:

            shape_input = get_input(
                bevel,
                "Profile"
            )

        link(
            links,
            shape_output,
            shape_input
        )


    # =========================================================
    # SLICE
    #
    # DIFFERENCE BEVEL
    # +
    # INTERSECT BEVEL
    # =========================================================

    slice_join = nodes.new(
        "GeometryNodeJoinGeometry"
    )

    slice_join.name = "Slice Join"
    slice_join.label = "Slice"

    slice_join.location = (
        100,
        -100
    )


    link(
        links,
        get_output(
            bevel_difference,
            "Mesh"
        ),
        get_input(
            slice_join,
            "Geometry"
        )
    )

    link(
        links,
        get_output(
            bevel_intersect,
            "Mesh"
        ),
        get_input(
            slice_join,
            "Geometry"
        )
    )


    # =========================================================
    # =========================================================
    # DEBOSS
    # =========================================================
    # =========================================================
    #
    # CONFIGURACION RECTIFICADA:
    # Offset 1 -> Multiply -1 -> Extrude Geometry = A
    # Geometry + Object/Collection Switch -> Difference = B
    # A + B -> Union = Deboss
    #
    # Los Boolean usan EXACT.
    # Union e Intersect (cuando corresponde) usan inputs[1]
    # como socket multi-input en Blender 5.3.
    # =========================================================

    # ---------------------------------------------------------
    # OFFSET 1 × -1
    # ---------------------------------------------------------
    deboss_offset_math = nodes.new("ShaderNodeMath")
    deboss_offset_math.name = "Deboss Offset Negative"
    deboss_offset_math.label = "Offset 1 × -1"
    deboss_offset_math.location = (-1100, -1000)
    deboss_offset_math.operation = 'MULTIPLY'
    deboss_offset_math.inputs[1].default_value = -1.0
    link(
        links,
        get_output(group_input, "Offset 1"),
        deboss_offset_math.inputs[0]
    )

    # ---------------------------------------------------------
    # DEBOSS — A
    # GEOMETRY -> EXTRUDE MESH
    # ---------------------------------------------------------
    deboss_extrude_a = nodes.new("GeometryNodeExtrudeMesh")
    deboss_extrude_a.name = "Deboss Extrude A"
    deboss_extrude_a.label = "Deboss: A"
    deboss_extrude_a.location = (-800, -1000)
    deboss_extrude_a.mode = 'FACES'
    individual_socket = get_input(deboss_extrude_a, "Individual")
    if individual_socket is not None:
        individual_socket.default_value = False
    link(
        links,
        geometry_output,
        get_input(deboss_extrude_a, "Mesh")
    )
    link(
        links,
        get_output(deboss_offset_math, "Value"),
        get_input(deboss_extrude_a, "Offset Scale")
    )

    # ---------------------------------------------------------
    # DEBOSS — B
    # GEOMETRY - OBJECT/COLLECTION SWITCH
    # ---------------------------------------------------------
    deboss_difference_b = nodes.new("GeometryNodeMeshBoolean")
    deboss_difference_b.name = "Deboss Difference B"
    deboss_difference_b.label = "Deboss: B"
    deboss_difference_b.location = (-450, -850)
    deboss_difference_b.operation = 'DIFFERENCE'
    deboss_difference_b.solver = 'EXACT'
    link(
        links,
        geometry_output,
        deboss_difference_b.inputs[0]
    )
    link(
        links,
        secondary_geometry,
        deboss_difference_b.inputs[1]
    )

    # ---------------------------------------------------------
    # DEBOSS — FINAL
    # A UNION B
    # ---------------------------------------------------------
    deboss_union = nodes.new("GeometryNodeMeshBoolean")
    deboss_union.name = "Deboss Union"
    deboss_union.label = "Deboss"
    deboss_union.location = (-50, -900)
    deboss_union.operation = 'UNION'
    deboss_union.solver = 'EXACT'
    link(
        links,
        get_output(deboss_extrude_a, "Mesh"),
        deboss_union.inputs[1]
    )
    link(
        links,
        get_output(deboss_difference_b, "Mesh"),
        deboss_union.inputs[1]
    )

    # =========================================================
    # =========================================================
    # EMBOSS
    # =========================================================
    # =========================================================
    #
    # REFERENCIA EXACTA:
    #
    # Geometry -> Extrude Mesh = B
    # Offset 1 -> Offset Scale
    # B + Object/Collection Switch -> Intersect
    # Intersect + Geometry original -> Union
    #
    # INTERSECT y UNION usan el socket 1 multi-input en Blender 5.3.
    # =========================================================


    # ---------------------------------------------------------
    # EMBOSS EXTRUDE B
    #
    # GEOMETRY + OFFSET 1
    # ---------------------------------------------------------

    emboss_extrude = nodes.new(
        "GeometryNodeExtrudeMesh"
    )

    emboss_extrude.name = "Emboss Extrude B"
    emboss_extrude.label = ""
    emboss_extrude.location = (
        -450,
        -1400
    )

    emboss_extrude.mode = 'FACES'

    individual_socket = get_input(
        emboss_extrude,
        "Individual"
    )

    if individual_socket is not None:
        individual_socket.default_value = False

    link(
        links,
        geometry_output,
        get_input(
            emboss_extrude,
            "Mesh"
        )
    )

    link(
        links,
        get_output(
            group_input,
            "Offset 1"
        ),
        get_input(
            emboss_extrude,
            "Offset Scale"
        )
    )


    # ---------------------------------------------------------
    # EMBOSS INTERSECT
    #
    # B ∩ OBJECT/COLLECTION SWITCH
    # ---------------------------------------------------------

    emboss_intersect = nodes.new(
        "GeometryNodeMeshBoolean"
    )

    emboss_intersect.name = "Emboss Intersect"
    emboss_intersect.label = ""
    emboss_intersect.location = (
        -100,
        -1400
    )

    emboss_intersect.operation = 'INTERSECT'
    emboss_intersect.solver = 'EXACT'

    link(
        links,
        get_output(
            emboss_extrude,
            "Mesh"
        ),
        emboss_intersect.inputs[1]
    )

    link(
        links,
        secondary_geometry,
        emboss_intersect.inputs[1]
    )


    # ---------------------------------------------------------
    # EMBOSS UNION
    #
    # INTERSECT + ORIGINAL GEOMETRY
    # ---------------------------------------------------------

    emboss_union = nodes.new(
        "GeometryNodeMeshBoolean"
    )

    emboss_union.name = "Emboss Union"
    emboss_union.label = ""
    emboss_union.location = (
        250,
        -1400
    )

    emboss_union.operation = 'UNION'
    emboss_union.solver = 'EXACT'

    link(
        links,
        get_output(
            emboss_intersect,
            "Mesh"
        ),
        emboss_union.inputs[1]
    )

    link(
        links,
        geometry_output,
        emboss_union.inputs[1]
    )


    # =========================================================
    # =========================================================
    # OUTLINE D / OUTLINE E — V2 SIN BEVEL
    # =========================================================
    #
    # Reconstructed from the corrected individual screenshots.
    # No bevels are added to these two branches yet.
    #
    # Outline D = Outline -
    # Outline E = Outline +
    #
    # =========================================================
    # OUTLINE D  (Outline -) — RECTIFIED
    # =========================================================
    # Offset 1 is inverted with Multiply -1.
    # A = Geometry extruded with negative offset.
    # B = Secondary (Object/Collection Switch) extruded with negative offset.
    # C = Geometry INTERSECT Secondary.
    # D = Geometry DIFFERENCE Secondary.
    # E = B INTERSECT C.
    # F = D UNION E.
    # Final = A UNION F.
    # =========================================================

    # ---------------------------------------------------------
    # OUTLINE D — OFFSET 1 × -1
    # ---------------------------------------------------------
    outline_d_offset_neg = nodes.new("ShaderNodeMath")
    outline_d_offset_neg.name = "Outline D Offset Negative"
    outline_d_offset_neg.label = "Outline D: Offset 1 × -1"
    outline_d_offset_neg.location = (-1200, -1750)
    outline_d_offset_neg.operation = 'MULTIPLY'
    outline_d_offset_neg.inputs[1].default_value = -1.0
    link(
        links,
        get_output(group_input, "Offset 1"),
        outline_d_offset_neg.inputs[0]
    )

    # ---------------------------------------------------------
    # OUTLINE D — A
    # GEOMETRY → EXTRUDE (NEGATIVE OFFSET)
    # ---------------------------------------------------------
    outline_d_extrude_a = nodes.new("GeometryNodeExtrudeMesh")
    outline_d_extrude_a.name = "Outline D Extrude A"
    outline_d_extrude_a.label = "Outline D: A"
    outline_d_extrude_a.location = (-850, -1650)
    outline_d_extrude_a.mode = 'FACES'
    individual = get_input(outline_d_extrude_a, "Individual")
    if individual is not None:
        individual.default_value = False
    link(
        links,
        geometry_output,
        get_input(outline_d_extrude_a, "Mesh")
    )
    link(
        links,
        get_output(outline_d_offset_neg, "Value"),
        get_input(outline_d_extrude_a, "Offset Scale")
    )

    # ---------------------------------------------------------
    # OUTLINE D — OFFSET 1 × -1 (SECONDARY EXTRUDE)
    # Separate math output for this Extrude.
    # ---------------------------------------------------------
    outline_d_offset_neg_b = nodes.new("ShaderNodeMath")
    outline_d_offset_neg_b.name = "Outline D Offset Negative B"
    outline_d_offset_neg_b.label = "Outline D: Offset 1 × -1 (B)"
    outline_d_offset_neg_b.location = (-1200, -2050)
    outline_d_offset_neg_b.operation = 'MULTIPLY'
    outline_d_offset_neg_b.inputs[1].default_value = -1.0
    link(
        links,
        get_output(group_input, "Offset 2"),
        outline_d_offset_neg_b.inputs[0]
    )

    # ---------------------------------------------------------
    # OUTLINE D — B
    # SWITCH (OBJECT/COLLECTION) → EXTRUDE (NEGATIVE OFFSET)
    # ---------------------------------------------------------
    outline_d_extrude_b = nodes.new("GeometryNodeExtrudeMesh")
    outline_d_extrude_b.name = "Outline D Extrude B"
    outline_d_extrude_b.label = "Outline D: B"
    outline_d_extrude_b.location = (-850, -1950)
    outline_d_extrude_b.mode = 'FACES'
    individual = get_input(outline_d_extrude_b, "Individual")
    if individual is not None:
        individual.default_value = False
    link(
        links,
        secondary_geometry,
        get_input(outline_d_extrude_b, "Mesh")
    )
    link(
        links,
        get_output(outline_d_offset_neg_b, "Value"),
        get_input(outline_d_extrude_b, "Offset Scale")
    )

    # ---------------------------------------------------------
    # OUTLINE D — C
    # GEOMETRY ∩ SWITCH
    # ---------------------------------------------------------
    outline_d_intersect_c = nodes.new("GeometryNodeMeshBoolean")
    outline_d_intersect_c.name = "Outline D Intersect C"
    outline_d_intersect_c.label = "Outline D: C"
    outline_d_intersect_c.location = (-450, -1550)
    outline_d_intersect_c.operation = 'INTERSECT'
    outline_d_intersect_c.solver = 'EXACT'
    link(
        links,
        geometry_output,
        outline_d_intersect_c.inputs[1]
    )
    link(
        links,
        secondary_geometry,
        outline_d_intersect_c.inputs[1]
    )

    # ---------------------------------------------------------
    # OUTLINE D — D
    # GEOMETRY - SWITCH
    # ---------------------------------------------------------
    outline_d_difference_d = nodes.new("GeometryNodeMeshBoolean")
    outline_d_difference_d.name = "Outline D Difference D"
    outline_d_difference_d.label = "Outline D: D"
    outline_d_difference_d.location = (-450, -1300)
    outline_d_difference_d.operation = 'DIFFERENCE'
    outline_d_difference_d.solver = 'EXACT'
    link(
        links,
        geometry_output,
        outline_d_difference_d.inputs[0]
    )
    link(
        links,
        secondary_geometry,
        outline_d_difference_d.inputs[1]
    )

    # ---------------------------------------------------------
    # OUTLINE D — E
    # B ∩ C
    # ---------------------------------------------------------
    outline_d_intersect_e = nodes.new("GeometryNodeMeshBoolean")
    outline_d_intersect_e.name = "Outline D Intersect E"
    outline_d_intersect_e.label = "Outline D: E"
    outline_d_intersect_e.location = (-50, -1650)
    outline_d_intersect_e.operation = 'INTERSECT'
    outline_d_intersect_e.solver = 'EXACT'
    link(
        links,
        get_output(outline_d_extrude_b, "Mesh"),
        outline_d_intersect_e.inputs[1]
    )
    link(
        links,
        get_output(outline_d_intersect_c, "Mesh"),
        outline_d_intersect_e.inputs[1]
    )

    # ---------------------------------------------------------
    # OUTLINE D — F
    # D ∪ E
    # ---------------------------------------------------------
    outline_d_union_f = nodes.new("GeometryNodeMeshBoolean")
    outline_d_union_f.name = "Outline D Union F"
    outline_d_union_f.label = "Outline D: F"
    outline_d_union_f.location = (250, -1400)
    outline_d_union_f.operation = 'UNION'
    outline_d_union_f.solver = 'EXACT'
    link(
        links,
        get_output(outline_d_difference_d, "Mesh"),
        outline_d_union_f.inputs[1]
    )
    link(
        links,
        get_output(outline_d_intersect_e, "Mesh"),
        outline_d_union_f.inputs[1]
    )

    # ---------------------------------------------------------
    # OUTLINE D — FINAL
    # A ∪ F
    # ---------------------------------------------------------
    outline_d_final = nodes.new("GeometryNodeMeshBoolean")
    outline_d_final.name = "Outline D Final"
    outline_d_final.label = "Outline D: Outline -"
    outline_d_final.location = (550, -1400)
    outline_d_final.operation = 'UNION'
    outline_d_final.solver = 'EXACT'
    link(
        links,
        get_output(outline_d_extrude_a, "Mesh"),
        outline_d_final.inputs[1]
    )
    link(
        links,
        get_output(outline_d_union_f, "Mesh"),
        outline_d_final.inputs[1]
    )

    outline_d_output = get_output(outline_d_final, "Mesh")


    # =========================================================
    # OUTLINE E  (Outline +) — RECTIFIED
    # =========================================================
    # A = SWITCH extruded with Offset 1 × -1
    # B = GEOMETRY extruded with Offset 1
    # C = SWITCH INTERSECT B
    # D = C DIFFERENCE A
    # Final = GEOMETRY UNION D
    # =========================================================

    # ---------------------------------------------------------
    # OUTLINE E — OFFSET 1 × -1 FOR A
    # ---------------------------------------------------------
    outline_e_offset_neg = nodes.new("ShaderNodeMath")
    outline_e_offset_neg.name = "Outline E Offset Negative"
    outline_e_offset_neg.label = "Outline E: Offset 1 × -1"
    outline_e_offset_neg.location = (-1100, -2250)
    outline_e_offset_neg.operation = 'MULTIPLY'
    outline_e_offset_neg.inputs[1].default_value = -1.0
    link(
        links,
        get_output(group_input, "Offset 1"),
        outline_e_offset_neg.inputs[0]
    )

    # ---------------------------------------------------------
    # OUTLINE E — A
    # SWITCH (OBJECT/COLLECTION) → EXTRUDE (NEGATIVE OFFSET)
    # ---------------------------------------------------------
    outline_e_extrude_a = nodes.new("GeometryNodeExtrudeMesh")
    outline_e_extrude_a.name = "Outline E Extrude A"
    outline_e_extrude_a.label = "Outline E: A"
    outline_e_extrude_a.location = (-750, -2250)
    outline_e_extrude_a.mode = 'FACES'
    individual = get_input(outline_e_extrude_a, "Individual")
    if individual is not None:
        individual.default_value = False
    link(
        links,
        secondary_geometry,
        get_input(outline_e_extrude_a, "Mesh")
    )
    link(
        links,
        get_output(outline_e_offset_neg, "Value"),
        get_input(outline_e_extrude_a, "Offset Scale")
    )

    # ---------------------------------------------------------
    # OUTLINE E — B
    # GEOMETRY → EXTRUDE (POSITIVE OFFSET 1)
    # ---------------------------------------------------------
    outline_e_extrude_b = nodes.new("GeometryNodeExtrudeMesh")
    outline_e_extrude_b.name = "Outline E Extrude B"
    outline_e_extrude_b.label = "Outline E: B"
    outline_e_extrude_b.location = (-750, -2500)
    outline_e_extrude_b.mode = 'FACES'
    individual = get_input(outline_e_extrude_b, "Individual")
    if individual is not None:
        individual.default_value = False
    link(
        links,
        geometry_output,
        get_input(outline_e_extrude_b, "Mesh")
    )
    link(
        links,
        get_output(group_input, "Offset 2"),
        get_input(outline_e_extrude_b, "Offset Scale")
    )

    # ---------------------------------------------------------
    # OUTLINE E — C
    # SWITCH ∩ B
    # ---------------------------------------------------------
    outline_e_intersect_c = nodes.new("GeometryNodeMeshBoolean")
    outline_e_intersect_c.name = "Outline E Intersect C"
    outline_e_intersect_c.label = "Outline E: C"
    outline_e_intersect_c.location = (-350, -2300)
    outline_e_intersect_c.operation = 'INTERSECT'
    outline_e_intersect_c.solver = 'EXACT'
    link(
        links,
        secondary_geometry,
        outline_e_intersect_c.inputs[1]
    )
    link(
        links,
        get_output(outline_e_extrude_b, "Mesh"),
        outline_e_intersect_c.inputs[1]
    )

    # ---------------------------------------------------------
    # OUTLINE E — D
    # C - A
    # ---------------------------------------------------------
    outline_e_difference_d = nodes.new("GeometryNodeMeshBoolean")
    outline_e_difference_d.name = "Outline E Difference D"
    outline_e_difference_d.label = "Outline E: D"
    outline_e_difference_d.location = (20, -2200)
    outline_e_difference_d.operation = 'DIFFERENCE'
    outline_e_difference_d.solver = 'EXACT'
    link(
        links,
        get_output(outline_e_intersect_c, "Mesh"),
        outline_e_difference_d.inputs[0]
    )
    link(
        links,
        get_output(outline_e_extrude_a, "Mesh"),
        outline_e_difference_d.inputs[1]
    )

    # ---------------------------------------------------------
    # OUTLINE E — FINAL
    # GEOMETRY + D
    # ---------------------------------------------------------
    outline_e_final = nodes.new("GeometryNodeMeshBoolean")
    outline_e_final.name = "Outline E Final"
    outline_e_final.label = "Outline E: Outline +"
    outline_e_final.location = (350, -2200)
    outline_e_final.operation = 'UNION'
    outline_e_final.solver = 'EXACT'
    link(
        links,
        geometry_output,
        outline_e_final.inputs[1]
    )
    link(
        links,
        get_output(outline_e_difference_d, "Mesh"),
        outline_e_final.inputs[1]
    )

    outline_e_output = get_output(outline_e_final, "Mesh")


    # =========================================================
    # BEVEL DEBOSS / EMBOSS / OUTLINES
    # =========================================================
    # Bevel geometry is unchanged.  Only the Selection field is
    # controlled by reusable Boolean-selection Menu Switches.
    # =========================================================

    def setup_bevel_base(name, label, location, mesh_socket):
        bevel = nodes.new("GeometryNodeMeshBevel")
        bevel.name = name
        bevel.label = label
        bevel.location = location
        link(links, mesh_socket, get_input(bevel, "Mesh"))

        offset_output = get_output(group_input, "Bevel")
        for socket_name in (
            "Start Left Offset", "Start Right Offset",
            "End Left Offset", "End Right Offset",
        ):
            link(links, offset_output, get_input(bevel, socket_name))

        link(links, get_output(group_input, "Segments"), get_input(bevel, "Segments"))
        shape_input = get_input(bevel, "Shape") or get_input(bevel, "Profile")
        if shape_input is not None:
            link(links, get_output(group_input, "Shape"), shape_input)
        return bevel


    def get_or_create_selection_switch_group():
        group_name = "Boolean Advanced Bevel Selection Switch"
        ng = bpy.data.node_groups.get(group_name)
        if ng is None:
            ng = bpy.data.node_groups.new(group_name, 'GeometryNodeTree')
            gi = ng.nodes.new("NodeGroupInput")
            go = ng.nodes.new("NodeGroupOutput")
            gi.location = (-500, 0)
            go.location = (500, 0)

            ng.interface.new_socket(name="Menu", in_out='INPUT', socket_type='NodeSocketMenu')
            for n in ("A", "B", "C"):
                ng.interface.new_socket(name=n, in_out='INPUT', socket_type='NodeSocketBool')
            ng.interface.new_socket(name="Output", in_out='OUTPUT', socket_type='NodeSocketBool')

            menu = ng.nodes.new("GeometryNodeMenuSwitch")
            menu.name = "Reusable Bevel Selection Menu"
            menu.data_type = 'BOOLEAN'
            menu.location = (0, 0)
            menu.enum_items.clear()
            for n in ("A", "B", "C"):
                menu.enum_items.new(n)

            for n in ("A", "B", "C"):
                if gi.outputs.get(n) and menu.inputs.get(n):
                    ng.links.new(gi.outputs[n], menu.inputs[n])
            if gi.outputs.get("Menu") and menu.inputs.get("Menu"):
                ng.links.new(gi.outputs["Menu"], menu.inputs["Menu"])
            if menu.outputs.get("Output") and go.inputs.get("Output"):
                ng.links.new(menu.outputs["Output"], go.inputs["Output"])
        return ng

    selection_group = get_or_create_selection_switch_group()


    def add_bool_fields(name, location, a_socket, b_socket):
        add = nodes.new("ShaderNodeMath")
        add.name = name
        add.label = name
        add.operation = 'ADD'
        add.location = location
        link(links, a_socket, add.inputs[0])
        link(links, b_socket, add.inputs[1])
        return add


    def selection_switch(name, location, a_socket, b_socket, c_socket):
        sw = nodes.new("GeometryNodeGroup")
        sw.name = name
        sw.label = "Bevel Selection"
        sw.node_tree = selection_group
        sw.location = location
        # Bevel Selection has its own Group Input menu.
        # It is intentionally separate from the final Boolean menu.
        link(links, get_output(group_input, "Bevel Selection"), get_input(sw, "Menu"))
        link(links, a_socket, get_input(sw, "A"))
        link(links, b_socket, get_input(sw, "B"))
        link(links, c_socket, get_input(sw, "C"))
        return sw

    # ---------------------------------------------------------
    # DEBOSS
    # Image pattern: first Boolean edge field, mathematical
    # combination, final Boolean edge field.
    # ---------------------------------------------------------
    deboss_sel_add = add_bool_fields(
        "Deboss Selection Add", (40, -760),
        get_output(deboss_difference_b, "Intersecting Edges"),
        get_output(deboss_union, "Intersecting Edges")
    )
    deboss_sel = selection_switch(
        "Deboss Bevel Selection Switch", (360, -760),
        get_output(deboss_difference_b, "Intersecting Edges"),
        get_output(deboss_sel_add, "Value"),
        get_output(deboss_union, "Intersecting Edges")
    )
    bevel_deboss = setup_bevel_base(
        "Bevel Deboss", "Bevel Deboss", (650, -1000),
        get_output(deboss_union, "Mesh")
    )
    link(links, get_output(deboss_sel, "Output"), get_input(bevel_deboss, "Selection"))

    # ---------------------------------------------------------
    # EMBOSS
    # ---------------------------------------------------------
    emboss_sel_add = add_bool_fields(
        "Emboss Selection Add", (40, -1320),
        get_output(emboss_intersect, "Intersecting Edges"),
        get_output(emboss_union, "Intersecting Edges")
    )
    emboss_sel = selection_switch(
        "Emboss Bevel Selection Switch", (360, -1320),
        get_output(emboss_intersect, "Intersecting Edges"),
        get_output(emboss_sel_add, "Value"),
        get_output(emboss_union, "Intersecting Edges")
    )
    bevel_emboss = setup_bevel_base(
        "Bevel Emboss", "Bevel Emboss", (650, -1400),
        get_output(emboss_union, "Mesh")
    )
    link(links, get_output(emboss_sel, "Output"), get_input(bevel_emboss, "Selection"))

    # ---------------------------------------------------------
    # OUTLINE D / OUTLINE -
    # Two mathematical combinations visible in the reference,
    # followed by the final Boolean edge field.
    # ---------------------------------------------------------
    # A original + B original -> nuevo A
    od_add_1 = add_bool_fields(
        "Outline D Selection Add 1", (300, -1760),
        get_output(outline_d_intersect_c, "Intersecting Edges"),
        get_output(outline_d_difference_d, "Intersecting Edges")
    )
    od_add_2 = add_bool_fields(
        "Outline D Selection Add 2", (300, -1900),
        get_output(outline_d_intersect_e, "Intersecting Edges"),
        get_output(outline_d_union_f, "Intersecting Edges")
    )
    od_add_3 = add_bool_fields(
        "Outline D Selection Add 3", (500, -1760),
        get_output(od_add_1, "Value"),
        get_output(od_add_2, "Value")
    )
    # nuevo A + C original -> nuevo B
    od_add_4 = add_bool_fields(
        "Outline D Selection Add 4", (500, -1900),
        get_output(od_add_3, "Value"),
        get_output(outline_d_final, "Intersecting Edges")
    )
    od_sel = selection_switch(
        "Outline D Bevel Selection Switch", (650, -1760),
        get_output(od_add_3, "Value"),
        get_output(od_add_4, "Value"),
        get_output(outline_d_final, "Intersecting Edges")
    )
    bevel_outline_d = setup_bevel_base(
        "Bevel Outline D", "Bevel Outline -", (950, -1800),
        get_output(outline_d_final, "Mesh")
    )
    link(links, get_output(od_sel, "Output"), get_input(bevel_outline_d, "Selection"))

    # ---------------------------------------------------------
    # OUTLINE E / OUTLINE +
    # ---------------------------------------------------------
    # A = A original (C + D)
    # B = A + C
    # C = C original (final Union)
    # A and C remain unchanged; only the math feeding B is changed.
    oe_add = add_bool_fields(
        "Outline E Selection Add", (300, -2140),
        get_output(outline_e_intersect_c, "Intersecting Edges"),
        get_output(outline_e_difference_d, "Intersecting Edges")
    )
    oe_add_b = add_bool_fields(
        "Outline E Selection Add B", (480, -2040),
        get_output(oe_add, "Value"),
        get_output(outline_e_final, "Intersecting Edges")
    )
    oe_sel = selection_switch(
        "Outline E Bevel Selection Switch", (650, -2140),
        get_output(oe_add, "Value"),
        get_output(oe_add_b, "Value"),
        get_output(outline_e_final, "Intersecting Edges")
    )
    bevel_outline_e = setup_bevel_base(
        "Bevel Outline E", "Bevel Outline +", (950, -2200),
        get_output(outline_e_final, "Mesh")
    )
    link(links, get_output(oe_sel, "Output"), get_input(bevel_outline_e, "Selection"))


    # MENU SWITCH
    # =========================================================
    # FINAL GEOMETRY MENU SWITCH
    # This menu is used only once, so it remains a direct
    # GeometryNodeMenuSwitch in the main node tree.
    # Only the bevel Selection Menu Switches are wrapped in
    # a dedicated reusable node group.
    # =========================================================

    menu_switch = nodes.new("GeometryNodeMenuSwitch")
    menu_switch.name = "Boolean Menu Switch"
    menu_switch.label = "Boolean"
    menu_switch.data_type = 'GEOMETRY'
    menu_switch.location = (1100, 100)

    menu_switch.enum_items.clear()
    for item_name in (
        "Difference",
        "Union",
        "Intersect",
        "Slice",
        "Deboss",
        "Emboss",
        "Outline D",
        "Outline E",
    ):
        menu_switch.enum_items.new(item_name)

    # Menu selector
    link(
        links,
        get_output(group_input, "Boolean"),
        get_input(menu_switch, "Menu")
    )

    # Geometry choices
    link(links, get_output(bevel_difference, "Mesh"), get_input(menu_switch, "Difference"))
    link(links, get_output(bevel_union, "Mesh"), get_input(menu_switch, "Union"))
    link(links, get_output(bevel_intersect, "Mesh"), get_input(menu_switch, "Intersect"))
    link(links, get_output(slice_join, "Geometry"), get_input(menu_switch, "Slice"))
    link(links, get_output(bevel_deboss, "Mesh"), get_input(menu_switch, "Deboss"))
    link(links, get_output(bevel_emboss, "Mesh"), get_input(menu_switch, "Emboss"))
    link(links, get_output(bevel_outline_d, "Mesh"), get_input(menu_switch, "Outline D"))
    link(links, get_output(bevel_outline_e, "Mesh"), get_input(menu_switch, "Outline E"))

    # MENU → OUTPUT
    link(
        links,
        get_output(menu_switch, "Output"),
        get_input(group_output, "Geometry")
    )



    # Select the main nodes for a clean node-editor result.

    # =========================================================

    for node in nodes:

        node.select = False


    group_input.select = True
    group_output.select = True

    nodes.active = group_input



    modifier = obj.modifiers.new(name=GROUP_NAME, type='NODES')
    modifier.node_group = ng
    return modifier

class VIEW3D_OT_add_simple_modifier(
    bpy.types.Operator
):

    bl_idname = "view3d.add_simple_modifier"
    bl_label = "Add Modifier"

    modifier_type: bpy.props.StringProperty()

    @staticmethod
    def modifier_name(modifier_type):

        names = {

            'MIRROR':
                "Mirror",

            'SUBSURF':
                "Subdivision",

            'MULTIRES':
                "Multiresolution",

            'REMESH':
                "Remesh",

            'DECIMATE':
                "Decimate",

            'BOOLEAN':
                "Boolean",

            'BEVEL':
                "Bevel",

            'SOLIDIFY':
                "Solidify",

            'ARRAY':
                "Array",

            'ARRAY_MODERN':
                "Array +",

            'BOOLEAN_PLUS':
                "Boolean +",

            'CURVE':
                "Curve Deform",

            'DATA_TRANSFER':
                "Data Transfer",

            'HOOK':
                "Hook",

            'SCREW':
                "Screw",

            'SIMPLE_DEFORM':
                "Simple Deform",

            'LATTICE':
                "Lattice",

            'ARMATURE':
                "Armature",

            'SHRINKWRAP':
                "Shrinkwrap",

            'SKIN':
                "Skin",

            'DISPLACE':
                "Displace",

            'NODES':
                "Geometry Nodes",

            'CAST':
                "Cast",

            'CORRECTIVE_SMOOTH':
                "Corrective Smooth",

            'SCATTER_ON_SURFACE':
                "Scatter",
            'BUILD':
                "Build",

            'CLOTH':
                "Cloth",

            'COLLISION':
                "Collision",

            'EXPLODE':
                "Explode",

            'FLUID':
                "Fluid",

            'LAPLACIANDEFORM':
                "Laplacian Deform",

            'LAPLACIANSMOOTH':
                "Laplacian Smooth",

            'MASK':
                "Mask",

            'MESH_CACHE':
                "Mesh Cache",

            'MESH_DEFORM':
                "Mesh Deform",

            'MESH_SEQUENCE_CACHE':
                "Mesh Sequence Cache",

            'NORMAL_EDIT':
                "Normal Edit",

            'PARTICLE_INSTANCE':
                "Particle Instance",

            'PARTICLE_SYSTEM':
                "Particle System",

            'SMOOTH':
                "Smooth",

            'SURFACE_DEFORM':
                "Surface Deform",
            'SOFT_BODY':
                "Soft Body",


            'TRIANGULATE':
                "Triangulate",

            'UV_WARP':
                "UV Warp",

            'VERTEX_WEIGHT_EDIT':
                "Vertex Weight Edit",

            'VERTEX_WEIGHT_MIX':
                "Vertex Weight Mix",

            'VERTEX_WEIGHT_PROXIMITY':
                "Vertex Weight Proximity",

            'WARP':
                "Warp",

            'WAVE':
                "Wave",

            'WELD':
                "Weld",

            'WIREFRAME':
                "Wireframe",

            'WEIGHTED_NORMAL':
                "Weighted Normal",

        }

        return names.get(
            modifier_type,
            modifier_type.title()
        )

    def execute(self, context):

        obj = get_active_object(context)

        if obj is None:

            self.report(
                {'ERROR'},
                "Select a mesh or curve"
            )

            return {'CANCELLED'}

        state = enter_object_mode(context)

        if state is None:

            self.report(
                {'ERROR'},
                "Could not enter Object Mode"
            )

            return {'CANCELLED'}

        try:

            # ---------------------------------------------
            # ARRAY LEGACY / NORMAL
            # ---------------------------------------------

            if self.modifier_type == 'ARRAY':

                modifier = obj.modifiers.new(
                    name="Array",
                    type='ARRAY'
                )

            # ---------------------------------------------
            # ARRAY MODERNO / ADVANCED
            # ---------------------------------------------

            elif self.modifier_type == 'ARRAY_MODERN':

                modifier = add_modern_array(
                    context,
                    obj
                )

            # ---------------------------------------------
            # SCATTER ON SURFACE
            # ---------------------------------------------

            elif self.modifier_type == 'SCATTER_ON_SURFACE':

                modifier = add_scatter_on_surface(
                    context,
                    obj
                )

            # ---------------------------------------------
            # BOOLEAN + (Advanced Geometry Nodes)
            # ---------------------------------------------

            elif self.modifier_type == 'BOOLEAN_PLUS':

                modifier = build_boolean_plus(
                    context,
                    obj
                )

            # ---------------------------------------------
            # MORE / CAST
            # ---------------------------------------------

            elif self.modifier_type == 'CAST':

                modifier = obj.modifiers.new(
                    name="Cast",
                    type='CAST'
                )

            # ---------------------------------------------
            # MORE / CORRECTIVE SMOOTH
            # ---------------------------------------------

            elif self.modifier_type == 'CORRECTIVE_SMOOTH':

                modifier = obj.modifiers.new(
                    name="Corrective Smooth",
                    type='CORRECTIVE_SMOOTH'
                )

            # ---------------------------------------------
            # MULTIRES
            # ---------------------------------------------

            elif self.modifier_type == 'MULTIRES':

                modifier = obj.modifiers.new(
                    name="Multiresolution",
                    type='MULTIRES'
                )

            # ---------------------------------------------
            # NORMAL
            # ---------------------------------------------

            else:

                if self.modifier_type not in REAL_MODIFIERS:

                    raise RuntimeError(
                        f"Unsupported modifier: "
                        f"{self.modifier_type}"
                    )

                modifier = obj.modifiers.new(
                    name=self.modifier_name(
                        self.modifier_type
                    ),
                    type=self.modifier_type
                )

            context.scene.simple_modifier_index = (
                len(obj.modifiers) - 1
            )

        except Exception as error:

            restore_context(
                context,
                state
            )

            self.report(
                {'ERROR'},
                f"Could not add modifier: {error}"
            )

            return {'CANCELLED'}

        restore_context(
            context,
            state
        )

        return {'FINISHED'}

class VIEW3D_OT_select_modifier(
    bpy.types.Operator
):

    bl_idname = "view3d.select_simple_modifier"
    bl_label = "Select Modifier"

    index: bpy.props.IntProperty()

    def execute(self, context):

        context.scene.simple_modifier_index = (
            self.index
        )

        return {'FINISHED'}

class VIEW3D_OT_remove_simple_modifier(
    bpy.types.Operator
):

    bl_idname = "view3d.remove_simple_modifier"
    bl_label = "Delete Modifier"

    index: bpy.props.IntProperty()

    def execute(self, context):

        obj = get_active_object(context)

        if obj is None:
            return {'CANCELLED'}

        modifier = get_modifier(
            obj,
            self.index
        )

        if modifier is None:
            return {'CANCELLED'}

        state = enter_object_mode(context)

        if state is None:
            return {'CANCELLED'}

        try:

            obj.modifiers.remove(
                modifier
            )

        except Exception as error:

            restore_context(
                context,
                state
            )

            self.report(
                {'ERROR'},
                f"Could not remove modifier: {error}"
            )

            return {'CANCELLED'}

        if obj.modifiers:

            context.scene.simple_modifier_index = min(
                self.index,
                len(obj.modifiers) - 1
            )

        else:

            context.scene.simple_modifier_index = 0

        restore_context(
            context,
            state
        )

        return {'FINISHED'}

class VIEW3D_OT_apply_simple_modifier(
    bpy.types.Operator
):

    bl_idname = "view3d.apply_simple_modifier"
    bl_label = "Apply Modifier"

    index: bpy.props.IntProperty()

    def execute(self, context):

        obj = get_active_object(context)

        if obj is None:
            return {'CANCELLED'}

        modifier = get_modifier(
            obj,
            self.index
        )

        if modifier is None:
            return {'CANCELLED'}

        state = enter_object_mode(context)

        if state is None:

            self.report(
                {'ERROR'},
                "Could not enter Object Mode"
            )

            return {'CANCELLED'}

        try:

            set_active_only(
                context,
                obj
            )

            bpy.ops.object.modifier_apply(
                modifier=modifier.name
            )

        except Exception as error:

            restore_context(
                context,
                state
            )

            self.report(
                {'ERROR'},
                f"Could not apply modifier: {error}"
            )

            return {'CANCELLED'}

        if obj.modifiers:

            context.scene.simple_modifier_index = min(
                self.index,
                len(obj.modifiers) - 1
            )

        else:

            context.scene.simple_modifier_index = 0

        restore_context(
            context,
            state
        )

        return {'FINISHED'}

class VIEW3D_OT_move_modifier_up(
    bpy.types.Operator
):

    bl_idname = "view3d.move_modifier_up"
    bl_label = "Move Modifier Up"

    index: bpy.props.IntProperty()

    def execute(self, context):

        obj = get_active_object(context)

        if obj is None:
            return {'CANCELLED'}

        modifier = get_modifier(
            obj,
            self.index
        )

        if modifier is None or self.index <= 0:
            return {'CANCELLED'}

        state = enter_object_mode(context)

        if state is None:
            return {'CANCELLED'}

        try:

            set_active_only(
                context,
                obj
            )

            bpy.ops.object.modifier_move_up(
                modifier=modifier.name
            )

        except Exception as error:

            restore_context(
                context,
                state
            )

            self.report(
                {'ERROR'},
                f"Could not move modifier: {error}"
            )

            return {'CANCELLED'}

        context.scene.simple_modifier_index = (
            self.index - 1
        )

        restore_context(
            context,
            state
        )

        return {'FINISHED'}

class VIEW3D_OT_move_modifier_down(
    bpy.types.Operator
):

    bl_idname = "view3d.move_modifier_down"
    bl_label = "Move Modifier Down"

    index: bpy.props.IntProperty()

    def execute(self, context):

        obj = get_active_object(context)

        if obj is None:
            return {'CANCELLED'}

        modifier = get_modifier(
            obj,
            self.index
        )

        if (
            modifier is None or
            self.index >= len(obj.modifiers) - 1
        ):
            return {'CANCELLED'}

        state = enter_object_mode(context)

        if state is None:
            return {'CANCELLED'}

        try:

            set_active_only(
                context,
                obj
            )

            bpy.ops.object.modifier_move_down(
                modifier=modifier.name
            )

        except Exception as error:

            restore_context(
                context,
                state
            )

            self.report(
                {'ERROR'},
                f"Could not move modifier: {error}"
            )

            return {'CANCELLED'}

        context.scene.simple_modifier_index = (
            self.index + 1
        )

        restore_context(
            context,
            state
        )

        return {'FINISHED'}

class VIEW3D_OT_multires_subdivide(
    bpy.types.Operator
):

    bl_idname = "view3d.simple_multires_subdivide"
    bl_label = "Subdivide"

    subdivision_type: bpy.props.EnumProperty(
        items=[
            ('CATMULL_CLARK', "Catmull-Clark", ""),
            ('SIMPLE', "Simple", ""),
            ('LINEAR', "Linear", ""),
        ],
        default='CATMULL_CLARK'
    )

    def execute(self, context):

        obj = get_active_object(context)

        if obj is None:
            return {'CANCELLED'}

        modifier = None

        for mod in obj.modifiers:

            if mod.type == 'MULTIRES':
                modifier = mod
                break

        if modifier is None:
            return {'CANCELLED'}

        state = enter_object_mode(context)

        if state is None:
            return {'CANCELLED'}

        try:

            set_active_only(
                context,
                obj
            )

            bpy.ops.object.multires_subdivide(
                modifier=modifier.name,
                mode=self.subdivision_type
            )

        except Exception as error:

            restore_context(
                context,
                state
            )

            self.report(
                {'ERROR'},
                str(error)
            )

            return {'CANCELLED'}

        restore_context(
            context,
            state
        )

        return {'FINISHED'}

class VIEW3D_OT_multires_delete_higher(
    bpy.types.Operator
):

    bl_idname = "view3d.simple_multires_delete_higher"
    bl_label = "Delete Higher"

    def execute(self, context):

        obj = get_active_object(context)

        if obj is None:
            return {'CANCELLED'}

        state = enter_object_mode(context)

        if state is None:
            return {'CANCELLED'}

        try:

            set_active_only(
                context,
                obj
            )

            bpy.ops.object.multires_higher_levels_delete(
                modifier=next(
                    mod for mod in obj.modifiers
                    if mod.type == 'MULTIRES'
                ).name
            )

        except Exception as error:

            restore_context(
                context,
                state
            )

            self.report(
                {'ERROR'},
                str(error)
            )

            return {'CANCELLED'}

        restore_context(
            context,
            state
        )

        return {'FINISHED'}

class VIEW3D_OT_multires_unsubdivide(
    bpy.types.Operator
):

    bl_idname = "view3d.simple_multires_unsubdivide"
    bl_label = "Unsubdivide"

    def execute(self, context):

        obj = get_active_object(context)

        if obj is None:
            return {'CANCELLED'}

        state = enter_object_mode(context)

        if state is None:
            return {'CANCELLED'}

        try:

            set_active_only(
                context,
                obj
            )

            bpy.ops.object.multires_unsubdivide(
                modifier=next(
                    mod for mod in obj.modifiers
                    if mod.type == 'MULTIRES'
                ).name
            )

        except Exception as error:

            restore_context(
                context,
                state
            )

            self.report(
                {'ERROR'},
                str(error)
            )

            return {'CANCELLED'}

        restore_context(
            context,
            state
        )

        return {'FINISHED'}

class VIEW3D_OT_skin_create_armature(
    bpy.types.Operator
):

    bl_idname = "view3d.skin_create_armature"
    bl_label = "Create Armature"

    def execute(self, context):

        obj = get_active_object(context)

        if obj is None:
            return {'CANCELLED'}

        state = enter_object_mode(context)

        if state is None:
            return {'CANCELLED'}

        try:

            set_active_only(
                context,
                obj
            )

            bpy.ops.object.skin_armature_create(
                modifier="",
                view_layer="ViewLayer"
            )

        except Exception as error:

            restore_context(
                context,
                state
            )

            self.report(
                {'ERROR'},
                f"Could not create armature: {error}"
            )

            return {'CANCELLED'}

        restore_context(
            context,
            state
        )

        return {'FINISHED'}

class VIEW3D_OT_displace_new_texture(
    bpy.types.Operator
):

    bl_idname = "view3d.displace_new_texture"
    bl_label = "New Texture"

    def execute(self, context):

        obj = get_active_object(context)

        if obj is None:
            return {'CANCELLED'}

        modifier = get_modifier(
            obj,
            context.scene.simple_modifier_index
        )

        if modifier is None:
            return {'CANCELLED'}

        if modifier.type != 'DISPLACE':
            return {'CANCELLED'}

        texture = bpy.data.textures.new(
            name="Displace Texture",
            type='CLOUDS'
        )

        modifier.texture = texture

        return {'FINISHED'}

def modifier_icon(modifier):

    # -----------------------------------------------------
    # SCATTER ON SURFACE
    # -----------------------------------------------------

    if (
        modifier.type == 'NODES' and
        modifier.name == "Scatter"
    ):

        return 'NODETREE'

    # -----------------------------------------------------
    # ARRAY ADVANCED
    # -----------------------------------------------------

    if (
        modifier.type == 'NODES' and
        (
            modifier.name == "Array +" or
            (
                modifier.node_group and
                modifier.node_group.name == "Array"
            )
        )
    ):

        return 'MOD_ARRAY'

    if (
        modifier.type == 'NODES' and
        (
            modifier.name == "Boolean +" or
            (
                modifier.node_group and
                modifier.node_group.name == "Boolean +"
            )
        )
    ):
        return 'MOD_BOOLEAN'

    icons = {

        'MIRROR':
            'MOD_MIRROR',

        'SUBSURF':
            'MOD_SUBSURF',

        'MULTIRES':
            'MOD_MULTIRES',

        'REMESH':
            'MOD_REMESH',

        'DECIMATE':
            'MOD_DECIM',

        'BOOLEAN':
            'MOD_BOOLEAN',

        'BEVEL':
            'MOD_BEVEL',

        'SOLIDIFY':
            'MOD_SOLIDIFY',

        'ARRAY':
            'MOD_ARRAY',

        'CURVE':
            'MOD_CURVE',

        'DATA_TRANSFER':
            'MOD_DATA_TRANSFER',

        'HOOK':
            'HOOK',

        'SCREW':
            'MOD_SCREW',

        'SIMPLE_DEFORM':
            'MOD_SIMPLEDEFORM',

        'LATTICE':
            'MOD_LATTICE',

        'ARMATURE':
            'MOD_ARMATURE',

        'SHRINKWRAP':
            'MOD_SHRINKWRAP',

        'SKIN':
            'MOD_SKIN',

        'DISPLACE':
            'MOD_DISPLACE',

        'NODES':
            'NODETREE',
    }

    return icons.get(
        modifier.type,
        'MODIFIER'
    )

def draw_modifier_options(
    layout,
    modifier
):

    if modifier is None:
        return

    # =====================================================
    # MIRROR
    # =====================================================

    if modifier.type == 'MIRROR':

        layout.label(
            text="Axis"
        )

        row = layout.row(
            align=True
        )

        row.prop(
            modifier,
            "use_axis",
            index=0,
            text="X",
            toggle=True
        )

        row.prop(
            modifier,
            "use_axis",
            index=1,
            text="Y",
            toggle=True
        )

        row.prop(
            modifier,
            "use_axis",
            index=2,
            text="Z",
            toggle=True
        )

        layout.label(
            text="Bisect"
        )

        row = layout.row(
            align=True
        )

        row.prop(
            modifier,
            "use_bisect_axis",
            index=0,
            text="X",
            toggle=True
        )

        row.prop(
            modifier,
            "use_bisect_axis",
            index=1,
            text="Y",
            toggle=True
        )

        row.prop(
            modifier,
            "use_bisect_axis",
            index=2,
            text="Z",
            toggle=True
        )

        layout.label(
            text="Flip"
        )

        row = layout.row(
            align=True
        )

        row.prop(
            modifier,
            "use_bisect_flip_axis",
            index=0,
            text="X",
            toggle=True
        )

        row.prop(
            modifier,
            "use_bisect_flip_axis",
            index=1,
            text="Y",
            toggle=True
        )

        row.prop(
            modifier,
            "use_bisect_flip_axis",
            index=2,
            text="Z",
            toggle=True
        )

        layout.prop(
            modifier,
            "mirror_object",
            text="Mirror Object"
        )

        layout.prop(
            modifier,
            "merge_threshold",
            text="Bisect Distance"
        )

        layout.prop(
            modifier,
            "use_clip",
            text="Clipping"
        )

        layout.prop(
            modifier,
            "use_mirror_merge",
            text="Merge"
        )

    # =====================================================
    # SUBDIVISION
    # =====================================================

    elif modifier.type == 'SUBSURF':

        layout.prop(
            modifier,
            "subdivision_type",
            text="Type"
        )

        layout.prop(
            modifier,
            "levels",
            text="Viewport"
        )

        layout.prop(
            modifier,
            "render_levels",
            text="Render"
        )

    # =====================================================
    # MULTIRES
    # =====================================================

    elif modifier.type == 'MULTIRES':

        layout.prop(
            modifier,
            "levels",
            text="Viewport"
        )

        layout.prop(
            modifier,
            "sculpt_levels",
            text="Sculpt"
        )

        layout.prop(
            modifier,
            "render_levels",
            text="Render"
        )

        if safe_prop(
            modifier,
            "use_sculpt_base_mesh"
        ):

            layout.prop(
                modifier,
                "use_sculpt_base_mesh",
                text="Sculpt Base"
            )

        if safe_prop(
            modifier,
            "show_only_control_edges"
        ):

            layout.prop(
                modifier,
                "show_only_control_edges",
                text="Optimal"
            )

        row = layout.row(
            align=True
        )

        op = row.operator(
            "view3d.simple_multires_subdivide",
            text="Subdivide"
        )

        op.subdivision_type = 'CATMULL_CLARK'

        row = layout.row(
            align=True
        )

        op = row.operator(
            "view3d.simple_multires_subdivide",
            text="Simple"
        )

        op.subdivision_type = 'SIMPLE'

        op = row.operator(
            "view3d.simple_multires_subdivide",
            text="Linear"
        )

        op.subdivision_type = 'LINEAR'

        row = layout.row(
            align=True
        )

        row.operator(
            "view3d.simple_multires_delete_higher",
            text="Delete Higher"
        )

        row.operator(
            "view3d.simple_multires_unsubdivide",
            text="Unsubdivide"
        )

    # =====================================================
    # REMESH
    # =====================================================

    elif modifier.type == 'REMESH':

        layout.prop(
            modifier,
            "mode",
            text="Mode"
        )

        layout.prop(
            modifier,
            "octree_depth",
            text="Resolution"
        )

        layout.prop(
            modifier,
            "scale",
            text="Scale"
        )

        layout.prop(
            modifier,
            "sharpness",
            text="Sharpness"
        )

    # =====================================================
    # DECIMATE
    # =====================================================

    elif modifier.type == 'DECIMATE':

        layout.prop(
            modifier,
            "decimate_type",
            text="Mode"
        )

        if modifier.decimate_type == 'COLLAPSE':

            layout.prop(
                modifier,
                "ratio",
                text="Ratio"
            )

        elif modifier.decimate_type == 'UNSUBDIV':

            layout.prop(
                modifier,
                "iterations",
                text="Iterations"
            )

        elif modifier.decimate_type == 'DISSOLVE':

            layout.prop(
                modifier,
                "angle_limit",
                text="Angle Limit"
            )

    # =====================================================
    # BOOLEAN
    # =====================================================

    elif modifier.type == 'BOOLEAN':

        layout.prop(
            modifier,
            "operation",
            text="Operation"
        )

        layout.prop(
            modifier,
            "solver",
            text="Solver"
        )

        layout.prop(
            modifier,
            "operand_type",
            text="Operand"
        )

        if modifier.operand_type == 'OBJECT':

            layout.prop(
                modifier,
                "object",
                text="Object"
            )

        elif modifier.operand_type == 'COLLECTION':

            layout.prop(
                modifier,
                "collection",
                text="Collection"
            )

    # =====================================================
    # BEVEL
    # =====================================================

    elif modifier.type == 'BEVEL':

        layout.prop(
            modifier,
            "offset_type",
            text="Width Type"
        )

        layout.prop(
            modifier,
            "width",
            text="Width"
        )

        layout.prop(
            modifier,
            "segments",
            text="Segments"
        )

        layout.prop(
            modifier,
            "limit_method",
            text="Limit Method"
        )

        box = layout.box()

        box.label(
            text="Profile"
        )

        box.prop(
            modifier,
            "profile_type",
            text=""
        )

        if modifier.profile_type == 'CUSTOM':

            box.prop(
                modifier,
                "custom_profile",
                text=""
            )

        else:

            box.prop(
                modifier,
                "profile",
                text="Profile"
            )

    # =====================================================
    # SOLIDIFY
    # =====================================================

    elif modifier.type == 'SOLIDIFY':

        layout.prop(
            modifier,
            "thickness",
            text="Thickness"
        )

        layout.prop(
            modifier,
            "offset",
            text="Offset"
        )

        layout.prop(
            modifier,
            "use_rim",
            text="Fill"
        )

    # =====================================================
    # ARRAY LEGACY / NORMAL
    # =====================================================

    elif modifier.type == 'ARRAY':

        # -------------------------------------------------
        # FIT TYPE
        # -------------------------------------------------

        layout.prop(
            modifier,
            "fit_type",
            text="Fit Type"
        )

        # -------------------------------------------------
        # COUNT
        # -------------------------------------------------

        layout.prop(
            modifier,
            "count",
            text="Count"
        )

        # -------------------------------------------------
        # RELATIVE OFFSET
        # -------------------------------------------------

        box = layout.box()

        box.label(
            text="Relative Offset"
        )

        row = box.row(
            align=True
        )

        row.prop(
            modifier,
            "relative_offset_displace",
            index=0,
            text="X"
        )

        row.prop(
            modifier,
            "relative_offset_displace",
            index=1,
            text="Y"
        )

        row.prop(
            modifier,
            "relative_offset_displace",
            index=2,
            text="Z"
        )

        # -------------------------------------------------
        # CONSTANT OFFSET
        # -------------------------------------------------

        box = layout.box()

        box.prop(
            modifier,
            "use_constant_offset",
            text="Constant Offset"
        )

        row = box.row(
            align=True
        )

        row.enabled = modifier.use_constant_offset

        row.prop(
            modifier,
            "constant_offset_displace",
            index=0,
            text="X"
        )

        row.prop(
            modifier,
            "constant_offset_displace",
            index=1,
            text="Y"
        )

        row.prop(
            modifier,
            "constant_offset_displace",
            index=2,
            text="Z"
        )

        # -------------------------------------------------
        # OBJECT OFFSET
        # -------------------------------------------------

        box = layout.box()

        box.prop(
            modifier,
            "use_object_offset",
            text="Object Offset"
        )

        row = box.row()

        row.enabled = modifier.use_object_offset

        row.prop(
            modifier,
            "offset_object",
            text="Object"
        )

        # -------------------------------------------------
        # MERGE
        # -------------------------------------------------

        box = layout.box()

        box.label(
            text="Merge"
        )

        box.prop(
            modifier,
            "use_merge_vertices",
            text="Merge"
        )

        row = box.row()

        row.enabled = modifier.use_merge_vertices

        row.prop(
            modifier,
            "merge_threshold",
            text="Distance"
        )

        box.prop(
            modifier,
            "use_merge_vertices_cap",
            text="First and Last"
        )

    # =====================================================
    # ARRAY +
    # =====================================================

    elif modifier.type == 'NODES' and (
        modifier.name == "Array +" or
        (
            modifier.node_group and
            modifier.node_group.name == "Array"
        )
    ):

        layout.label(
            text="Open Properties Modifiers to start editing.",
            icon='INFO'
        )

    # =====================================================
    # BOOLEAN +
    # =====================================================

    elif modifier.type == 'NODES' and (
        modifier.name == "Boolean +" or
        (
            modifier.node_group and
            modifier.node_group.name == "Boolean +"
        )
    ):

        layout.label(
            text="Open Properties Modifiers to start editing.",
            icon='INFO'
        )

    # =====================================================
    # SCATTER
    # =====================================================

    elif modifier.type == 'NODES' and (
        modifier.name == "Scatter"
    ):

        layout.label(
            text="Open Properties Modifiers to start editing.",
            icon='INFO'
        )

    # =====================================================
    # CURVE
    # =====================================================

    # =====================================================
    # CAST / CORRECTIVE SMOOTH
    # =====================================================

    elif modifier.type in {
        'CAST',
        'CORRECTIVE_SMOOTH'
    }:

        layout.label(
            text="Open Properties Modifiers to start editing.",
            icon='INFO'
        )

    # =====================================================
    # CURVE
    # =====================================================


        layout.prop(
            modifier,
            "object",
            text="Curve"
        )

        layout.prop(
            modifier,
            "deform_axis",
            text="Deform Axis"
        )

        layout.prop(
            modifier,
            "vertex_group",
            text="Vertex Group"
        )

    # =====================================================
    # DATA TRANSFER
    # =====================================================

    elif modifier.type == 'DATA_TRANSFER':

        layout.prop(
            modifier,
            "object",
            text="Source"
        )

        layout.prop(
            modifier,
            "mix_mode",
            text="Mix Mode"
        )

        layout.prop(
            modifier,
            "mix_factor",
            text="Mix Factor"
        )

        layout.prop(
            modifier,
            "vertex_group",
            text="Vertex Group"
        )

        box = layout.box()

        box.label(
            text="Face Corner Data"
        )

        if safe_prop(
            modifier,
            "use_loop_data"
        ):

            box.prop(
                modifier,
                "use_loop_data",
                text="Enable"
            )

        if safe_prop(
            modifier,
            "data_types_loops"
        ):

            box.prop(
                modifier,
                "data_types_loops",
                text=""
            )

        if safe_prop(
            modifier,
            "loop_mapping"
        ):

            box.prop(
                modifier,
                "loop_mapping",
                text="Mapping"
            )

    # =====================================================
    # HOOK
    # =====================================================

    elif modifier.type == 'HOOK':

        layout.prop(
            modifier,
            "object",
            text="Object"
        )

        layout.prop(
            modifier,
            "strength",
            text="Strength"
        )

        layout.prop(
            modifier,
            "falloff_type",
            text="Falloff Type"
        )

        layout.prop(
            modifier,
            "use_falloff_uniform",
            text="Uniform"
        )

        layout.prop(
            modifier,
            "falloff_radius",
            text="Radius"
        )

        layout.prop(
            modifier,
            "vertex_group",
            text="Vertex Group"
        )

    # =====================================================
    # SCREW
    # =====================================================

    elif modifier.type == 'SCREW':

        layout.prop(
            modifier,
            "angle",
            text="Angle"
        )

        layout.prop(
            modifier,
            "screw_offset",
            text="Screw"
        )

        layout.prop(
            modifier,
            "iterations",
            text="Iterations"
        )

        layout.prop(
            modifier,
            "axis",
            text="Axis"
        )

        layout.prop(
            modifier,
            "steps",
            text="Viewport Steps"
        )

        layout.prop(
            modifier,
            "render_steps",
            text="Render Steps"
        )

        row = layout.row(
            align=True
        )

        if safe_prop(
            modifier,
            "use_merge_vertices"
        ):

            row.prop(
                modifier,
                "use_merge_vertices",
                text="Merge"
            )

        if safe_prop(
            modifier,
            "merge_threshold"
        ):

            row.prop(
                modifier,
                "merge_threshold",
                text="Distance"
            )

    # =====================================================
    # SIMPLE DEFORM
    # =====================================================

    elif modifier.type == 'SIMPLE_DEFORM':

        layout.prop(
            modifier,
            "deform_method",
            text="Deform"
        )

        layout.prop(
            modifier,
            "deform_axis",
            text="Axis"
        )

        if modifier.deform_method in {
            'TWIST',
            'BEND'
        }:

            layout.prop(
                modifier,
                "angle",
                text="Angle"
            )

        else:

            layout.prop(
                modifier,
                "factor",
                text="Factor"
            )

        layout.prop(
            modifier,
            "origin",
            text="Origin"
        )

        layout.prop(
            modifier,
            "vertex_group",
            text="Vertex Group"
        )

    # =====================================================
    # LATTICE
    # =====================================================

    elif modifier.type == 'LATTICE':

        layout.prop(
            modifier,
            "object",
            text="Lattice"
        )

        layout.prop(
            modifier,
            "strength",
            text="Strength"
        )

        layout.prop(
            modifier,
            "vertex_group",
            text="Vertex Group"
        )

    # =====================================================
    # ARMATURE
    # =====================================================

    elif modifier.type == 'ARMATURE':

        layout.prop(
            modifier,
            "object",
            text="Object"
        )

        layout.prop(
            modifier,
            "vertex_group",
            text="Vertex Group"
        )

        layout.prop(
            modifier,
            "use_deform_preserve_volume",
            text="Preserve Volume"
        )

        layout.prop(
            modifier,
            "use_multi_modifier",
            text="Multi Modifier"
        )

        layout.prop(
            modifier,
            "use_vertex_groups",
            text="Bind to Vertex Group"
        )

        layout.prop(
            modifier,
            "use_bone_envelopes",
            text="Bone Envelopes"
        )

    # =====================================================
    # SHRINKWRAP
    # =====================================================

    elif modifier.type == 'SHRINKWRAP':

        layout.prop(
            modifier,
            "wrap_method",
            text="Method"
        )

        layout.prop(
            modifier,
            "wrap_mode",
            text="Snap"
        )

        layout.prop(
            modifier,
            "target",
            text="Target"
        )

        layout.prop(
            modifier,
            "offset",
            text="Offset"
        )

        layout.prop(
            modifier,
            "vertex_group",
            text="Vertex Group"
        )

    # =====================================================
    # SKIN
    # =====================================================

    elif modifier.type == 'SKIN':

        layout.prop(
            modifier,
            "use_smooth_shade",
            text="Smooth Shading"
        )

        row = layout.row()

        row.operator(
            "view3d.skin_create_armature",
            text="Create Armature",
            icon='ARMATURE_DATA'
        )

    # =====================================================
    # DISPLACE
    # =====================================================

    elif modifier.type == 'DISPLACE':

        row = layout.row(
            align=True
        )

        row.operator(
            "view3d.displace_new_texture",
            text="New Texture",
            icon='ADD'
        )

        layout.prop(
            modifier,
            "texture",
            text="Texture"
        )

        layout.prop(
            modifier,
            "strength",
            text="Strength"
        )

        layout.prop(
            modifier,
            "mid_level",
            text="Midlevel"
        )

        layout.prop(
            modifier,
            "direction",
            text="Direction"
        )

        layout.prop(
            modifier,
            "texture_coords",
            text="Coordinates"
        )

        layout.prop(
            modifier,
            "vertex_group",
            text="Vertex Group"
        )

    # =====================================================
    # MODIFIERS WITHOUT CUSTOM OPTIONS
    # =====================================================

    elif modifier.type in {
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
    }:

        layout.label(
            text="Open Properties Modifiers to start editing.",
            icon='INFO'
        )

    # =====================================================
    # GEOMETRY NODES
    # =====================================================

    elif modifier.type == 'NODES':

        layout.prop(
            modifier,
            "node_group",
            text="Node Group"
        )

def modifier_add_items(self, context):

    return [

        (
            'MIRROR',
            "Mirror",
            "Add Mirror modifier"
        ),

        (
            'SUBSURF',
            "Subdivision",
            "Add Subdivision Surface modifier"
        ),

        (
            'MULTIRES',
            "Multiresolution",
            "Add Multiresolution modifier"
        ),

        (
            'REMESH',
            "Remesh",
            "Add Remesh modifier"
        ),

        (
            'SCATTER_ON_SURFACE',
            "Scatter",
            "Add Scatter on Surface modifier"
        ),

        (
            'DECIMATE',
            "Decimate",
            "Add Decimate modifier"
        ),

        (
            'BOOLEAN',
            "Boolean",
            "Add Boolean modifier"
        ),

        (
            'BOOLEAN_PLUS',
            "Boolean +",
            "Add Boolean + Geometry Nodes modifier"
        ),

        (
            'BEVEL',
            "Bevel",
            "Add Bevel modifier"
        ),

        (
            'SOLIDIFY',
            "Solidify",
            "Add Solidify modifier"
        ),

        (
            'ARRAY',
            "Array",
            "Add legacy Array modifier"
        ),

        (
            'ARRAY_MODERN',
            "Array +",
            "Add modern Blender Array Geometry Nodes modifier"
        ),

        (
            'CURVE',
            "Curve Deform",
            "Add Curve Deform modifier"
        ),

        (
            'DATA_TRANSFER',
            "Data Transfer",
            "Add Data Transfer modifier"
        ),

        (
            'HOOK',
            "Hook",
            "Add Hook modifier"
        ),

        (
            'SCREW',
            "Screw",
            "Add Screw modifier"
        ),

        (
            'SIMPLE_DEFORM',
            "Simple Deform",
            "Add Simple Deform modifier"
        ),

        (
            'LATTICE',
            "Lattice",
            "Add Lattice modifier"
        ),

        (
            'ARMATURE',
            "Armature",
            "Add Armature modifier"
        ),

        (
            'SHRINKWRAP',
            "Shrinkwrap",
            "Add Shrinkwrap modifier"
        ),

        (
            'SKIN',
            "Skin",
            "Add Skin modifier"
        ),

        (
            'DISPLACE',
            "Displace",
            "Add Displace modifier"
        ),

        (
            'NODES',
            "Geometry Nodes",
            "Add Geometry Nodes modifier"
        ),

        (
            'BUILD',
            "Build",
            "Add Build modifier"
        ),

        (
            'CLOTH',
            "Cloth",
            "Add Cloth modifier"
        ),

        (
            'COLLISION',
            "Collision",
            "Add Collision modifier"
        ),

        (
            'EXPLODE',
            "Explode",
            "Add Explode modifier"
        ),

        (
            'FLUID',
            "Fluid",
            "Add Fluid modifier"
        ),

        (
            'LAPLACIANDEFORM',
            "Laplacian Deform",
            "Add Laplacian Deform modifier"
        ),

        (
            'LAPLACIANSMOOTH',
            "Laplacian Smooth",
            "Add Laplacian Smooth modifier"
        ),

        (
            'MESH_CACHE',
            "Mesh Cache",
            "Add Mesh Cache modifier"
        ),

        (
            'MESH_DEFORM',
            "Mesh Deform",
            "Add Mesh Deform modifier"
        ),

        (
            'MESH_SEQUENCE_CACHE',
            "Mesh Sequence Cache",
            "Add Mesh Sequence Cache modifier"
        ),

        (
            'NORMAL_EDIT',
            "Normal Edit",
            "Add Normal Edit modifier"
        ),

        (
            'PARTICLE_INSTANCE',
            "Particle Instance",
            "Add Particle Instance modifier"
        ),

        (
            'PARTICLE_SYSTEM',
            "Particle System",
            "Add Particle System modifier"
        ),

        (
            'SMOOTH',
            "Smooth",
            "Add Smooth modifier"
        ),

        (
            'SURFACE_DEFORM',
            "Surface Deform",
            "Add Surface Deform modifier"
        ),
        (
            'SOFT_BODY',
            "Soft Body",
            "Add Soft Body modifier"
        ),

        (
            'TRIANGULATE',
            "Triangulate",
            "Add Triangulate modifier"
        ),

        (
            'UV_WARP',
            "UV Warp",
            "Add UV Warp modifier"
        ),

        (
            'VERTEX_WEIGHT_EDIT',
            "Vertex Weight Edit",
            "Add Vertex Weight Edit modifier"
        ),

        (
            'VERTEX_WEIGHT_MIX',
            "Vertex Weight Mix",
            "Add Vertex Weight Mix modifier"
        ),

        (
            'VERTEX_WEIGHT_PROXIMITY',
            "Vertex Weight Proximity",
            "Add Vertex Weight Proximity modifier"
        ),

        (
            'WARP',
            "Warp",
            "Add Warp modifier"
        ),

        (
            'WAVE',
            "Wave",
            "Add Wave modifier"
        ),

        (
            'WELD',
            "Weld",
            "Add Weld modifier"
        ),

        (
            'WIREFRAME',
            "Wireframe",
            "Add Wireframe modifier"
        ),

        (
            'WEIGHTED_NORMAL',
            "Weighted Normal",
            "Add Weighted Normal modifier"
        ),

        (
            'CAST',
            "Cast",
            "Add Cast modifier"
        ),

        (
            'CORRECTIVE_SMOOTH',
            "Corrective Smooth",
            "Add Corrective Smooth modifier"
        ),

    ]

class VIEW3D_PT_simple_modifiers(
    bpy.types.Panel
):

    bl_label = "Simple Modifiers"
    bl_idname = "VIEW3D_PT_simple_modifiers"

    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

    bl_category = "Modifiers"

    def draw(self, context):

        layout = self.layout
        obj = context.active_object

        # -------------------------------------------------
        # SIN OBJETO
        # -------------------------------------------------

        if obj is None:

            layout.label(
                text="No active object",
                icon='INFO'
            )

            return

        # -------------------------------------------------
        # OBJETO NO COMPATIBLE
        # -------------------------------------------------

        if obj.type not in {
            'MESH',
            'CURVE'
        }:

            layout.label(
                text="Select a mesh or curve",
                icon='INFO'
            )

            return

        # =================================================
        # ADD MODIFIER
        # =================================================

        box = layout.box()

        box.label(
            text="Add Modifier",
            icon='ADD'
        )

        row = box.row(
            align=True
        )

        row.prop(
            context.scene,
            "simple_modifier_add",
            text=""
        )

        selected_modifier = context.scene.simple_modifier_add

        # Independent square More dropdown. It only changes the selected modifier.

        # Add is the final control on the right and performs the actual addition.
        op = row.operator(
            "view3d.add_simple_modifier",
            text="Add",
            icon='ADD'
        )
        op.modifier_type = selected_modifier

        # =================================================
        # STACK
        # =================================================

        layout.separator()

        box = layout.box()

        box.label(
            text="Modifier Stack",
            icon='MODIFIER'
        )

        if not obj.modifiers:

            box.label(
                text="No modifiers",
                icon='INFO'
            )

        else:

            for index, modifier in enumerate(
                obj.modifiers
            ):

                selected = (
                    index ==
                    context.scene.simple_modifier_index
                )

                row = box.row(
                    align=True
                )

                op = row.operator(
                    "view3d.select_simple_modifier",
                    text=modifier.name,
                    icon=modifier_icon(modifier),
                    depress=selected
                )

                op.index = index

                op = row.operator(
                    "view3d.move_modifier_up",
                    text="",
                    icon='TRIA_UP'
                )

                op.index = index

                op = row.operator(
                    "view3d.move_modifier_down",
                    text="",
                    icon='TRIA_DOWN'
                )

                op.index = index

        # =================================================
        # OPCIONES
        # =================================================

        modifier = get_modifier(
            obj,
            context.scene.simple_modifier_index
        )

        if modifier is not None:

            layout.separator()

            box = layout.box()

            box.label(
                text=f"Options: {modifier.name}",
                icon=modifier_icon(modifier)
            )

            draw_modifier_options(
                box,
                modifier
            )

            row = box.row(
                align=True
            )

            op = row.operator(
                "view3d.apply_simple_modifier",
                text="Apply",
                icon='CHECKMARK'
            )

            op.index = (
                context.scene.simple_modifier_index
            )

            op = row.operator(
                "view3d.remove_simple_modifier",
                text="Delete",
                icon='X'
            )

            op.index = (
                context.scene.simple_modifier_index
            )

CLASSES=(
    VIEW3D_OT_add_simple_modifier,
    VIEW3D_OT_select_modifier,
    VIEW3D_OT_remove_simple_modifier,
    VIEW3D_OT_apply_simple_modifier,
    VIEW3D_OT_move_modifier_up,
    VIEW3D_OT_move_modifier_down,
    VIEW3D_OT_multires_subdivide,
    VIEW3D_OT_multires_delete_higher,
    VIEW3D_OT_multires_unsubdivide,
    VIEW3D_OT_skin_create_armature,
    VIEW3D_OT_displace_new_texture,
    VIEW3D_PT_simple_modifiers,
)

def register():
    for cls in CLASSES:
        try: bpy.utils.register_class(cls)
        except ValueError: pass
    if not hasattr(bpy.types.Scene, "simple_modifier_index"):
        bpy.types.Scene.simple_modifier_index=bpy.props.IntProperty(name="Selected Modifier",default=0,min=0)
    if not hasattr(bpy.types.Scene, "simple_modifier_add"):
        bpy.types.Scene.simple_modifier_add=bpy.props.EnumProperty(name="Modifier",description="Choose a modifier",items=modifier_add_items)

def unregister():
    for p in ('simple_modifier_index','simple_modifier_add'):
        try: delattr(bpy.types.Scene,p)
        except Exception: pass
    for cls in reversed(CLASSES):
        try: bpy.utils.unregister_class(cls)
        except Exception: pass
