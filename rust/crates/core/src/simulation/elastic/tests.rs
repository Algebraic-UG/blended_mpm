// SPDX-License-Identifier: MIT
//
// Copyright 2025  Algebraic UG (haftungsbeschränkt)
//
// Use of this source code is governed by an MIT-style
// license that can be found in the LICENSE_MIT file or at
// https://opensource.org/licenses/MIT.

use nalgebra::Matrix3;

// TODO: this is currently broken
use crate::math::{Matrix9, T, Vector9, safe_inverse::SafeInverse};

use super::{
    double_partial_elastic_energy_inviscid_by_invariant_3,
    double_partial_elastic_energy_neo_hookean_by_invariant_3, elastic_energy_inviscid,
    elastic_energy_inviscid_by_invariant, elastic_energy_neo_hookean,
    elastic_energy_neo_hookean_by_invariants, elastic_energy_stable_neo_hookean,
    first_piola_stress_inviscid, first_piola_stress_neo_hookean,
    first_piola_stress_stable_neo_hookean, hessian_inviscid, hessian_neo_hookean, invariant_2,
    invariant_3, lambda, mu, partial_elastic_energy_inviscid_by_invariant_3,
    partial_elastic_energy_neo_hookean_by_invariant_3, partial_invariant_2_by_position_gradient,
    partial_invariant_3_by_position_gradient,
};

fn test_scalar_from_scalar<Value, Gradient>(
    h: T,
    eps: T,
    value: Value,
    gradient: Gradient,
    sample: T,
) where
    Value: Fn(T) -> T,
    Gradient: Fn(T) -> T,
{
    let mut a = sample;
    let mut b = sample;
    a += h;
    b -= h;
    let a = value(a);
    let b = value(b);
    let finite_difference = (a - b) / h / 2.;

    let analytic_value = gradient(sample);

    if finite_difference.abs() < 1e-10 {
        assert!(analytic_value.abs() < 1e-8);
    } else {
        assert!((finite_difference - analytic_value).abs() / finite_difference.abs() < eps);
    }
}

fn test_scalar_from_matrix<Value, Gradient>(
    h: T,
    eps: T,
    value: Value,
    gradient: Gradient,
    sample: Matrix3<T>,
) where
    Value: Fn(&Matrix3<T>) -> T,
    Gradient: Fn(&Matrix3<T>) -> Matrix3<T>,
{
    let finite_differences = Matrix3::from_iterator((0..sample.len()).map(|i| {
        let mut a = sample;
        let mut b = sample;
        a[i] += h;
        b[i] -= h;
        let a = value(&a);
        let b = value(&b);
        (a - b) / h / 2.
    }));

    let analytic_values = gradient(&sample);

    for (finite_difference, analytic_value) in finite_differences.iter().zip(analytic_values.iter())
    {
        eprintln!(
            "finite_difference: {}, analytic_value: {}, diff: {}",
            finite_difference,
            analytic_value,
            finite_difference - analytic_value
        );
        if finite_difference.abs() < 1e-2 {
            assert!(analytic_value.abs() < 1e-2);
        } else {
            assert!((finite_difference - analytic_value).abs() / finite_difference.abs() < eps);
        }
    }
}

fn test_hessian<Gradient, Hessian>(
    h: T,
    eps: T,
    gradient: Gradient,
    hessian: Hessian,
    sample: Matrix3<T>,
) where
    Gradient: Fn(&Matrix3<T>) -> Vector9<T>,
    Hessian: Fn(&Matrix3<T>) -> Matrix9<T>,
{
    let finite_differences: Matrix9<T> = Matrix9::from_iterator((0..sample.len()).flat_map(|i| {
        let mut a = sample;
        let mut b = sample;
        a[i] += h;
        b[i] -= h;
        let a = gradient(&a);
        let b = gradient(&b);
        ((a - b) / h / 2.).iter().cloned().collect::<Vec<_>>()
    }));

    let analytic_values = hessian(&sample);

    for (finite_difference, analytic_value) in finite_differences.iter().zip(analytic_values.iter())
    {
        eprintln!(
            "finite_difference: {}, analytic_value: {}, diff: {}",
            finite_difference,
            analytic_value,
            finite_difference - analytic_value
        );
        if finite_difference.abs() < 1e-2 {
            assert!(analytic_value.abs() < 1e-2);
        } else {
            assert!((finite_difference - analytic_value).abs() / finite_difference.abs() < eps);
        }
    }
}

fn run_with_random_position_gradients<Test>(n: usize, test: Test)
where
    Test: Fn(Matrix3<T>),
{
    let mut position_gradient = Matrix3::identity();
    test(position_gradient);
    for _ in 0..n {
        loop {
            position_gradient = Matrix3::new_random();
            let d = position_gradient.determinant().abs();
            if d > 1e-1 && d < 1e+1 {
                break;
            }
        }

        if position_gradient.determinant() < 0. {
            position_gradient *= -1.;
        }
        test(position_gradient);
    }
}

fn test_lame_parameters() -> impl Iterator<Item = [T; 2]> {
    [[10000., 0.3], [1000000., 0.3], [10000., 0.], [0., 0.4]]
        .into_iter()
        .map(|[youngs_modulus, poissons_ratio]| {
            [
                mu(youngs_modulus, poissons_ratio),
                lambda(youngs_modulus, poissons_ratio),
            ]
        })
}

fn test_inviscid_parameters() -> impl Iterator<Item = (T, i32)> {
    [(100., 2), (1000., 2), (100., 7), (1000., 7)].into_iter()
}

#[test]
fn test_partial_invariant_2_by_position_gradient() {
    let h = 1e-5;
    let eps = 1e-3;
    run_with_random_position_gradients(1000, |position_gradient| {
        test_scalar_from_matrix(
            h,
            eps,
            invariant_2,
            partial_invariant_2_by_position_gradient,
            position_gradient,
        )
    });
}

#[test]
fn test_partial_invariant_3_by_position_gradient() {
    let h = 1e-5;
    let eps = 1e-3;
    run_with_random_position_gradients(1000, |position_gradient| {
        test_scalar_from_matrix(
            h,
            eps,
            invariant_3,
            partial_invariant_3_by_position_gradient,
            position_gradient,
        )
    });
}

#[test]
fn test_first_piola_stress_neo_hookean() {
    let h = 1e-8;
    let eps = 1e-1;

    for [mu, lambda] in test_lame_parameters() {
        run_with_random_position_gradients(1000, |position_gradient| {
            if position_gradient.safe_inverse().is_none() {
                return;
            }
            test_scalar_from_matrix(
                h,
                eps,
                |position_gradient| elastic_energy_neo_hookean(mu, lambda, position_gradient),
                |position_gradient| first_piola_stress_neo_hookean(mu, lambda, position_gradient),
                position_gradient,
            );
        })
    }
}

#[test]
fn test_first_piola_stress_stable_neo_hookean() {
    let h = 1e-8;
    let eps = 1e-1;

    for [mu, lambda] in test_lame_parameters() {
        run_with_random_position_gradients(1000, |position_gradient| {
            test_scalar_from_matrix(
                h,
                eps,
                |position_gradient| {
                    elastic_energy_stable_neo_hookean(mu, lambda, position_gradient)
                },
                |position_gradient| {
                    first_piola_stress_stable_neo_hookean(mu, lambda, position_gradient)
                },
                position_gradient,
            );
        })
    }
}

#[test]
fn test_partial_elastic_energy_neo_hookean_by_invariant_3() {
    let h = 1e-8;
    let eps = 1e-3;

    for [mu, lambda] in test_lame_parameters() {
        run_with_random_position_gradients(1000, |position_gradient| {
            test_scalar_from_scalar(
                h,
                eps,
                |invariant_3| {
                    elastic_energy_neo_hookean_by_invariants(
                        mu,
                        lambda,
                        invariant_2(&position_gradient),
                        invariant_3,
                    )
                },
                |invariant_3| {
                    partial_elastic_energy_neo_hookean_by_invariant_3(mu, lambda, invariant_3)
                },
                invariant_3(&position_gradient),
            );
        })
    }
}

#[test]
fn test_double_partial_elastic_energy_neo_hookean_by_invariant_3() {
    let h = 1e-8;
    let eps = 1e-3;

    for [mu, lambda] in test_lame_parameters() {
        run_with_random_position_gradients(1000, |position_gradient| {
            test_scalar_from_scalar(
                h,
                eps,
                |invariant_3| {
                    partial_elastic_energy_neo_hookean_by_invariant_3(mu, lambda, invariant_3)
                },
                |invariant_3| {
                    double_partial_elastic_energy_neo_hookean_by_invariant_3(
                        mu,
                        lambda,
                        invariant_3,
                    )
                },
                invariant_3(&position_gradient),
            );
        })
    }
}

#[test]
fn test_hessian_neo_hookean() {
    let h = 1e-8;
    let eps = 1e-2;

    for [mu, lambda] in test_lame_parameters() {
        run_with_random_position_gradients(1000, |position_gradient| {
            test_hessian(
                h,
                eps,
                |invariant_3| {
                    Vector9::from_iterator(
                        first_piola_stress_neo_hookean(mu, lambda, invariant_3)
                            .iter()
                            .cloned(),
                    )
                },
                |invariant_3| hessian_neo_hookean(mu, lambda, &position_gradient),
                position_gradient,
            );
        })
    }
}

#[test]
fn test_partial_elastic_energy_inviscid_by_invariant_3() {
    let h = 1e-8;
    let eps = 1e-3;

    for (bulk_modulus, exponent) in test_inviscid_parameters() {
        run_with_random_position_gradients(1000, |position_gradient| {
            test_scalar_from_scalar(
                h,
                eps,
                |invariant_3| {
                    elastic_energy_inviscid_by_invariant(bulk_modulus, exponent, invariant_3)
                },
                |invariant_3| {
                    partial_elastic_energy_inviscid_by_invariant_3(
                        bulk_modulus,
                        exponent,
                        invariant_3,
                    )
                },
                invariant_3(&position_gradient),
            );
        })
    }
}

#[test]
fn test_first_piola_stress_inviscid() {
    let h = 1e-8;
    let eps = 1e-1;

    for (bulk_modulus, exponent) in test_inviscid_parameters() {
        run_with_random_position_gradients(1000, |position_gradient| {
            test_scalar_from_matrix(
                h,
                eps,
                |position_gradient| {
                    elastic_energy_inviscid(bulk_modulus, exponent, position_gradient)
                },
                |position_gradient| {
                    first_piola_stress_inviscid(bulk_modulus, exponent, position_gradient)
                },
                position_gradient,
            );
        })
    }
}

#[test]
fn test_double_partial_elastic_energy_inviscid_by_invariant_3() {
    let h = 1e-8;
    let eps = 1e-3;

    for (bulk_modulus, exponent) in test_inviscid_parameters() {
        run_with_random_position_gradients(1000, |position_gradient| {
            test_scalar_from_scalar(
                h,
                eps,
                |invariant_3| {
                    partial_elastic_energy_inviscid_by_invariant_3(
                        bulk_modulus,
                        exponent,
                        invariant_3,
                    )
                },
                |invariant_3| {
                    double_partial_elastic_energy_inviscid_by_invariant_3(
                        bulk_modulus,
                        exponent,
                        invariant_3,
                    )
                },
                invariant_3(&position_gradient),
            );
        })
    }
}

#[test]
fn test_hessian_inviscid() {
    let h = 1e-8;
    let eps = 1e-2;

    for (bulk_modulus, exponent) in test_inviscid_parameters() {
        run_with_random_position_gradients(1000, |position_gradient| {
            test_hessian(
                h,
                eps,
                |invariant_3| {
                    Vector9::from_iterator(
                        first_piola_stress_inviscid(bulk_modulus, exponent, invariant_3)
                            .iter()
                            .cloned(),
                    )
                },
                |invariant_3| hessian_inviscid(bulk_modulus, exponent, &position_gradient),
                position_gradient,
            );
        })
    }
}
