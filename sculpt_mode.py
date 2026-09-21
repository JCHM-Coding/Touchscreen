# SPDX-License-Identifier: GPL-3.0-or-later
#
# Touchscreen - Sculpt Mode
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

import bpy_extras.view3d_utils

import ctypes

def _get_geodesic_step(scene):
    return getattr(scene, "expand_helper_geodesic_step", 0)

def _get_recursion_topology(scene):
    return getattr(scene, "expand_helper_recursion_topology", False)

# Expand Helper runtime state.
_test_timers = []
_test_kmis = []
_draw_handler = None
_frames_counter = 0
_target_frames = 0
_active_phase = 'NONE'
_loop_events = 0
_distort_events = 0
_kmi_loop = None
_kmi_distort = None
_snap_kmi = None
_geodesic_step_timer = None
_geodesic_step_kmi = None

# Blender 5.3 can expose the native sculpt.expand operator as two small
# "Expand undocumented operator" toolbar tools.  Expand Helper already
# provides its own dedicated Expand tools, so hide only those native entries
# while this addon is enabled.
_hidden_native_expand_tools = None

def _hide_native_sculpt_expand_tools():
    global _hidden_native_expand_tools
    try:
        from bl_ui.space_toolsystem_toolbar import VIEW3D_PT_tools_active
        tools = VIEW3D_PT_tools_active._tools
        sculpt_tools = tools.get('SCULPT')
        if not isinstance(sculpt_tools, list):
            return

        _hidden_native_expand_tools = list(sculpt_tools)

        def filter_tools(items):
            result = []
            for item in items:
                if isinstance(item, (list, tuple)):
                    nested = filter_tools(item)
                    result.append(type(item)(nested))
                    continue
                try:
                    operator = getattr(item, 'operator', '')
                    if operator == 'sculpt.expand':
                        continue
                except Exception:
                    pass
                result.append(item)
            return result

        tools['SCULPT'] = filter_tools(sculpt_tools)
    except Exception:
        _hidden_native_expand_tools = None

def _restore_native_sculpt_expand_tools():
    global _hidden_native_expand_tools
    if _hidden_native_expand_tools is None:
        return
    try:
        from bl_ui.space_toolsystem_toolbar import VIEW3D_PT_tools_active
        VIEW3D_PT_tools_active._tools['SCULPT'] = _hidden_native_expand_tools
    except Exception:
        pass
    _hidden_native_expand_tools = None

def _find_expand_modal_keymap():
    wm = bpy.context.window_manager
    keyconfigs = []

    if wm.keyconfigs.active:
        keyconfigs.append(wm.keyconfigs.active)
    if wm.keyconfigs.user:
        keyconfigs.append(wm.keyconfigs.user)
    if wm.keyconfigs.addon:
        keyconfigs.append(wm.keyconfigs.addon)

    seen = set()
    for kc in keyconfigs:
        if kc is None or kc in seen:
            continue
        seen.add(kc)

        km = kc.keymaps.get("Sculpt Expand Modal")
        if km:
            return km

    return None

def cleanup_internal_events():
    global _test_timers, _test_kmis, _draw_handler, _frames_counter, _target_frames
    global _active_phase, _loop_events, _distort_events
    global _kmi_loop, _kmi_distort, _snap_kmi
    global _geodesic_step_timer, _geodesic_step_kmi

    wm = bpy.context.window_manager

    # 1. Remover Draw Handler
    if _draw_handler is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_draw_handler, 'WINDOW')
        except Exception:
            pass
        _draw_handler = None

    # 2. Remover Timers
    for t in _test_timers:
        try:
            wm.event_timer_remove(t)
        except Exception:
            pass
    _test_timers.clear()

    # 3. Remover Keymap Items
    if _test_kmis or _snap_kmi:
        km = _find_expand_modal_keymap()
        if km:
            for kmi in _test_kmis:
                try:
                    km.keymap_items.remove(kmi)
                except Exception:
                    pass
            if _snap_kmi:
                try:
                    km.keymap_items.remove(_snap_kmi)
                except Exception:
                    pass
        _test_kmis.clear()
        _snap_kmi = None

    # Remove the dedicated Geodesic Step timer/KMI.
    if _geodesic_step_kmi is not None:
        km = _find_expand_modal_keymap()
        if km:
            try:
                km.keymap_items.remove(_geodesic_step_kmi)
            except Exception:
                pass
        _geodesic_step_kmi = None

    if _geodesic_step_timer is not None:
        try:
            wm.event_timer_remove(_geodesic_step_timer)
        except Exception:
            pass
        _geodesic_step_timer = None

    _frames_counter = 0
    _target_frames = 0
    _active_phase = 'NONE'
    _loop_events = 0
    _distort_events = 0
    _kmi_loop = None
    _kmi_distort = None

def _on_expand_draw_step():
    global _frames_counter, _target_frames
    global _test_timers, _test_kmis, _draw_handler
    global _active_phase, _kmi_loop, _kmi_distort, _snap_kmi

    _frames_counter += 1

    # Disable SNAP after sending it so it is triggered only once
    if _snap_kmi and _frames_counter == 6:
        try:
            _snap_kmi.active = False
        except Exception:
            pass

    # Switch from Loop to Distortion phase when applicable
    if _active_phase == 'LOOP':
        if _frames_counter >= _loop_events and _distort_events > 0:
            if _kmi_loop is not None:
                try:
                    _kmi_loop.active = False
                except Exception:
                    pass

            if _kmi_distort is not None:
                try:
                    _kmi_distort.active = True
                except Exception:
                    pass

            _active_phase = 'DISTORTION'

    # Finish
    if _frames_counter >= _target_frames:
        cleanup_internal_events()

def setup_internal_events(loop_count=1, texture_distortion=0, is_snap=False):
    global _test_timers, _test_kmis, _draw_handler
    global _frames_counter, _target_frames
    global _active_phase, _loop_events, _distort_events
    global _kmi_loop, _kmi_distort, _snap_kmi

    cleanup_internal_events()

    km = _find_expand_modal_keymap()
    if not km:
        return False

    wm = bpy.context.window_manager
    window = bpy.context.window
    if not window:
        return False

    # SNAP LOGIC
    if is_snap:
        _target_frames = 20
        _frames_counter = 0
        try:
            _snap_kmi = km.keymap_items.new_modal("SNAP_TOGGLE", 'TIMER', 'ANY')
            _snap_kmi.active = True
        except Exception as e:
            print("EXPAND SNAP - Error creando KMI:", e)
            cleanup_internal_events()
            return False
    else:
        loops_to_add = max(0, loop_count - 1)
        distort_to_add = max(0, texture_distortion)

        if loops_to_add == 0 and distort_to_add == 0:
            return True

        _loop_events = loops_to_add
        _distort_events = distort_to_add
        _frames_counter = 0
        total_events = loops_to_add + distort_to_add
        _target_frames = total_events + 1

        if loops_to_add > 0:
            try:
                _kmi_loop = km.keymap_items.new_modal("LOOP_COUNT_INCREASE", 'TIMER', 'ANY')
                _kmi_loop.active = True
                _test_kmis.append(_kmi_loop)
            except Exception as e:
                print("EXPAND - Error creando KMI Loop:", e)
                cleanup_internal_events()
                return False

        if distort_to_add > 0:
            try:
                _kmi_distort = km.keymap_items.new_modal("TEXTURE_DISTORTION_INCREASE", 'TIMER', 'ANY')
                _kmi_distort.active = False if loops_to_add > 0 else True
                _test_kmis.append(_kmi_distort)
            except Exception as e:
                print("EXPAND - Error creando KMI Distortion:", e)
                cleanup_internal_events()
                return False

        _active_phase = 'LOOP' if loops_to_add > 0 else 'DISTORTION'

    # Single timer
    try:
        timer = wm.event_timer_add(0.02 if not is_snap else 0.05, window=window)
        _test_timers.append(timer)

        _draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            _on_expand_draw_step,
            (),
            'WINDOW',
            'POST_VIEW'
        )
    except Exception as e:
        print("EXPAND - Error creando timer:", e)
        cleanup_internal_events()
        return False

    return True

def stop_geodesic_step():
    """Immediately stop the dedicated Geodesic/Topology recursion timer and KMI."""
    global _geodesic_step_timer, _geodesic_step_kmi

    wm = bpy.context.window_manager

    if _geodesic_step_kmi is not None:
        km = _find_expand_modal_keymap()
        if km:
            try:
                km.keymap_items.remove(_geodesic_step_kmi)
            except Exception:
                pass
        _geodesic_step_kmi = None

    if _geodesic_step_timer is not None:
        try:
            wm.event_timer_remove(_geodesic_step_timer)
        except Exception:
            pass
        _geodesic_step_timer = None

def _update_geodesic_step(scene, context):
    """Reset recursion immediately when Step is changed back to 0."""
    if scene.expand_helper_geodesic_step <= 0:
        stop_geodesic_step()

def setup_geodesic_step(step_seconds, topology=False):
    """Create a repeating timer for native Geodesic/Topology recursion.

    Step 0 disables recursion.
    Step 1 = one recursion every second.
    Step 2 = one recursion every 2 seconds, etc.
    """
    global _geodesic_step_timer, _geodesic_step_kmi

    wm = bpy.context.window_manager
    window = bpy.context.window

    # IMPORTANT: Step 0 must actively remove a previously created timer/KMI.
    # Previously this only returned True, leaving the old recursion running.
    if step_seconds <= 0:
        stop_geodesic_step()
        return True

    # If Step is changed while a previous recursion timer exists, replace it
    # with the new interval instead of leaving the old timer alive.
    stop_geodesic_step()

    km = _find_expand_modal_keymap()
    if not km or not window:
        print("EXPAND HELPER - Sculpt Expand Modal keymap/window not found")
        return False

    try:
        recursion_event = (
            "RECURSION_STEP_TOPOLOGY" if topology
            else "RECURSION_STEP_GEODESIC"
        )
        _geodesic_step_kmi = km.keymap_items.new_modal(
            recursion_event, 'TIMER', 'ANY'
        )
        _geodesic_step_kmi.active = True

        _geodesic_step_timer = wm.event_timer_add(
            float(step_seconds), window=window
        )
        return True

    except Exception as e:
        print("EXPAND HELPER - Error creating Geodesic Step timer:", e)

        if _geodesic_step_kmi is not None:
            try:
                km.keymap_items.remove(_geodesic_step_kmi)
            except Exception:
                pass
            _geodesic_step_kmi = None

        if _geodesic_step_timer is not None:
            try:
                wm.event_timer_remove(_geodesic_step_timer)
            except Exception:
                pass
            _geodesic_step_timer = None

        return False

def raycast_from_event(context, event):
    coord = (event.mouse_region_x, event.mouse_region_y)
    region = context.region
    rv3d = context.region_data

    if not region or not rv3d:
        return False, None, None, None

    view_vector = bpy_extras.view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
    ray_origin = bpy_extras.view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)

    obj = context.active_object
    if not obj or obj.type != 'MESH':
        return False, None, None, None

    matrix_inv = obj.matrix_world.inverted()
    ray_origin_obj = matrix_inv @ ray_origin
    view_target_obj = matrix_inv @ (ray_origin + view_vector)
    ray_direction_obj = (view_target_obj - ray_origin_obj).normalized()

    hit, location, normal, face_index = obj.ray_cast(ray_origin_obj, ray_direction_obj)
    return hit, location, normal, face_index

class SCULPT_OT_expand_mask_execute(bpy.types.Operator):
    bl_idname = "sculpt.expand_mask_execute"
    bl_label = "Expand Mask"

    falloff: bpy.props.EnumProperty(
        name="Falloff",
        items=[
            ('GEODESIC', "Geodesic", ""),
            ('TOPOLOGY', "Topology", ""),
            ('TOPOLOGY_DIAGONALS', "Topology Diagonals", ""),
            ('SPHERICAL', "Spherical", ""),
        ],
        default='TOPOLOGY',
    )
    gradient_falloff: bpy.props.BoolProperty(name="Gradient Falloff", default=False)
    preserve: bpy.props.BoolProperty(name="Preserve", default=False)
    invert: bpy.props.BoolProperty(name="Invert", default=False)
    expand_by_normals: bpy.props.BoolProperty(name="Expand by Normals", default=False)
    loop_count: bpy.props.IntProperty(name="Loop", default=1, min=1, soft_max=16)
    texture_distortion: bpy.props.IntProperty(name="Distortion", default=0, min=0, soft_max=32)

    # Geodesic recursion:
    # 0 = disabled, 1 = every second, 2 = every 2 seconds, etc.
    step: bpy.props.IntProperty(
        name="Step",
        description="Perform one true Geodesic recursion every N seconds. 0 disables recursion.",
        default=0,
        min=0,
        soft_max=9,
    )

    def modal(self, context, event):
        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            hit, _, _, _ = raycast_from_event(context, event)

            if not hit:
                cleanup_internal_events()
                return {'FINISHED'}
        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        falloff_type = 'NORMALS' if self.expand_by_normals else self.falloff

        # Step drives native recursion for all non-snap Mask tools.
        # T / G selects Topology or Geodesic recursion.
        if not setup_geodesic_step(
            _get_geodesic_step(context.scene),
            _get_recursion_topology(context.scene),
        ):
            return {'CANCELLED'}

        # When Step is active, the TIMER event must belong exclusively to the
        # native recursion modal map. The old Loop/Distortion timer uses the
        # same TIMER event and would consume the event before recursion.
        # With Step=0, keep the existing Loop/Distortion behaviour unchanged.
        if _get_geodesic_step(context.scene) <= 0:
            setup_internal_events(self.loop_count, self.texture_distortion)

        return bpy.ops.sculpt.expand(
            'INVOKE_DEFAULT',
            target='MASK',
            falloff_type=falloff_type,
            invert=self.invert,
            use_mask_preserve=self.preserve,
            use_falloff_gradient=self.gradient_falloff,
        )

class SCULPT_OT_expand_mask_snap_execute(bpy.types.Operator):
    bl_idname = "sculpt.expand_mask_snap_execute"
    bl_label = "Expand Mask Snap"

    preserve: bpy.props.BoolProperty(name="Preserve", default=False)
    invert: bpy.props.BoolProperty(name="Invert", default=False)

    def invoke(self, context, event):
        if not setup_internal_events(is_snap=True):
            return {'CANCELLED'}

        return bpy.ops.sculpt.expand(
            'INVOKE_DEFAULT',
            target='MASK',
            falloff_type='GEODESIC',
            invert=self.invert,
            use_mask_preserve=self.preserve,
            use_reposition_pivot=True,
        )

class SCULPT_OT_expand_facesets_execute(bpy.types.Operator):
    bl_idname = "sculpt.expand_facesets_execute"
    bl_label = "Expand Face Sets"

    falloff: bpy.props.EnumProperty(
        name="Falloff",
        items=[
            ('GEODESIC', "Geodesic", ""),
            ('TOPOLOGY', "Topology", ""),
            ('TOPOLOGY_DIAGONALS', "Topology Diagonals", ""),
            ('SPHERICAL', "Spherical", ""),
        ],
        default='TOPOLOGY',
    )
    preserve: bpy.props.BoolProperty(name="Preserve", default=False)
    invert: bpy.props.BoolProperty(name="Invert", default=False)
    active_faceset: bpy.props.BoolProperty(name="Active Face Set", default=False)
    loop_count: bpy.props.IntProperty(name="Loop", default=1, min=1, soft_max=16)
    step: bpy.props.IntProperty(
        name="Step",
        description="Recursion interval in seconds. 0 disables recursion.",
        default=0,
        min=0,
        soft_max=9,
    )

    def modal(self, context, event):
        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            hit, _, _, _ = raycast_from_event(context, event)

            if not hit:
                cleanup_internal_events()
                return {'FINISHED'}
        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        if not setup_geodesic_step(
            _get_geodesic_step(context.scene),
            _get_recursion_topology(context.scene),
        ):
            return {'CANCELLED'}
        # As above, do not install another TIMER modal map while recursion is
        # active. With Step=0 the existing Loop behaviour remains available.
        if _get_geodesic_step(context.scene) <= 0:
            setup_internal_events(self.loop_count, 0)
        if self.active_faceset:
            return bpy.ops.sculpt.expand(
                'INVOKE_DEFAULT',
                target='FACE_SETS',
                falloff_type='BOUNDARY_FACE_SET',
                invert=self.invert,
                use_mask_preserve=self.preserve,
                use_modify_active=True,
            )

        return bpy.ops.sculpt.expand(
            'INVOKE_DEFAULT',
            target='FACE_SETS',
            falloff_type=self.falloff,
            invert=self.invert,
            use_mask_preserve=self.preserve,
        )

class SCULPT_OT_expand_facesets_visibility(bpy.types.Operator):
    bl_idname = "sculpt.expand_facesets_visibility"
    bl_label = "Face Sets Visibility Test"

    action: bpy.props.EnumProperty(
        items=[
            ('HIDE', "Hide", ""),
            ('ISOLATE', "Isolate", ""),
            ('SHOW_ALL', "Show All", ""),
        ]
    )

    def invoke(self, context, event):
        # Show All remains direct.
        if self.action == 'SHOW_ALL':
            try:
                bpy.ops.paint.hide_show_all(action='SHOW')
                print("VISIBILITY TEST - FACE SETS SHOW ALL")
            except Exception as e:
                print("VISIBILITY TEST - Show All ERROR:", e)
            return {'FINISHED'}

        # IMPORTANT:
        # Do not raycast and do not calculate Face Set IDs here.
        # We simply wait for the actual viewport click and then invoke
        # Blender's native cursor-dependent operator from the VIEW_3D
        # context.
        context.window_manager.modal_handler_add(self)
        print("VISIBILITY TEST - WAITING FOR VIEWPORT CLICK:", self.action)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type in {'ESC', 'RIGHTMOUSE'} and event.value == 'PRESS':
            print("VISIBILITY TEST - CANCEL")
            return {'CANCELLED'}

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            # We are now receiving the click in the 3D View.
            # Use the native Blender operator exactly as its Sculpt
            # keymap does. Blender's operator is cursor-dependent.
            try:
                if self.action == 'HIDE':
                    # Native Shift-H operation:
                    # Hide the Face Set under the cursor.
                    result = bpy.ops.sculpt.face_set_change_visibility(
                        'INVOKE_DEFAULT',
                        mode='HIDE_ACTIVE'
                    )
                    print(
                        "VISIBILITY TEST - NATIVE HIDE:",
                        result,
                        "mouse=", event.mouse_region_x, event.mouse_region_y
                    )
                else:
                    # Native H operation:
                    # Isolate/toggle visibility of the Face Set under
                    # the cursor.
                    result = bpy.ops.sculpt.face_set_change_visibility(
                        'INVOKE_DEFAULT',
                        mode='TOGGLE'
                    )
                    print(
                        "VISIBILITY TEST - NATIVE ISOLATE:",
                        result,
                        "mouse=", event.mouse_region_x, event.mouse_region_y
                    )

            except Exception as e:
                print("VISIBILITY TEST - NATIVE OPERATOR ERROR:", e)

            return {'FINISHED'}

        return {'RUNNING_MODAL'}

class SCULPT_OT_expand_mask_visibility(bpy.types.Operator):
    bl_idname = "sculpt.expand_mask_visibility"
    bl_label = "Mask Visibility"

    action: bpy.props.EnumProperty(
        items=[
            ('HIDE', "Hide Masked", ""),
            ('SHOW_ALL', "Show All", ""),
        ]
    )

    def execute(self, context):
        # Mask visibility buttons always launch the operator directly.
        try:
            if self.action == 'HIDE':
                bpy.ops.paint.hide_show_masked(action='HIDE')
            elif self.action == 'SHOW_ALL':
                bpy.ops.paint.hide_show_all(action='SHOW')
        except Exception as e:
            print("Expand Helper - Mask visibility:", e)
        return {'FINISHED'}

class EXPAND_PT_facesets_visibility_popover(bpy.types.Panel):
    bl_label = "Visibility"
    bl_idname = "EXPAND_PT_facesets_visibility_popover"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_context = 'sculpt'

    def draw(self, context):
        col = self.layout.column(align=True)
        op = col.operator("sculpt.expand_facesets_visibility", text="Hide")
        op.action = 'HIDE'
        op = col.operator("sculpt.expand_facesets_visibility", text="Isolate")
        op.action = 'ISOLATE'
        op = col.operator("sculpt.expand_facesets_visibility", text="Show All")
        op.action = 'SHOW_ALL'

class EXPAND_PT_mask_visibility_popover(bpy.types.Panel):
    bl_label = "Visibility"
    bl_idname = "EXPAND_PT_mask_visibility_popover"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_context = 'sculpt'

    def draw(self, context):
        col = self.layout.column(align=True)
        op = col.operator("sculpt.expand_mask_visibility", text="Hide Masked")
        op.action = 'HIDE'
        op = col.operator("sculpt.expand_mask_visibility", text="Show All")
        op.action = 'SHOW_ALL'

class SCULPT_OT_expand_facesets_snap_execute(bpy.types.Operator):
    bl_idname = "sculpt.expand_facesets_snap_execute"
    bl_label = "Expand Face Sets Snap"

    preserve: bpy.props.BoolProperty(name="Preserve", default=False)
    invert: bpy.props.BoolProperty(name="Invert", default=False)

    def invoke(self, context, event):
        if not setup_internal_events(is_snap=True):
            return {'CANCELLED'}

        return bpy.ops.sculpt.expand(
            'INVOKE_DEFAULT',
            target='FACE_SETS',
            falloff_type='GEODESIC',
            invert=self.invert,
            use_mask_preserve=self.preserve,
            use_reposition_pivot=True,
        )

class TEST_PT_HeaderPopover(bpy.types.Panel):
    bl_label = "Test Panel"
    bl_idname = "TEST_PT_header_popover"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'HEADER'

    def draw(self, context):
        layout = self.layout
        brush = context.tool_settings.sculpt.brush

        if brush is None:
            layout.label(text="No hay brocha activa")
            return

        box = layout.box()
        box.label(text="Texture Browser", icon='TEXTURE')
        box.template_ID_preview(brush, "texture", new="texture.new", rows=3, cols=5)

        tex = brush.texture
        tex_slot = brush.texture_slot

        if tex is None:
            return

        box = layout.box()
        box.prop(tex, "type", text="Type")

        if tex_slot is not None:
            box.prop(tex_slot, "map_mode", text="Mapping")

            row = box.row()
            row.label(text="Offset")
            col = box.column(align=True)
            col.prop(tex_slot, "offset", index=0, text="X")
            col.prop(tex_slot, "offset", index=1, text="Y")
            col.prop(tex_slot, "offset", index=2, text="Z")

            row = box.row()
            row.label(text="Size")
            col = box.column(align=True)
            col.prop(tex_slot, "scale", index=0, text="X")
            col.prop(tex_slot, "scale", index=1, text="Y")
            col.prop(tex_slot, "scale", index=2, text="Z")

def draw_expand_mask_settings(context, layout, tool):
    props = tool.operator_properties("sculpt.expand_mask_execute")
    layout.prop(props, "preserve", text="Preserve")
    layout.prop(props, "invert", text="Invert")
    layout.prop(props, "gradient_falloff", text="Gradient")
    layout.prop(props, "expand_by_normals", text="Normals")

    sub_dist = layout.row(align=True)
    sub_dist.scale_x = 0.8
    sub_dist.prop(props, "texture_distortion", text="Distortion")

    layout.popover(panel="TEST_PT_header_popover", text="Texture", icon='NONE')

    sub_loop = layout.row(align=True)
    sub_loop.scale_x = 0.75
    sub_loop.prop(props, "loop_count", text="Loop")

    # Recursion controls are shown on every non-snap Mask brush,
    # immediately before View.
    sub_step = layout.row(align=True)
    sub_step.scale_x = 0.75
    sub_step.prop(context.scene, "expand_helper_geodesic_step", text="Step")

    sub_tg = layout.row(align=True)
    sub_tg.scale_x = 1.15
    sub_tg.prop(context.scene, "expand_helper_recursion_topology", text="T / G")

    layout.popover(
        panel="EXPAND_PT_mask_visibility_popover",
        text="",
        icon='HIDE_OFF',
    )

def draw_expand_facesets_settings(context, layout, tool):
    props = tool.operator_properties("sculpt.expand_facesets_execute")
    layout.prop(props, "preserve", text="Preserve")
    layout.prop(props, "invert", text="Invert")
    layout.prop(props, "active_faceset", text="Active")

    sub_loop = layout.row(align=True)
    sub_loop.scale_x = 0.75
    sub_loop.prop(props, "loop_count", text="Loop")

    # Recursion controls immediately before View.
    sub_step = layout.row(align=True)
    sub_step.scale_x = 0.75
    sub_step.prop(context.scene, "expand_helper_geodesic_step", text="Step")

    sub_tg = layout.row(align=True)
    sub_tg.scale_x = 1.15
    sub_tg.prop(context.scene, "expand_helper_recursion_topology", text="T / G")

    layout.popover(
        panel="EXPAND_PT_facesets_visibility_popover",
        text="",
        icon='HIDE_OFF',
    )

def draw_snap_settings(context, layout, tool_op_name):
    props = tool.operator_properties(tool_op_name)
    layout.prop(props, "preserve", text="Preserve")
    layout.prop(props, "invert", text="Invert")

class SCULPT_WST_expand_mask_geodesic(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'SCULPT'
    bl_idname = "sculpt.expand_mask_geodesic"
    bl_label = "Expand Mask - Geodesic"
    bl_description = "Expand Mask - Geodesic"
    bl_icon = "brush.sculpt.mask"
    bl_operator = "sculpt.expand_mask_execute"
    bl_keymap = ((
        "sculpt.expand_mask_execute",
        {"type": 'LEFTMOUSE', "value": 'PRESS'},
        {"properties": [("falloff", 'GEODESIC')]},
    ),)

    @staticmethod
    def draw_settings(context, layout, tool):
        draw_expand_mask_settings(context, layout, tool)

class SCULPT_WST_expand_mask_topology(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'SCULPT'
    bl_idname = "sculpt.expand_mask_topology"
    bl_label = "Expand Mask - Topology"
    bl_description = "Expand Mask - Topology"
    bl_icon = "brush.sculpt.mask"
    bl_operator = "sculpt.expand_mask_execute"
    bl_keymap = ((
        "sculpt.expand_mask_execute",
        {"type": 'LEFTMOUSE', "value": 'PRESS'},
        {"properties": [("falloff", 'TOPOLOGY')]},
    ),)

    @staticmethod
    def draw_settings(context, layout, tool):
        draw_expand_mask_settings(context, layout, tool)

class SCULPT_WST_expand_mask_topology_diagonals(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'SCULPT'
    bl_idname = "sculpt.expand_mask_topology_diagonals"
    bl_label = "Expand Mask - Topology Diagonals"
    bl_description = "Expand Mask - Topology Diagonals"
    bl_icon = "brush.sculpt.mask"
    bl_operator = "sculpt.expand_mask_execute"
    bl_keymap = ((
        "sculpt.expand_mask_execute",
        {"type": 'LEFTMOUSE', "value": 'PRESS'},
        {"properties": [("falloff", 'TOPOLOGY_DIAGONALS')]},
    ),)

    @staticmethod
    def draw_settings(context, layout, tool):
        draw_expand_mask_settings(context, layout, tool)

class SCULPT_WST_expand_mask_spherical(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'SCULPT'
    bl_idname = "sculpt.expand_mask_spherical"
    bl_label = "Expand Mask - Spherical"
    bl_description = "Expand Mask - Spherical"
    bl_icon = "brush.sculpt.mask"
    bl_operator = "sculpt.expand_mask_execute"
    bl_keymap = ((
        "sculpt.expand_mask_execute",
        {"type": 'LEFTMOUSE', "value": 'PRESS'},
        {"properties": [("falloff", 'SPHERICAL')]},
    ),)

    @staticmethod
    def draw_settings(context, layout, tool):
        draw_expand_mask_settings(context, layout, tool)

class SCULPT_WST_expand_mask_snap(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'SCULPT'
    bl_idname = "sculpt.expand_mask_snap"
    bl_label = "Snap Mask"
    bl_description = "Snap Mask"
    bl_icon = "brush.sculpt.mask"
    bl_operator = "sculpt.expand_mask_snap_execute"
    bl_keymap = ((
        "sculpt.expand_mask_snap_execute",
        {"type": 'LEFTMOUSE', "value": 'PRESS'},
        {},
    ),)

    @staticmethod
    def draw_settings(context, layout, tool):
        draw_snap_settings(context, layout, "sculpt.expand_mask_snap_execute")

class SCULPT_WST_expand_facesets_geodesic(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'SCULPT'
    bl_idname = "sculpt.expand_facesets_geodesic"
    bl_label = "Expand Face Sets - Geodesic"
    bl_description = "Expand Face Sets - Geodesic"
    bl_icon = "brush.sculpt.draw_face_sets"
    bl_operator = "sculpt.expand_facesets_execute"
    bl_keymap = ((
        "sculpt.expand_facesets_execute",
        {"type": 'LEFTMOUSE', "value": 'PRESS'},
        {"properties": [("falloff", 'GEODESIC')]},
    ),)

    @staticmethod
    def draw_settings(context, layout, tool):
        draw_expand_facesets_settings(context, layout, tool)

class SCULPT_WST_expand_facesets_topology(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'SCULPT'
    bl_idname = "sculpt.expand_facesets_topology"
    bl_label = "Expand Face Sets - Topology"
    bl_description = "Expand Face Sets - Topology"
    bl_icon = "brush.sculpt.draw_face_sets"
    bl_operator = "sculpt.expand_facesets_execute"
    bl_keymap = ((
        "sculpt.expand_facesets_execute",
        {"type": 'LEFTMOUSE', "value": 'PRESS'},
        {"properties": [("falloff", 'TOPOLOGY')]},
    ),)

    @staticmethod
    def draw_settings(context, layout, tool):
        draw_expand_facesets_settings(context, layout, tool)

class SCULPT_WST_expand_facesets_topology_diagonals(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'SCULPT'
    bl_idname = "sculpt.expand_facesets_topology_diagonals"
    bl_label = "Expand Face Sets - Topology Diagonals"
    bl_description = "Expand Face Sets - Topology Diagonals"
    bl_icon = "brush.sculpt.draw_face_sets"
    bl_operator = "sculpt.expand_facesets_execute"
    bl_keymap = ((
        "sculpt.expand_facesets_execute",
        {"type": 'LEFTMOUSE', "value": 'PRESS'},
        {"properties": [("falloff", 'TOPOLOGY_DIAGONALS')]},
    ),)

    @staticmethod
    def draw_settings(context, layout, tool):
        draw_expand_facesets_settings(context, layout, tool)

class SCULPT_WST_expand_facesets_spherical(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'SCULPT'
    bl_idname = "sculpt.expand_facesets_spherical"
    bl_label = "Expand Face Sets - Spherical"
    bl_description = "Expand Face Sets - Spherical"
    bl_icon = "brush.sculpt.draw_face_sets"
    bl_operator = "sculpt.expand_facesets_execute"
    bl_keymap = ((
        "sculpt.expand_facesets_execute",
        {"type": 'LEFTMOUSE', "value": 'PRESS'},
        {"properties": [("falloff", 'SPHERICAL')]},
    ),)

    @staticmethod
    def draw_settings(context, layout, tool):
        draw_expand_facesets_settings(context, layout, tool)

class SCULPT_WST_expand_facesets_snap(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'SCULPT'
    bl_idname = "sculpt.expand_facesets_snap"
    bl_label = "Snap Face Sets"
    bl_description = "Snap Face Sets"
    bl_icon = "brush.sculpt.draw_face_sets"
    bl_operator = "sculpt.expand_facesets_snap_execute"
    bl_keymap = ((
        "sculpt.expand_facesets_snap_execute",
        {"type": 'LEFTMOUSE', "value": 'PRESS'},
        {},
    ),)

    @staticmethod
    def draw_settings(context, layout, tool):
        draw_snap_settings(context, layout, "sculpt.expand_facesets_snap_execute")



# Touchscreen Sculpt toolbar helper
class TOUCHSCREEN_OT_sculpt_expand(bpy.types.Operator):
    bl_idname = "touchscreen.sculpt_expand"
    bl_label = "Expand"
    bl_options = {'REGISTER', 'UNDO'}

    target: bpy.props.EnumProperty(
        name="Target",
        items=[
            ('MASK', "Mask", ""),
            ('FACE_SETS', "Face Sets", ""),
        ],
        default='MASK',
    )

    falloff_type: bpy.props.EnumProperty(
        name="Falloff",
        items=[
            ('GEODESIC', "Geodesic", ""),
            ('TOPOLOGY', "Topology", ""),
            ('TOPOLOGY_DIAGONALS', "Topology Diagonals", ""),
            ('NORMALS', "Normals", ""),
            ('SPHERICAL', "Spherical", ""),
            ('BOUNDARY_TOPOLOGY', "Boundary Topology", ""),
            ('BOUNDARY_FACE_SET', "Boundary Face Set", ""),
            ('ACTIVE_FACE_SET', "Active Face Set", ""),
        ],
        default='GEODESIC',
    )

    invert: bpy.props.BoolProperty(name="Invert", default=False)
    use_mask_preserve: bpy.props.BoolProperty(
        name="Preserve Previous", default=False
    )
    use_falloff_gradient: bpy.props.BoolProperty(
        name="Falloff Gradient", default=False
    )
    use_modify_active: bpy.props.BoolProperty(
        name="Modify Active", default=False
    )
    use_reposition_pivot: bpy.props.BoolProperty(
        name="Reposition Pivot", default=True
    )
    max_geodesic_move_preview: bpy.props.IntProperty(
        name="Geodesic Move",
        default=10000,
        min=0,
    )
    use_auto_mask: bpy.props.BoolProperty(
        name="Auto Create",
        default=False,
    )
    normal_falloff_smooth: bpy.props.IntProperty(
        name="Normal Smooth",
        default=2,
        min=0,
        max=10,
    )

    def invoke(self, context, event):
        try:
            result = bpy.ops.sculpt.expand(
                target=self.target,
                falloff_type=self.falloff_type,
                invert=self.invert,
                use_mask_preserve=self.use_mask_preserve,
                use_falloff_gradient=self.use_falloff_gradient,
                use_modify_active=self.use_modify_active,
                use_reposition_pivot=self.use_reposition_pivot,
                max_geodesic_move_preview=self.max_geodesic_move_preview,
                use_auto_mask=self.use_auto_mask,
                normal_falloff_smooth=self.normal_falloff_smooth,
            )
            return result
        except RuntimeError as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}



CLASSES=(
    TOUCHSCREEN_OT_sculpt_expand,
    SCULPT_OT_expand_mask_execute,
    SCULPT_OT_expand_mask_snap_execute,
    SCULPT_OT_expand_facesets_execute,
    SCULPT_OT_expand_facesets_visibility,
    SCULPT_OT_expand_mask_visibility,
    EXPAND_PT_facesets_visibility_popover,
    EXPAND_PT_mask_visibility_popover,
    SCULPT_OT_expand_facesets_snap_execute,
    TEST_PT_HeaderPopover,
)

# Tool grouping follows the original Expand Helper registration.
# The first Mask tool creates the first nested group; the remaining Mask
# tools are inserted after it. Face Sets then creates a second group
# immediately after the Mask group.
TOOLS=(
    (SCULPT_WST_expand_mask_geodesic, {"builtin.annotate"}, True, True),
    (SCULPT_WST_expand_mask_topology, {SCULPT_WST_expand_mask_geodesic.bl_idname}, False, False),
    (SCULPT_WST_expand_mask_topology_diagonals, {SCULPT_WST_expand_mask_topology.bl_idname}, False, False),
    (SCULPT_WST_expand_mask_spherical, {SCULPT_WST_expand_mask_topology_diagonals.bl_idname}, False, False),
    (SCULPT_WST_expand_mask_snap, {SCULPT_WST_expand_mask_spherical.bl_idname}, False, False),
    (SCULPT_WST_expand_facesets_geodesic, {SCULPT_WST_expand_mask_geodesic.bl_idname}, True, False),
    (SCULPT_WST_expand_facesets_topology, {SCULPT_WST_expand_facesets_geodesic.bl_idname}, False, False),
    (SCULPT_WST_expand_facesets_topology_diagonals, {SCULPT_WST_expand_facesets_topology.bl_idname}, False, False),
    (SCULPT_WST_expand_facesets_spherical, {SCULPT_WST_expand_facesets_topology_diagonals.bl_idname}, False, False),
    (SCULPT_WST_expand_facesets_snap, {SCULPT_WST_expand_facesets_spherical.bl_idname}, False, False),
)

def _register_scene_properties():
    bpy.types.Scene.expand_helper_geodesic_step = bpy.props.IntProperty(
        name="Geodesic Step", default=0, min=0, soft_max=9,
        update=_update_geodesic_step,
    )
    bpy.types.Scene.expand_helper_recursion_topology = bpy.props.BoolProperty(
        name="Topology Recursion", default=False,
    )

def _unregister_scene_properties():
    if hasattr(bpy.types.Scene, "expand_helper_recursion_topology"):
        del bpy.types.Scene.expand_helper_recursion_topology
    if hasattr(bpy.types.Scene, "expand_helper_geodesic_step"):
        del bpy.types.Scene.expand_helper_geodesic_step

def register():
    _hide_native_sculpt_expand_tools()
    _register_scene_properties()

    for cls in CLASSES:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            pass

    try:
        bpy.types.VIEW3D_PT_tools_active.prepend(draw_sculpt_touch_tools)
    except Exception:
        pass

    for tool_cls, after_ids, is_group, separator in TOOLS:
        try:
            bpy.utils.register_tool(
                tool_cls,
                after=after_ids,
                group=is_group,
                separator=separator,
            )
        except Exception as e:
            print(f"Touchscreen - sculpt tool {tool_cls.bl_idname}: {e}")

def unregister():
    cleanup_internal_events()
    _restore_native_sculpt_expand_tools()

    try:
        bpy.types.VIEW3D_PT_tools_active.remove(draw_sculpt_touch_tools)
    except Exception:
        pass

    for tool_cls, _, _, _ in reversed(TOOLS):
        try:
            bpy.utils.unregister_tool(tool_cls)
        except Exception:
            pass

    _unregister_scene_properties()

    for cls in reversed(CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass
