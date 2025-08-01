// SPDX-License-Identifier: MIT
//
// Copyright 2025  Algebraic UG (haftungsbeschränkt)
//
// Use of this source code is governed by an MIT-style
// license that can be found in the LICENSE_MIT file or at
// https://opensource.org/licenses/MIT.

use anyhow::Result;
use itertools::izip;
use nalgebra::Vector3;
use rayon::iter::{ParallelBridge, ParallelExtend, ParallelIterator};
use std::{mem::take, sync::mpsc::channel, thread::spawn};

use crate::{
    simulation::state::find_worst_incompatibility,
    weights::{kernel_quadratic_unrolled, position_to_shift_quadratic},
};

use super::{PhaseInput, State, profile};

impl State {
    // Update the hash map that allows to index into all the vectors of each momentum grid
    // with the node's 3d integer position. The data vectors are effectively invalidated.
    pub(super) fn update_momentum_maps(mut self, phase_input: PhaseInput) -> Result<Self> {
        profile!("update_momentum_maps");
        let grid_node_size = phase_input.setup.settings.grid_node_size;

        {
            profile!("prune");
            self.grid_momentums_mut().par_bridge().for_each(|grid| {
                grid.map
                    .retain(|_, idx| !grid.contributors[*idx].get_mut().unwrap().is_empty());
            });
        }

        let (common_map, collider_maps) = {
            profile!("lookup copies");
            let common_map = self.grid_momentum.map.clone();
            let collider_maps = self
                .grid_collider_momentums
                .iter_mut()
                .map(|grid| grid.map.clone())
                .collect::<Vec<_>>();
            (common_map, collider_maps)
        };

        let (senders, collectors): (Vec<_>, Vec<_>) = self
            .grid_collider_momentums
            .iter_mut()
            .map(|grid| {
                let mut map = take(&mut grid.map);
                let (tx, rx) = channel();
                (
                    tx,
                    spawn(move || {
                        while let Ok(grid_idx) = rx.recv() {
                            map.insert(grid_idx, 0);
                        }
                        map
                    }),
                )
            })
            .unzip();

        self.grid_momentum.map.par_extend(
            izip!(
                self.particles.positions.iter(),
                self.particles.collider_insides.iter(),
            )
            .par_bridge()
            .flat_map(|(position, collider_inside)| {
                let shift = position_to_shift_quadratic(position, grid_node_size);
                kernel_quadratic_unrolled!(|grid_idx| {
                    let grid_idx = grid_idx + shift;
                    let incompatibility =
                        self.grid_collider_distances
                            .get(&grid_idx)
                            .and_then(|grid_node| {
                                find_worst_incompatibility(collider_inside, &grid_node.lock())
                            });

                    if let Some(collider_idx) = incompatibility {
                        if !collider_maps[collider_idx].contains_key(&grid_idx) {
                            senders[collider_idx]
                                .send(grid_idx)
                                .expect("collector died");
                        }
                        return None;
                    }

                    (!common_map.contains_key(&grid_idx)).then_some(grid_idx)
                })
            })
            .filter_map(|grid_idx| grid_idx.map(|grid_idx| (grid_idx, 0))),
        );

        {
            profile!("collect");
            drop(senders);
            self.grid_collider_momentums
                .iter_mut()
                .zip(collectors)
                .for_each(|(grid, collector)| grid.map = collector.join().unwrap());
        }

        {
            profile!("re-index");
            for grid in self.grid_momentums_mut() {
                grid.map.values_mut().enumerate().for_each(|(i, e)| *e = i);
            }
        }

        Ok(self)
    }
}
