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

from ..magic_consts import (
    BLENDED_MPM_ELASTIC_ENERGY,
    BLENDED_MPM_TRANSFORM,
    BLENDED_MPM_COLLIDER_INSIDE,
    BLENDED_MPM_VELOCITY,
    BLENDED_MPM_DISTANCE,
    BLENDED_MPM_NORMAL,
    BLENDED_MPM_MASS,
    BLENDED_MPM_PRESSURE,
    BLENDED_MPM_INITIAL_VOLUME,
)


def optional_attributes_set_all(optional_attributes, value):
    optional_attributes.grid_collider_distances = value
    optional_attributes.grid_collider_normals = value
    optional_attributes.grid_momentum_masses = value
    optional_attributes.grid_momentum_velocities = value
    optional_attributes.solid_masses = value
    optional_attributes.solid_initial_volumes = value
    optional_attributes.solid_velocities = value
    optional_attributes.solid_transformations = value
    optional_attributes.solid_energies = value
    optional_attributes.solid_collider_insides = value
    optional_attributes.fluid_velocities = value
    optional_attributes.fluid_transformations = value
    optional_attributes.fluid_collider_insides = value
    optional_attributes.fluid_pressures = value
    optional_attributes.collider_normals = value
    optional_attributes.collider_velocities = value


class Blended_MPM_Optional_Attributes(bpy.types.PropertyGroup):
    grid_collider_distances: bpy.props.BoolProperty(
        name="Distance",
        description=f"Attribute name: {BLENDED_MPM_DISTANCE}",
        default=True,
        options=set(),
    )  # type: ignore

    grid_collider_normals: bpy.props.BoolProperty(
        name="Normal",
        description=f"Attribute name: {BLENDED_MPM_NORMAL}",
        default=True,
        options=set(),
    )  # type: ignore

    grid_momentum_masses: bpy.props.BoolProperty(
        name="Masses",
        description=f"Attribute name: {BLENDED_MPM_MASS}",
        default=True,
        options=set(),
    )  # type: ignore

    grid_momentum_velocities: bpy.props.BoolProperty(
        name="Velocities",
        description=f"Attribute name: {BLENDED_MPM_VELOCITY}",
        default=True,
        options=set(),
    )  # type: ignore

    solid_masses: bpy.props.BoolProperty(
        name="Masses",
        description=f"Attribute name: {BLENDED_MPM_MASS}",
        default=False,
        options=set(),
    )  # type: ignore

    solid_initial_volumes: bpy.props.BoolProperty(
        name="Initial Volumes",
        description=f"Attribute name: {BLENDED_MPM_INITIAL_VOLUME}",
        default=False,
        options=set(),
    )  # type: ignore

    solid_velocities: bpy.props.BoolProperty(
        name="Velocites",
        description=f"Attribute name: {BLENDED_MPM_VELOCITY}",
        default=True,
        options=set(),
    )  # type: ignore

    solid_transformations: bpy.props.BoolProperty(
        name="Transformations",
        description=f"Attribute name: {BLENDED_MPM_TRANSFORM}",
        default=True,
        options=set(),
    )  # type: ignore

    solid_energies: bpy.props.BoolProperty(
        name="Energies",
        description=f"Attribute name: {BLENDED_MPM_ELASTIC_ENERGY}",
        default=True,
        options=set(),
    )  # type: ignore

    solid_collider_insides: bpy.props.BoolProperty(
        name="Collider Insides",
        description=f"Attribute name: {BLENDED_MPM_COLLIDER_INSIDE}_X",
        default=True,
        options=set(),
    )  # type: ignore

    fluid_velocities: bpy.props.BoolProperty(
        name="Velocities",
        description=f"Attribute name: {BLENDED_MPM_VELOCITY}",
        default=True,
        options=set(),
    )  # type: ignore

    fluid_transformations: bpy.props.BoolProperty(
        name="Transformations",
        description=f"Attribute name: {BLENDED_MPM_TRANSFORM}",
        default=True,
        options=set(),
    )  # type: ignore

    fluid_collider_insides: bpy.props.BoolProperty(
        name="Collider Insides",
        description=f"Attribute name: {BLENDED_MPM_COLLIDER_INSIDE}_X",
        default=True,
        options=set(),
    )  # type: ignore

    fluid_pressures: bpy.props.BoolProperty(
        name="Pressures",
        description=f"Attribute name: {BLENDED_MPM_PRESSURE}",
        default=True,
        options=set(),
    )  # type: ignore

    collider_normals: bpy.props.BoolProperty(
        name="Normals",
        description=f"Attribute name: {BLENDED_MPM_NORMAL}",
        default=True,
        options=set(),
    )  # type: ignore

    collider_velocities: bpy.props.BoolProperty(
        name="Velocities",
        description=f"Attribute name: {BLENDED_MPM_VELOCITY}",
        default=True,
        options=set(),
    )  # type: ignore
