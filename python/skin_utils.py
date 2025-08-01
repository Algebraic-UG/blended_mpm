# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of the Blended MPM extension.
# Copyright (C) 2025  Algebraic UG (haftungsbeschränkt)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import bpy
import numpy as np

from .magic_consts import (
    BLENDED_MPM_BREAKING_FRAME,
    FLUID_PARTICLES,
    SOLID_PARTICLES,
    BLENDED_MPM_TRANSFORM,
    BLENDED_MPM_REFERENCE_INDEX,
    BLENDED_MPM_REFERENCE_OFFSET,
)

from .nodes.geometry_nodes_move_with_reference import (
    create_geometry_nodes_move_with_reference,
)
from .nodes.geometry_nodes_store_reference import create_geometry_nodes_store_reference
from .nodes.geometry_nodes_store_breaking_frame import (
    create_geometry_nodes_store_breaking_frame,
)
from .nodes.geometry_nodes_remove_broken import create_geometry_nodes_remove_broken


def selectable_particle_objects(_, _context):
    return [
        (obj.name, obj.name, "")
        for obj in bpy.data.objects
        if (
            obj.blended_mpm_object.output_type == SOLID_PARTICLES
            or obj.blended_mpm_object.output_type == FLUID_PARTICLES
        )
    ]


class OBJECT_OT_Blended_MPM_Move_With_Particles(bpy.types.Operator):
    bl_idname = "object.blended_mpm_move_with_particles"
    bl_label = "Blended MPM Move with Particles"
    bl_description = f"""Use a Blended MPM particle output to animate this mesh.

This adds the point attributes {BLENDED_MPM_REFERENCE_INDEX} and {BLENDED_MPM_REFERENCE_OFFSET}.

This happens in two steps:
1. "Blended MPM Store Reference" is applied.
2. "Blended MPM Move With Reference" is attached.

Note that the references are calculated in the current configuration.
In most cases, this should be done while displaying the initial frame."""
    bl_options = {"REGISTER", "UNDO"}

    particle_obj: bpy.props.EnumProperty(
        items=selectable_particle_objects,
        name="Driving Particle Object",
        description=f"""You can only select active particle output objects.
The object should have the {BLENDED_MPM_TRANSFORM} attribute.""",
        options=set(),
    )  # type: ignore

    @classmethod
    def poll(cls, context):
        return (
            context.active_object is not None
            and context.active_object.select_get()
            and not context.active_object.blended_mpm_object.simulation_uuid
        )

    def execute(self, context):
        obj = context.active_object

        modifier = obj.modifiers.new("Blended MPM Temporary", type="NODES")
        modifier.node_group = create_geometry_nodes_store_reference()
        modifier["Socket_2"] = bpy.data.objects[self.particle_obj]
        bpy.ops.object.modifier_apply(modifier=modifier.name)

        modifier = obj.modifiers.new("Blended MPM Default", type="NODES")
        modifier.node_group = create_geometry_nodes_move_with_reference()
        modifier["Socket_2"] = bpy.data.objects[self.particle_obj]
        modifier["Socket_3"] = 3

        self.report(
            {"INFO"},
            message=f"{obj.name} is now moving with {self.particle_obj}",
        )
        return {"FINISHED"}

    def invoke(self, context, _event):
        return context.window_manager.invoke_props_dialog(self)


class OBJECT_OT_Blended_MPM_Break_Edges(bpy.types.Operator):
    bl_idname = "object.blended_mpm_break_edges"
    bl_label = "Blended MPM Break Edges"
    bl_description = f"""Avoid unnatural stretching of mesh that is moving with particles.

This adds the edge attribute {BLENDED_MPM_BREAKING_FRAME}.

This happens in two steps:
1. "Blended MPM Store Breaking Farme" is applied.
2. "Blended MPM Remove Broken" is attached.

Note that this operation steps through the given frame range.
That means it can be quite slow, depending on the complexity of the scene.
"""
    bl_options = {"REGISTER", "UNDO"}

    particle_obj: bpy.props.EnumProperty(
        items=selectable_particle_objects,
        name="Driving Particle Object",
        description="This should match the particle object that is moving the mesh.",
        options=set(),
    )  # type: ignore
    dilation_threshold: bpy.props.FloatProperty(
        name="Dilation Threshold",
        description="The first frame in which an edge exceeds this threshold is stored.",
        default=4,
    )  # type: ignore
    num_colliders: bpy.props.IntProperty(
        name="Num Colliders",
        description="""For colliders #0 to #NumColliders:
The first frame in which referenced particles are on opposite sides of a collider is store.

This is useful for cases where the mesh is cut by colliders
but the but dilation threshold isn't violated.""",
        default=0,
    )  # type: ignore
    start_frame: bpy.props.IntProperty(
        name="Start Frame",
        description="Check for breaking edges starting with this frame.",
        default=1,
    )  # type: ignore
    end_frame: bpy.props.IntProperty(
        name="End Frame",
        description="Check for breaking edges ending with this frame (inclusively).",
        default=250,
    )  # type: ignore

    @classmethod
    def poll(cls, context):
        return (
            context.active_object is not None
            and context.active_object.select_get()
            and not context.active_object.blended_mpm_object.simulation_uuid
        )

    def execute(self, context):
        obj = context.active_object

        array = np.full(shape=(len(obj.data.edges)), fill_value=1e8, dtype="int32")
        if BLENDED_MPM_BREAKING_FRAME in obj.data.attributes:
            obj.data.attributes.remove(obj.data.attributes[BLENDED_MPM_BREAKING_FRAME])
        attr = obj.data.attributes.new(
            BLENDED_MPM_BREAKING_FRAME, type="INT", domain="EDGE"
        )
        attr.data.foreach_set("value", array)

        node_group = create_geometry_nodes_store_breaking_frame()

        for frame in range(self.start_frame, self.end_frame + 1):
            context.scene.frame_set(frame)
            bpy.context.view_layer.update()

            print(f"Checking for edge breakage in frame {frame}")

            modifier = obj.modifiers.new("Blended MPM Temporary", type="NODES")
            modifier.node_group = node_group
            modifier["Socket_2"] = self.num_colliders
            modifier["Socket_3"] = bpy.data.objects[self.particle_obj]
            modifier["Socket_4"] = self.dilation_threshold
            bpy.ops.object.modifier_apply(modifier=modifier.name)

        modifier = obj.modifiers.new("Blended MPM Default", type="NODES")
        modifier.node_group = create_geometry_nodes_remove_broken()

        self.report(
            {"INFO"},
            message=f"{obj.name} stored if and when edges break",
        )
        return {"FINISHED"}

    def invoke(self, context, _event):
        return context.window_manager.invoke_props_dialog(self)


classes = [
    OBJECT_OT_Blended_MPM_Move_With_Particles,
    OBJECT_OT_Blended_MPM_Break_Edges,
]


def menu_func_move_with_particles(self, _context):
    self.layout.operator(
        OBJECT_OT_Blended_MPM_Move_With_Particles.bl_idname, icon="MODIFIER"
    )


def menu_func_break_edges(self, _context):
    self.layout.operator(OBJECT_OT_Blended_MPM_Break_Edges.bl_idname, icon="MODIFIER")


menu_funcs = [menu_func_move_with_particles, menu_func_break_edges]


def register_skin_utils():
    for cls in classes:
        bpy.utils.register_class(cls)
    for menu_func in menu_funcs:
        bpy.types.VIEW3D_MT_object.append(menu_func)


def unregister_skin_utils():
    for menu_func in menu_funcs:
        bpy.types.VIEW3D_MT_object.remove(menu_func)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
