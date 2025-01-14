#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Author: Tomas Cassanelli
import numpy as np
import matplotlib.pyplot as plt
from astropy import units as u
import pyoof

# Initial fits file configuration
n = 5                                       # initial order
N_K_coeff = (n + 1) * (n + 2) // 2          # total number of polynomials
c_dB = -14.5 * u.dB                         # illumination taper
I_coeff = [1, c_dB, 2, 0 * u.m, 0 * u.m]    # illumination coefficients
K_coeff = np.array([0.1] * N_K_coeff)       # random Zernike circle coeff.
wavel = 0.0093685143125 * u.m               # wavelenght
d_z = [-2.2, 0, 2.2] * u.cm                 # radial offset

# Making example for the Effelsberg telescope
effelsberg_telescope = [
    pyoof.telgeometry.block_effelsberg(alpha=10 * u.deg),
    pyoof.telgeometry.opd_effelsberg,       # OPD function
    50. * u.m,                              # primary reflector radius
    'effelsberg'                            # telescope name
    ]

# simulte data
pyoof.simulate_data_pyoof(
    I_coeff=I_coeff,
    K_coeff=K_coeff,
    wavel=wavel,
    d_z=d_z,
    illum_func=pyoof.aperture.illum_parabolic,
    telgeo=effelsberg_telescope[:-1],
    noise=0,
    resolution=2 ** 8,
    box_factor=5,
    work_dir=None
    )

data_info, data_obs = pyoof.extract_data_pyoof('data_generated/test000.fits')
[name, pthto, obs_object, obs_date, freq, wavel, d_z, meanel] = data_info
[beam_data, u_data, v_data] = data_obs

# print('beam_data.shape', beam_data.shape)
# print('u_data.shape', u_data.shape)
# print('v_data.shape', v_data.shape)

fig = pyoof.plot_beam_data(
    u_data=u_data,
    v_data=v_data,
    beam_data=beam_data,
    d_z=d_z,
    angle=u.deg,
    title='test000',
    resolution=2 ** 8,
    res_mode=False
    )

plt.show()