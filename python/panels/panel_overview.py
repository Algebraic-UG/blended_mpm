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

import json
import os
import uuid
from pathlib import Path

import bpy

from ..bridge import (
    available_frames,
    context_exists,
    drop_context,
    load_simulation,
)
from ..frame_change import sync_simulation
from ..nodes.drivers import update_drivers
from ..popup import popup
from ..progress_update import cleanup_markers
from ..properties.blended_mpm_simulation import Blended_MPM_Simulation
from ..properties.util import get_selected_simulation
from ..util import (
    force_ui_redraw,
    get_simulation_by_uuid,
    get_simulation_idx_by_uuid,
    simulation_cache_exists,
    simulation_cache_locked,
    tutorial_msg,
)


class OBJECT_OT_Blended_MPM_Add_Simulation(bpy.types.Operator):
    bl_idname = "object.blended_mpm_add_simulation"
    bl_label = "Add Simulation"
    bl_description = """Create a new Blended MPM simulation.

There can be multiple simulations at once
and they can share input geometries, but the physics
are completely separate from each other."""
    bl_options = {"REGISTER", "UNDO"}

    simulation: bpy.props.PointerProperty(type=Blended_MPM_Simulation)  # type: ignore

    @classmethod
    def poll(cls, context):
        return (
            not context.scene.blended_mpm_scene.tutorial_active
            or not context.scene.blended_mpm_scene.simulations
        )

    def execute(self, context):
        simulations = context.scene.blended_mpm_scene.simulations

        new_simulation = simulations.add()
        new_simulation.uuid = self.simulation.uuid
        new_simulation.name = self.simulation.name
        new_simulation.cache_directory = self.simulation.cache_directory

        force_ui_redraw()
        return {"FINISHED"}

    def invoke(self, context, _):
        self.simulation.uuid = str(uuid.uuid4())
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.prop(self.simulation, "name")
        self.layout.prop(self.simulation, "cache_directory")
        col = self.layout.column()
        col.enabled = False
        col.prop(self.simulation, "uuid")
        self.layout.prop(self.simulation, "max_giga_bytes_on_disk")
        tutorial_msg(
            self.layout,
            context,
            """\
            You're about to add a new simulation.

            That means you are creating a *cache* directory
            where all the inputs and outputs of
            your simulation are stored!

            You can leave everything as default for now
            and press OK.""",
        )


class OBJECT_OT_Blended_MPM_Reload(bpy.types.Operator):
    bl_idname = "object.blended_mpm_reload"
    bl_label = "Reload"
    bl_description = "Reloads the cache"
    bl_options = {"REGISTER"}

    uuid: bpy.props.StringProperty()  # type: ignore

    def execute(self, context):
        simulation = get_simulation_by_uuid(self.uuid)
        simulation.last_exception = ""
        simulation.loaded_frame = -1
        load_simulation(simulation)
        sync_simulation(simulation, context.scene.frame_current)
        self.report({"INFO"}, "Reloaded simulation.")
        return {"FINISHED"}


class OBJECT_OT_Blended_MPM_Remove_Simulation(bpy.types.Operator):
    bl_idname = "object.blended_mpm_remove_simulation"
    bl_label = "Remove"
    bl_description = """Remove the simulation from the scene.

This does not clear the cache. If you want to delete (not overwrite) the cache,
please use your OS's file browser."""
    bl_options = {"REGISTER"}

    uuid: bpy.props.StringProperty()  # type: ignore

    def execute(self, context):
        simulation = get_simulation_by_uuid(self.uuid)
        idx = get_simulation_idx_by_uuid(self.uuid)
        selected_uuid = get_selected_simulation(context).uuid

        update_drivers(idx)
        cleanup_markers(simulation)
        drop_context(simulation)

        simulations = context.scene.blended_mpm_scene.simulations

        # Note:
        # This actually invalidates the element!
        # It's UB to continue using simulation
        simulations.remove(idx)

        if simulations and self.uuid == selected_uuid:
            context.scene.blended_mpm_scene.selected_simulation = simulations[0].uuid
            self.report({"INFO"}, "Updated simulation selection.")

        self.report({"INFO"}, "Removed simulation")

        return {"FINISHED"}


class OBJECT_OT_Blended_MPM_Remove_Lock_File(bpy.types.Operator):
    bl_idname = "object.blended_mpm_remove_lock_file"
    bl_label = "Remove Lock"
    bl_description = """Use with care!

If the lock file is present, it usually means that another simulation is using this cache.
However, the lock file can remain after a crash, in which case it must be deleted."""
    bl_options = {"REGISTER"}

    uuid: bpy.props.StringProperty()  # type: ignore

    def execute(self, _context):
        simulation = get_simulation_by_uuid(self.uuid)
        lock_file = Path(simulation.cache_directory) / "lock"
        if os.path.exists(lock_file):
            os.remove(lock_file)
            self.report({"INFO"}, "Removed lock file.")
        else:
            self.report({"INFO"}, "No lock file present.")
        return {"FINISHED"}


class OBJECT_OT_Blended_MPM_Show_Message(bpy.types.Operator):
    bl_idname = "object.blended_mpm_show_message"
    bl_label = "Show"

    uuid: bpy.props.StringProperty()  # type: ignore

    def execute(self, _context):
        popup(self.uuid)
        return {"FINISHED"}


class OBJECT_PT_Blended_MPM_Overview(bpy.types.Panel):
    bl_label = "Overview"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Blended MPM"

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"

    def draw(self, context):
        layout = self.layout

        for simulation in context.scene.blended_mpm_scene.simulations:
            (header, body) = layout.panel(
                simulation.uuid, default_closed=not simulation_cache_exists(simulation)
            )
            if simulation.last_exception:
                col = header.column()
                col.alert = True
                col.label(text=f"{simulation.name}: Message")
                header.operator("object.blended_mpm_show_message").uuid = (
                    simulation.uuid
                )
            else:
                progress_text = f"{simulation.name}: "
                factor = 0.0
                if context_exists(simulation):
                    if simulation.progress_json_string:
                        progress = json.loads(simulation.progress_json_string)
                        progress_text += progress["name"]
                        completed_steps = progress["completed_steps"]
                        steps_to_completion = progress["steps_to_completion"]
                        progress_text += f" {completed_steps}/{steps_to_completion}"
                        factor = completed_steps / steps_to_completion
                    else:
                        computed = available_frames(simulation)
                        if computed == simulation.bake_frames:
                            progress_text += "Completed: "
                        else:
                            progress_text += "Paused at: "
                        progress_text += f"{computed}/{simulation.bake_frames}"
                        factor = computed / simulation.bake_frames
                else:
                    if not context_exists(simulation) and simulation_cache_locked(
                        simulation
                    ):
                        progress_text += "Cache Locked!"
                    elif simulation_cache_exists(simulation):
                        progress_text += "Cache Unloaded"
                    else:
                        progress_text += "Uninitialized"
                header.progress(text=progress_text, factor=factor)

            if body is not None:
                body.prop(simulation, "name")
                body.prop(simulation, "cache_directory")
                col = body.column()
                col.enabled = False
                col.prop(simulation, "uuid")
                body.prop(simulation, "max_giga_bytes_on_disk")
                row = body.row()
                if not context_exists(simulation) and simulation_cache_locked(
                    simulation
                ):
                    row.operator(
                        "object.blended_mpm_remove_lock_file", icon="WARNING_LARGE"
                    ).uuid = simulation.uuid
                elif simulation_cache_exists(simulation):
                    tut = row.column()
                    tut.enabled = not context.scene.blended_mpm_scene.tutorial_active
                    tut.operator(
                        "object.blended_mpm_reload", icon="FILE_CACHE"
                    ).uuid = simulation.uuid
                row.operator(
                    "object.blended_mpm_remove_simulation", icon="TRASH"
                ).uuid = simulation.uuid

        tut = layout.column()
        tut.alert = (
            context.scene.blended_mpm_scene.tutorial_active
            and not context.scene.blended_mpm_scene.simulations
        )
        tut.operator("object.blended_mpm_add_simulation", icon="ADD")

        if len(context.scene.blended_mpm_scene.simulations) > 1:
            layout.separator()
            layout.prop(
                context.scene.blended_mpm_scene,
                "selected_simulation",
                text="Select",
            )


classes = [
    OBJECT_OT_Blended_MPM_Add_Simulation,
    OBJECT_OT_Blended_MPM_Reload,
    OBJECT_OT_Blended_MPM_Remove_Simulation,
    OBJECT_OT_Blended_MPM_Remove_Lock_File,
    OBJECT_OT_Blended_MPM_Show_Message,
    OBJECT_PT_Blended_MPM_Overview,
]


def register_panel_overview():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister_panel_overview():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
