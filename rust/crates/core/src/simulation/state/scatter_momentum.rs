// SPDX-License-Identifier: MIT
//
// Copyright 2025  Algebraic UG (haftungsbeschränkt)
//
// Use of this source code is governed by an MIT-style
// license that can be found in the LICENSE_MIT file or at
// https://opensource.org/licenses/MIT.

use std::mem::take;

use anyhow::Result;
use blended_mpm_api::T;
use itertools::izip;
use nalgebra::Vector3;
use rayon::iter::{ParallelBridge, ParallelIterator};

use crate::{
    simulation::{
        elastic::{first_piola_stress_inviscid, first_piola_stress_neo_hookean},
        particles::ParticleParameters,
    },
    weights::kernel_quadratic,
};

use super::{PhaseInput, State, profile};

impl State {
    // Mass and velocity transported by particles is scattered to the grids.
    // In explicit time integration the forces can be applied at the same time.
    pub(super) fn scatter_momentum<const EXPLICIT_FORCES: bool>(
        mut self,
        phase_input: PhaseInput,
    ) -> Result<Self> {
        profile!("scatter_momentum");
        let grid_node_size = phase_input.setup.settings.grid_node_size;
        let scaling = phase_input.time_step * 4. / grid_node_size.powi(2);

        // Take memory to satisfy the borrow checker, return at the end
        let mut grids = self.grid_momentums_mut().map(take).collect::<Vec<_>>();
        for grid in &mut grids {
            grid.masses = vec![0.; grid.map.len()];
            grid.velocities = vec![Vector3::zeros(); grid.map.len()];
            izip!(
                grid.map.keys(),
                grid.contributors.iter_mut(),
                grid.masses.iter_mut(),
                grid.velocities.iter_mut(),
            )
            .par_bridge()
            .for_each(|(grid_idx, contributors, mass, velocity)| {
                for &particle_idx in contributors.get_mut().unwrap().iter() {
                    let normalized = self.particles.positions[particle_idx] / grid_node_size;

                    let to_grid_node_normalized = grid_idx.map(|x| x as T) - normalized;
                    let weight = to_grid_node_normalized.map(kernel_quadratic).product();

                    let to_grid_node = to_grid_node_normalized * grid_node_size;

                    let mut imparted_momentum = (self.particles.velocities[particle_idx]
                        + self.particles.velocity_gradients[particle_idx] * to_grid_node)
                        * self.particles.masses[particle_idx];

                    if EXPLICIT_FORCES {
                        let position_gradient = &self.particles.position_gradients[particle_idx];
                        let stress = match self.particles.parameters[particle_idx] {
                            ParticleParameters::Solid { mu, lambda } => {
                                first_piola_stress_neo_hookean(mu, lambda, position_gradient)
                            }
                            ParticleParameters::Fluid {
                                exponent,
                                bulk_modulus,
                            } => first_piola_stress_inviscid(
                                bulk_modulus,
                                exponent,
                                position_gradient,
                            ),
                        };
                        imparted_momentum -= stress
                            * (position_gradient.transpose()
                                * (to_grid_node
                                    * (scaling * self.particles.initial_volumes[particle_idx])));
                    }

                    imparted_momentum *= weight;

                    *mass += weight * self.particles.masses[particle_idx];
                    *velocity += imparted_momentum;
                }

                if *mass > 0. {
                    *velocity /= *mass;
                } else {
                    // Numerical edge case
                    *velocity = Vector3::zeros();
                }
            });
        }
        self.grid_momentums_mut()
            .zip(grids)
            .for_each(|(old, new)| *old = new);
        Ok(self)
    }
}
