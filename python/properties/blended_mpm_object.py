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

from ..magic_consts import OUTPUT_TYPES

from .blended_mpm_object_attributes import Blended_MPM_Optional_Attributes
from .blended_mpm_object_settings import Blended_MPM_Object_Settings


class Blended_MPM_Object(bpy.types.PropertyGroup):
    simulation_specific_settings: bpy.props.CollectionProperty(
        type=Blended_MPM_Object_Settings,
        name="Settings per Simulation",
        description="For each simulation an input can have different meanings.",
        options=set(),
    )  # type: ignore
    input_name: bpy.props.StringProperty(
        name="Original Input Name",
        description="Referenced for retrieving outputs.",
        options=set(),
    )  # type: ignore
    simulation_uuid: bpy.props.StringProperty(
        name="Simulation UUID",
        description="The UUID of the simulation driving this",
        options=set(),
    )  # type: ignore
    output_type: bpy.props.StringProperty(
        name="Output Type",
        description=f"""Depending on this, different outputs are synchronizable.
Has to be one of:
{", ".join(OUTPUT_TYPES)}""",
        options=set(),
    )  # type: ignore
    optional_attributes: bpy.props.PointerProperty(
        type=Blended_MPM_Optional_Attributes,
        name="Optional Attributes",
        description="Further customization of what outputs are synchronized.",
        options=set(),
    )  # type: ignore

    sync_once: bpy.props.BoolProperty(
        name="Sync Once",
        description="Instead of continously synchronizing, load only a specific frame.",
        default=False,
    )  # type: ignore
    sync_once_frame: bpy.props.IntProperty(
        name="Sync Once Frame",
        description="""Simulation frame to synchronize on.

Only used if 'Sync Once' is active.
When the outputs of a simulation are synchronized on a different frame,
this object is left untouched.""",
        default=0,
    )  # type: ignore
