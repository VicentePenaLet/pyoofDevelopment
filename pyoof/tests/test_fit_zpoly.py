#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Author: Tomas Cassanelli
import pytest
import os
import yaml
import numpy as np
from astropy import units as apu
from astropy.utils.data import get_pkg_data_filename
from astropy.table import Table
from numpy.testing import assert_allclose
import pyoof


# initial configuration params same as the config_params.yml file
config_params_pyoof = get_pkg_data_filename('../data/config_params.yml')
with open(config_params_pyoof, 'r') as yaml_config:
    config_params = yaml.load(yaml_config, Loader=yaml.Loader)

n = 5                                           # initial order
N_K_coeff = (n + 1) * (n + 2) // 2              # total numb. polynomials
wavel = 0.00862712109352518 * apu.m
plus_minus = (2.6 * wavel).to_value(apu.cm)
d_z = [-plus_minus, 0, plus_minus] * apu.cm

# illumination parameters
i_amp = np.random.uniform(.001, 1.1)
c_dB = np.random.uniform(-21, -10) * apu.dB
q = np.random.uniform(1, 2)
x0 = np.random.uniform(-1, 1) * apu.cm
y0 = np.random.uniform(-1, 1) * apu.cm

K_coeff = np.random.uniform(-.06, .06, N_K_coeff)
I_coeff = [i_amp, c_dB, q, x0, y0]

I_coeff_dimensionless = [
    I_coeff[0], I_coeff[1].to_value(apu.dB), I_coeff[2],
    I_coeff[3].to_value(apu.m), I_coeff[4].to_value(apu.m)
    ]
params = np.hstack((I_coeff_dimensionless, K_coeff))

idx_exclude = config_params['excluded']
params_true = pyoof.params_complete(
    params=np.delete(params, idx_exclude),
    N_K_coeff=N_K_coeff,
    config_params=config_params
    )

K_coeff_true = params_true[5:]
I_coeff_true_dimensionless = params_true[:5]
I_coeff_true = [
    params_true[0], params_true[1] * apu.dB, params_true[2],
    params_true[3] * apu.m, params_true[4] * apu.m
    ]

noise_level = 0                                # noise added to gen data

effelsberg_telescope = [
    pyoof.telgeometry.block_effelsberg(alpha=10 * apu.deg),  # blockage
    pyoof.telgeometry.opd_effelsberg,           # OPD function
    50. * apu.m,                                # primary reflector radius m
    'effelsberg'                                # telescope name
    ]

illum_func = pyoof.aperture.illum_parabolic

# Generating temp file with pyoof fits and pyoof_out
@pytest.fixture()
def oof_work_dir(tmpdir_factory):

    tdir = str(tmpdir_factory.mktemp('pyoof'))

    pyoof.simulate_data_pyoof(
        K_coeff=K_coeff_true,
        I_coeff=I_coeff_true,
        wavel=wavel,
        d_z=d_z,
        telgeo=effelsberg_telescope[:-1],
        illum_func=illum_func,
        noise=noise_level,
        resolution=2 ** 9,
        box_factor=6.5,
        work_dir=tdir
        )

    print('temp directory: ', tdir)

    # Reading the generated data
    pathfits = os.path.join(tdir, 'data_generated', 'test000.fits')
    data_info, data_obs = pyoof.extract_data_pyoof(pathfits)

    pyoof.fit_zpoly(
        data_info=data_info,
        data_obs=data_obs,
        order_max=n,
        illum_func=illum_func,
        telescope=effelsberg_telescope,
        fit_previous=True,
        resolution=2 ** 8,
        box_factor=5,
        config_params_file=None,
        make_plots=False,
        verbose=0,
        work_dir=tdir
        )

    return tdir


def test_fit_beam(oof_work_dir):

    # To see if we are in the right temp directory
    print('temp directory: ', os.listdir(oof_work_dir))

    # lets compare the params from the last order
    fit_pars = os.path.join(
        oof_work_dir, 'pyoof_out', 'test000-000', f'fitpar_n{n}.csv'
        )

    params = Table.read(fit_pars, format='ascii')['parfit']
    assert_allclose(params[5:], K_coeff_true, rtol=1e-1, atol=1e-1)
    assert_allclose(params[:5], I_coeff_true_dimensionless, rtol=1e-1, atol=1)