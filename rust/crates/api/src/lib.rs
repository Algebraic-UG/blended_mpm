// SPDX-License-Identifier: MIT
//
// Copyright 2025  Algebraic UG (haftungsbeschränkt)
//
// Use of this source code is governed by an MIT-style
// license that can be found in the LICENSE_MIT file or at
// https://opensource.org/licenses/MIT.

use std::path::PathBuf;

use anyhow::Result;
use serde::{Deserialize, Serialize};
use serde_json::Value;

#[cfg(test)]
pub type T = f64;
#[cfg(not(test))]
pub type T = f32;

pub trait Context: Send + Sync {
    fn new_simulation(
        &mut self,
        uuid: String,
        cache_dir: PathBuf,
        setup: Value,
        max_bytes_on_disk: u64,
    ) -> Result<()>;
    fn load_simulation(
        &mut self,
        uuid: String,
        cache_dir: PathBuf,
        max_bytes_on_disk: u64,
    ) -> Result<()>;

    fn get_simulation(&self, uuid: &str) -> Result<&dyn Simulation>;
    fn get_simulation_mut(&mut self, uuid: &str) -> Result<&mut dyn Simulation>;
    fn drop_simulation(&mut self, uuid: &str) -> Result<()>;
}

pub trait Simulation {
    fn computing(&self) -> bool;

    fn poll(&mut self) -> Result<Option<Task>>;

    fn start_compute(
        &mut self,
        time_step: T,
        explicit: bool,
        debug_mode: bool,
        next_frame: usize,
        number_of_frames: usize,
        max_bytes_on_disk: u64,
    ) -> Result<()>;
    fn pause_compute(&mut self);

    fn available_frames(&self) -> usize;
    fn available_attributes(&self, frame: usize) -> Result<Vec<Value>>;
    fn fetch_flat_attribute(&self, frame: usize, attribute: Value) -> Result<Vec<T>>;
}

#[derive(Serialize, Deserialize)]
pub struct Task {
    pub name: String,
    pub completed_steps: usize,
    pub steps_to_completion: usize,
    pub sub_tasks: Vec<Task>,
}
