// SPDX-License-Identifier: MIT
//
// Copyright 2025  Algebraic UG (haftungsbeschränkt)
//
// Use of this source code is governed by an MIT-style
// license that can be found in the LICENSE_MIT file or at
// https://opensource.org/licenses/MIT.

use anyhow::Result;
use blended_mpm_api::T;
use nalgebra::Vector3;
use rayon::slice::ParallelSliceMut;

use crate::simulation::particles::Particles;

use super::{PhaseInput, State, profile};

impl State {
    // This is only to optimize memory access.
    pub(super) fn sort(mut self, phase_input: PhaseInput) -> Result<Self> {
        profile!("sort");
        let grid_node_size = phase_input.setup.settings.grid_node_size;

        // Probably many other alternatives exist, e.g. one could do a z-order curve.
        // This seemed to be faster though. Maybe try again with cached keys?
        #[derive(Ord, PartialOrd, PartialEq, Eq)]
        struct SortingPos {
            i: i32,
            j: i32,
            k: i32,
        }

        let to_sorting_pos = |position: &Vector3<T>| SortingPos {
            i: (position.x / grid_node_size - 0.5).floor() as i32,
            j: (position.y / grid_node_size - 0.5).floor() as i32,
            k: (position.z / grid_node_size - 0.5).floor() as i32,
        };

        {
            profile!("simulated particles");

            let mut tmp: Vec<(usize, Vector3<T>)> = {
                profile!("create index-position-pairs");
                self.particles
                    .positions
                    .iter()
                    .cloned()
                    .enumerate()
                    .collect()
            };

            {
                profile!("actual sorting");
                tmp.par_sort_by_key(|(_, position)| to_sorting_pos(position));
            }

            let permutation = {
                profile!("unzip");
                let (permutation, positions): (Vec<_>, Vec<_>) = tmp.into_iter().unzip();
                self.particles.positions = positions;
                permutation
            };

            {
                profile!("apply permutation");
                let Particles {
                    // Already sorted
                    positions: _,

                    // These need to be moved with the particles
                    sort_map,
                    parameters,
                    masses,
                    initial_volumes,
                    position_gradients,
                    velocities,
                    velocity_gradients,
                    collider_insides,

                    // These will be overwritten anyway
                    reverse_sort_map: _,
                    trial_position_gradients: _,
                    elastic_energies: _,
                    action_matrices: _,
                } = &mut self.particles;

                fn permute<T: Clone>(permutation: &[usize], to_permute: &mut Vec<T>) {
                    let lookup = to_permute.clone();
                    assert!(permutation.len() == to_permute.len());
                    for (&prior_position, to_permute) in permutation.iter().zip(to_permute) {
                        *to_permute = lookup[prior_position].clone();
                    }
                }

                permute(&permutation, sort_map);
                permute(&permutation, parameters);
                permute(&permutation, masses);
                permute(&permutation, initial_volumes);
                permute(&permutation, position_gradients);
                permute(&permutation, velocities);
                permute(&permutation, velocity_gradients);
                permute(&permutation, collider_insides);
            }

            {
                profile!("reverse sort map");
                self.particles
                    .reverse_sort_map
                    .resize(self.particles.sort_map.len(), 0);
                for (current, original) in self.particles.sort_map.iter().enumerate() {
                    self.particles.reverse_sort_map[*original] = current;
                }
            }
        }

        {
            profile!("collider");
            for collider in &mut self.collider_objects {
                collider
                    .surface_samples
                    .par_sort_unstable_by_key(|surface_sample| {
                        to_sorting_pos(
                            &collider
                                .kinematic
                                .to_world_position(surface_sample.position),
                        )
                    });
            }
        }
        Ok(self)
    }
}
