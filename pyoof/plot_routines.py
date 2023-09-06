#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Author: Tomas Cassanelli
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from mpl_toolkits.axes_grid1 import make_axes_locatable
from scipy import interpolate
from astropy.table import Table
from astropy import units as apu
import warnings
import os
import yaml
from .aperture import radiation_pattern, phase
from .aux_functions import uv_ratio
from .math_functions import norm

__all__ = [
    'plot_beam', 'plot_beam_data', 'plot_phase', 'plot_phase_data',
    'plot_variance', 'plot_fit_path', "plot_beam_data_multifrequency", "plot_phase_difference"
    ]


# TODO: Generalize this functions for multiple d_z
def plot_beam(
    I_coeff, K_coeff, d_z, wavel, illum_func, telgeo, resolution, box_factor,
    plim, angle, title
        ):
    """
    Beam maps, :math:`P_\\mathrm{norm}(u, v)`, figure given fixed
    ``I_coeff`` coefficients and ``K_coeff`` set of coefficients. It is the
    straight forward result from a least squares minimization
    (`~pyoof.fit_zpoly`). There will be three maps, for three radial offsets,
    :math:`d_z^-`, :math:`0` and :math:`d_z^+` (in meters).

    Parameters
    ----------
    I_coeff : `list`
        List which contains 4 parameters, the illumination amplitude,
        :math:`A_{E_\\mathrm{a}}`, the illumination taper,
        :math:`c_\\mathrm{dB}` and the two coordinate offset, :math:`(x_0,
        y_0)`. The illumination coefficients must be listed as follows,
        ``I_coeff = [i_amp, c_dB, x0, y0]``.
    K_coeff : `~numpy.ndarray`
        Constants coefficients, :math:`K_{n\\ell}`, for each of them there is
        only one Zernike circle polynomial, :math:`U^\\ell_n(\\varrho,
        \\varphi)`.
    d_z : `~astropy.units.quantity.Quantity`
        Radial offset :math:`d_z`, added to the sub-reflector in length units.
        This characteristic measurement adds the classical interference
        pattern to the beam maps, normalized squared (field) radiation
        pattern, which is an out-of-focus property. The radial offset list
        must be as follows, ``d_z = [d_z-, 0., d_z+]`` all of them in length
        units.
    wavel : `~astropy.units.quantity.Quantity`
        Wavelength, :math:`\\lambda`, of the observation in length units.
    illum_func : `function`
        Illumination function, :math:`E_\\mathrm{a}(x, y)`, to be evaluated
        with the key ``I_coeff``. The illumination functions available are
        `~pyoof.aperture.illum_pedestal` and `~pyoof.aperture.illum_gauss`.
    telgeo : `list`
        List that contains the blockage distribution, optical path difference
        (OPD) function, and the primary radius (`float`) in meters. The list
        must have the following order, ``telego = [block_dist, opd_func, pr]``.
    resolution : `int`
        Fast Fourier Transform resolution for a rectangular grid. The input
        value has to be greater or equal to the telescope resolution and with
        power of 2 for faster FFT processing. It is recommended a value higher
        than ``resolution = 2 ** 8``.
    box_factor : `int`
        Related to the FFT resolution (**resolution** key), defines the image
        pixel size level. It depends on the primary radius, ``pr``, of the
        telescope, e.g. a ``box_factor = 5`` returns ``x = np.linspace(-5 *
        pr, 5 * pr, resolution)``, an array to be used in the FFT2
        (`~numpy.fft.fft2`).
    plim : `~astropy.units.quantity.Quantity`
        Contains the maximum values for the :math:`u` and :math:`v`
        wave-vectors in angle units. The `~astropy.units.quantity.Quantity`
        must be in the following order, ``plim = [umin, umax, vmin, vmax]``.
    angle : `~astropy.units.quantity.Quantity` or `str`
        Angle unit. Power pattern axes.
    title : `str`
        Figure title.

    Returns
    -------
    fig : `~matplotlib.figure.Figure`
        The three beam maps plotted from the input parameters. Each map with a
        different offset :math:`d_z` value. From left to right, :math:`d_z^-`,
        :math:`0` and :math:`d_z^+`.
    """
    power_norm = np.zeros((d_z.size, resolution, resolution), dtype=np.float64)
    u = np.zeros((d_z.size, resolution), dtype=np.float64) << apu.rad
    v = np.zeros((d_z.size, resolution), dtype=np.float64) << apu.rad
    n_maps = len(d_z)
    for k, _d_z in enumerate(d_z):

        u[k, :], v[k, :], F = radiation_pattern(
            K_coeff=K_coeff,
            I_coeff=I_coeff,
            d_z=_d_z,
            wavel=wavel,
            illum_func=illum_func,
            telgeo=telgeo,
            resolution=resolution,
            box_factor=box_factor
            )

        power_norm[k, ...] = norm(np.abs(F) ** 2)

    # Limits, they need to be transformed to degrees
    if plim is None:
        pr = telgeo[2]                          # primary reflector radius
        bw = 1.22 * apu.rad * wavel / (2 * pr)  # Beamwidth radians
        s_bw = bw * 8                           # size-beamwidth ratio radians

        # Finding central point for shifted maps
        uu, vv = np.meshgrid(u[1, :], v[1, :])
        print(uu[power_norm[1, ...] == power_norm[1, ...].max()][0])
        u_offset = uu[power_norm[1, ...] == power_norm[1, ...].max()][0]
        v_offset = vv[power_norm[1, ...] == power_norm[1, ...].max()][0]

        plim = [
            (-s_bw + u_offset).to_value(apu.rad),
            (s_bw + u_offset).to_value(apu.rad),
            (-s_bw + v_offset).to_value(apu.rad),
            (s_bw + v_offset).to_value(apu.rad)
            ] * apu.rad
    plim = plim.to_value(angle)
    plim_u, plim_v = plim[:2], plim[2:]

    subtitle = [
        '$P_{\\textrm{\\scriptsize{norm}}}(u,v)$ $d_z=' +
        str(round(d_z[i].to_value(apu.cm), 3)) + '$ cm' for i in range(n_maps)
        ]

    fig = plt.figure(figsize=uv_ratio(plim_u, plim_v), constrained_layout=True)
    gs = GridSpec(
        nrows=2,
        ncols=n_maps,
        figure=fig,
        )


    ax = [plt.subplot(gs[i]) for i in range(2*n_maps)]

    #for i in range(n_maps):
    #    ax[i].set_yticklabels([])

    cax = [ax[i + n_maps] for i in range(n_maps)]

    for i in range(n_maps):
        vmin, vmax = power_norm[i, ...].min(), power_norm[i, ...].max()

        extent = [
            u[i, :].to_value(angle).min(), u[i, :].to_value(angle).max(),
            v[i, :].to_value(angle).min(), v[i, :].to_value(angle).max()
            ]
        levels = np.linspace(vmin, vmax, 10)

        im = ax[i].imshow(
            X=power_norm[i, ...],
            extent=extent,
            vmin=vmin,
            vmax=vmax
            )

        ax[i].contour(
            u[i, :].to_value(angle),
            v[i, :].to_value(angle),
            power_norm[i, ...],
            levels=levels,
            colors='k',
            linewidths=0.4
            )

        ax[i].set_title(subtitle[i])
        ax[i].set_xlabel(f'$u$ {angle}')
        ax[i].set_ylabel(f'$v$ {angle}')
        # limits don't work with astropy units
        ax[i].set_ylim(*plim_v)
        ax[i].set_xlim(*plim_u)
        ax[i].grid(False)

        plt.colorbar(
            im, cax=cax[i], orientation='horizontal', use_gridspec=True
            )
        cax[i].set_xlabel('Amplitude [arb]')
        cax[i].set_yticklabels([])
        cax[i].yaxis.set_ticks_position('none')
    fig.suptitle(title)
    # fig.tight_layout()

    return fig

def plot_beam_data_multifrequency(data, resolution, angle, title, res_mode):
    figs = []

    for key in data:
        if key != "pthto":      
            u_data = data[key]["u_data"]
            v_data = data[key]["v_data"]
            beam_data = data[key]["beam_data"]
            d_z = data[key]["d_z"]
            wavel = data[key]["wavel"]
            fig = plot_beam_data(u_data, v_data, beam_data, d_z, resolution, angle, title + " wavel: {}".format(wavel), res_mode)
            figs.append(fig)

    return figs

def plot_beam_data(
    u_data, v_data, beam_data, d_z, resolution, angle, title, res_mode
        ):
    """
    Real data beam maps, :math:`P^\\mathrm{obs}(x, y)`, figures given
    given 3 out-of-focus radial offsets, :math:`d_z`.

    Parameters
    ----------
    u_data : `list`
        :math:`x` axis value for the 3 beam maps in radians. The values have
        to be flatten, in one dimension, and stacked in the same order as the
        ``d_z = [d_z-, 0., d_z+]`` values from each beam map.
    v_data : `list`
        :math:`y` axis value for the 3 beam maps in radians. The values have
        to be flatten, one dimensional, and stacked in the same order as the
        ``d_z = [d_z-, 0., d_z+]`` values from each beam map.
    beam_data : `~numpy.ndarray`
        Amplitude value for the beam map in mJy. The values have to be
        flatten, one dimensional, and stacked in the same order as the ``d_z =
        [d_z-, 0., d_z+]`` values from each beam map. If ``res_mode = False``,
        the beam map will be normalized.
    resolution : `int`
        Fast Fourier Transform resolution for a rectangular grid. The input
        value has to be greater or equal to the telescope resolution and with
        power of 2 for faster FFT processing. It is recommended a value higher
        than ``resolution = 2 ** 8``.
    d_z : `~astropy.units.quantity.Quantity`
        Radial offset :math:`d_z`, added to the sub-reflector in meters. This
        characteristic measurement adds the classical interference pattern to
        the beam maps, normalized squared (field) radiation pattern, which is
        an out-of-focus property. The radial offset list must be as follows,
        ``d_z = [d_z-, 0., d_z+]`` all of them in length units.
    angle : `~astropy.units.quantity.Quantity` or `str`
        Angle unit. Power pattern axes.
    title : `str`
        Figure title.
    res_mode : `bool`
        If `True` the beam map will not be normalized. This feature is used
        to compare the residual outputs from the least squares minimization
        (`~pyoof.fit_zpoly`).

    Returns
    -------
    fig : `~matplotlib.figure.Figure`
        Figure from the three observed beam maps. Each map with a different
        offset :math:`d_z` value. From left to right, :math:`d_z^-`, :math:`0`
        and :math:`d_z^+`.
    """
    n_maps = len(d_z)
    if not res_mode:
        # Power pattern normalization
        beam_data = norm(beam_data, axis=1)

    subtitle = [
        '$P_{\\textrm{\\scriptsize{norm}}}(u,v)$ $d_z=' +
        str(round(d_z[i].to_value(apu.cm), 3)) + '$ cm' for i in range(n_maps)
        ]
    fig = plt.figure(
        figsize=uv_ratio(u_data, v_data),
        constrained_layout=True
        )

    gs = GridSpec(
        nrows=2,
        ncols=n_maps,
        figure=fig,
        )

    ax = [plt.subplot(gs[i]) for i in range(n_maps*2)]
    for i in range(n_maps):
        ax[i].set_yticklabels([])

    cax = [ax[i + n_maps] for i in range(n_maps)]

    for i in range(n_maps):
        # new grid for beam_data
        u_ng = np.linspace(
            u_data[i, :].to(angle).min(),
            u_data[i, :].to(angle).max(),
            resolution
            )
        v_ng = np.linspace(
            v_data[i, :].to(angle).min(),
            v_data[i, :].to(angle).max(),
            resolution
            )
        beam_ng = interpolate.griddata(
            # coordinates of grid points to interpolate from.
            points=(u_data[i, :].to(angle), v_data[i, :].to(angle)),
            values=beam_data[i, :],
            # coordinates of grid points to interpolate to.
            xi=tuple(np.meshgrid(u_ng, v_ng)),
            method='cubic'
            )

        vmin, vmax = beam_ng.min(), beam_ng.max()
        levels = np.linspace(vmin, vmax, 10)
        extent = [
            u_ng.to_value(angle).min(), u_ng.to_value(angle).max(),
            v_ng.to_value(angle).min(), v_ng.to_value(angle).max()
            ]

        im = ax[i].imshow(X=beam_ng, extent=extent, vmin=vmin, vmax=vmax)
        ax[i].contour(
            u_ng.to_value(angle),
            v_ng.to_value(angle),
            beam_ng,
            levels=levels,
            colors='k',
            linewidths=0.4
            )

        ax[i].set_xlabel(f'$u$ {angle}')
        ax[i].set_title(subtitle[i])
        ax[i].grid(False)

        plt.colorbar(
            im, cax=cax[i], orientation='horizontal', use_gridspec=True
            )
        cax[i].set_xlabel('Amplitude [arb]')
        cax[i].set_yticklabels([])
        cax[i].yaxis.set_ticks_position('none')

    fig.suptitle(title)

    return fig

def plot_phase_difference(K1, K2, pr, piston, tilt, title, wavel):
    if (not tilt) and (not piston):
        cbartitle = ' '.join((
            '$\\varphi_{\\scriptsize{\\textrm{no-piston, no-tilt}}}(x,y)$',
            'amplitude rad'
            ))
    elif (not tilt) and piston:
        cbartitle = (
            '$\\varphi_{\\scriptsize{\\textrm{no-tilt}}}(x,y)$ amplitude rad'
            )
    elif tilt and (not piston):
        cbartitle = (
            '$\\varphi_{\\scriptsize{\\textrm{no-piston}}}(x,y)$ amplitude rad'
            )
    else:
        cbartitle = '$\\varphi(x, y)$ amplitude rad'

    extent = [-pr.to_value(apu.m), pr.to_value(apu.m)] * 2
    _x1, _y1, _phase1 = phase(K_coeff=K1, pr=pr, tilt=tilt, piston=piston, wavel=wavel)
    _x2, _y2, _phase2 = phase(K_coeff=K2, pr=pr, tilt=tilt, piston=piston, wavel=wavel)
    print(_phase1)
    print(_phase2)
    _phase = _phase2-_phase1
    levels = np.arange(floor(_phase.min().value), ceil(_phase.max().value), 0.2)  # radians
    #levels = np.linspace(floor(_phase.min().value), ceil(_phase.max().value), 10)
    fig, ax = plt.subplots(figsize=(6, 5.8))

    im = ax.imshow(X=_phase.to_value(apu.rad), extent=extent)

    # Partial solution for contour Warning
    with warnings.catch_warnings():
        countour = ax.contour(
            _x1.to_value(apu.m),
            _y1.to_value(apu.m),
            _phase.to_value(apu.rad),
            levels=levels,
            colors=["white"],
            alpha=0,
            )

    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="3%", pad=0.03)
    cb = fig.colorbar(im, cax=cax)
    cb.ax.set_ylabel(cbartitle)
    plt.clabel(countour, inline=True, fontsize=15, colors = "white")

    ax.set_title(title)
    ax.set_ylabel('$y$ m')
    ax.set_xlabel('$x$ m')
    ax.grid(False)

    #fig.tight_layout()

    return fig, _phase

from pyoof.aperture import phase
import matplotlib.pyplot as plt
import warnings
from mpl_toolkits.axes_grid1 import make_axes_locatable
from math import ceil, floor

def plot_phase(K_coeff, pr, piston, tilt, title, wavel):
    """
    Aperture phase distribution (phase-error), :math:`\\varphi(x, y)`, figure,
    given the Zernike circle polynomial coefficients, ``K_coeff``, solution
    from the least squares minimization.

    Parameters
    ----------
    K_coeff : `~numpy.ndarray`
        Constants coefficients, :math:`K_{n\\ell}`, for each of them there is
        only one Zernike circle polynomial, :math:`U^\\ell_n(\\varrho,
        \\varphi)`.
    pr : `float`
        Primary reflector radius in length units.
    piston : `bool`
        Boolean to include or exclude the piston coefficient in the aperture
        phase distribution. The Zernike circle polynomials are related to
        piston through :math:`U^{0}_0(\\varrho, \\varphi)`.
    tilt : `bool`
        Boolean to include or exclude the tilt coefficients in the aperture
        phase distribution. The Zernike circle polynomials are related to tilt
        through :math:`U^{-1}_1(\\varrho, \\varphi)` and
        :math:`U^1_1(\\varrho, \\varphi)`.
    title : `str`
        Figure title.

    Returns
    -------
    fig : `~matplotlib.figure.Figure`
        Aperture phase distribution parametrized in terms of the Zernike
        circle polynomials, and represented for the telescope's primary
        reflector.
    """

    if (not tilt) and (not piston):
        cbartitle = ' '.join((
            '$\\varphi_{\\scriptsize{\\textrm{no-piston, no-tilt}}}(x,y)$',
            'amplitude rad'
            ))
    elif (not tilt) and piston:
        cbartitle = (
            '$\\varphi_{\\scriptsize{\\textrm{no-tilt}}}(x,y)$ amplitude rad'
            )
    elif tilt and (not piston):
        cbartitle = (
            '$\\varphi_{\\scriptsize{\\textrm{no-piston}}}(x,y)$ amplitude rad'
            )
    else:
        cbartitle = '$\\varphi(x, y)$ amplitude rad'
    
    extent = [-pr.to_value(apu.m), pr.to_value(apu.m)] * 2
    _x, _y, _phase = phase(K_coeff=K_coeff, pr=pr, tilt=tilt, piston=piston, wavel = wavel)
    levels = np.arange(floor(_phase.min().value), ceil(_phase.max().value), 0.2)  # radians
    #levels = np.linspace(floor(_phase.min().value), ceil(_phase.max().value), 4)
    fig, ax = plt.subplots(figsize=(6, 5.8))
    im = ax.imshow(X=_phase.to_value(apu.rad), extent=extent)
    # Partial solution for contour Warning
    #with warnings.catch_warnings():
    #    warnings.simplefilter("ignore")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        countour = ax.contour(
                _x.to_value(apu.m),
                _y.to_value(apu.m),
                _phase.to_value(apu.rad),
                levels=levels,
                colors=["white"],
                alpha=0,
                )
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="3%", pad=0.03)
    cb = fig.colorbar(im, cax=cax)
    cb.ax.set_ylabel(cbartitle)
    plt.clabel(countour, inline=True, fontsize=15, colors = "white")
    ax.set_title(title)
    ax.set_ylabel('$y$ m')
    ax.set_xlabel('$x$ m')
    ax.grid(False)

    #fig.tight_layout()

    return fig


def plot_phase_data(phase_data, pr, title):
    """
    Aperture phase distribution (phase-error), :math:`\\varphi(x, y)`, figure.
    The plot is made by giving the phase_data in radians and the primary
    reflector in length units. Notice that if the tilt term is not required
    this has to be removed manually from the ``phase_data`` array.

    Parameters
    ----------
    phase_data : `astropy.units.quantity.Quantity`
        Aperture phase distribution data in angle or radian units.
    pr : `astropy.units.quantity.Quantity`
        Primary reflector radius in length units.
    title : `str`
        Figure title.

    Returns
    -------
    fig : `~matplotlib.figure.Figure`
        Aperture phase distribution represented for the telescope's primary
        reflector.
    """
    _x = np.linspace(-pr, pr, phase_data.shape[0])
    _y = np.linspace(-pr, pr, phase_data.shape[0])

    extent = [-pr.to_value(apu.m), pr.to_value(apu.m)] * 2
    levels = np.linspace(-2, 2, 9)  # radians

    fig, ax = plt.subplots(figsize=(6, 5.8))

    im = ax.imshow(X=phase_data.to_value(apu.rad), extent=extent)

    # Partial solution for contour Warning
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ax.contour(
            _x.to_value(apu.m),
            _y.to_value(apu.m),
            phase_data.to_value(apu.rad),
            levels=levels,
            colors='k',
            alpha=0.3
            )

    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="3%", pad=0.03)
    cb = fig.colorbar(im, cax=cax)
    cbartitle = '$\\varphi(x, y)$ amplitude rad'
    cb.ax.set_ylabel(cbartitle)

    ax.set_title(title)
    ax.set_ylabel('$y$ m')
    ax.set_xlabel('$x$ m')
    ax.grid(False)

    #fig.tight_layout()

    return fig


def plot_variance(matrix, order, diag, cbtitle, title):
    """
    Variance-Covariance matrix or Correlation matrix figure. It returns
    the triangle figure with a color amplitude value for each element. Used to
    check/compare the correlation between the fitted parameters in a least
    squares minimization.

    Parameters
    ----------
    matrix : `~numpy.ndarray`
        Two dimensional array containing the Variance-Covariance or
        Correlation function. Output from the fit procedure.
    order : `int`
        Order used for the Zernike circle polynomial, :math:`n`.
    diag : `bool`
        If `True` it will plot the matrix diagonal.
    cbtitle : `str`
        Color bar title.
    title : `str`
        Figure title.

    Returns
    -------
    fig : `~matplotlib.figure.Figure`
        Triangle figure representing Variance-Covariance or Correlation matrix.
    """
    n = order
    N_K_coeff = (n + 1) * (n + 2) // 2
    ln = [(j, i) for i in range(0, n + 1) for j in range(-i, i + 1, 2)]
    L = np.array(ln)[:, 0]
    N = np.array(ln)[:, 1]

    params_names = [
        '$A_{E_\\mathrm{a}}$', '$c_\\mathrm{dB}$', 'q', '$x_0$', '$y_0$'
        ]
    for i in range(N_K_coeff):
        params_names.append(
            ''.join(('$K_{', f'{N[i]}', '\\,', f'{L[i]}', '}$'))
            )
    params_names = np.array(params_names)
    params_used = [int(i) for i in matrix[:1][0]]
    _matrix = matrix[1:]

    x_ticks, y_ticks = _matrix.shape

    extent = [0, x_ticks, 0, y_ticks]

    if diag:
        k = -1
        # idx represents the ignored elements
        labels_x = params_names[params_used]
        labels_y = labels_x[::-1]
    else:
        k = 0
        # idx represents the ignored elements
        labels_x = params_names[params_used][:-1]
        labels_y = labels_x[::-1][:-1]

    # selecting half covariance
    mask = np.tri(_matrix.shape[0], k=k)
    matrix_mask = np.ma.array(_matrix, mask=mask).T
    # mask out the lower triangle

    fig, ax = plt.subplots()

    # get rid of the frame
    for spine in plt.gca().spines.values():
        spine.set_visible(False)

    im = ax.imshow(
        X=matrix_mask,
        extent=extent,
        vmax=_matrix.max(),
        vmin=_matrix.min(),
        cmap=plt.cm.Reds,
        interpolation='nearest',
        origin='upper'
        )

    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="3%", pad=0.03)
    cb = fig.colorbar(im, cax=cax)
    cb.formatter.set_powerlimits((0, 0))
    cb.ax.yaxis.set_offset_position('left')
    cb.update_ticks()
    cb.ax.set_ylabel(cbtitle)

    ax.set_title(title)
    ax.set_xticks(np.arange(x_ticks) + 0.5)
    ax.set_xticklabels(labels_x, rotation='vertical')
    ax.set_yticks(np.arange(y_ticks) + 0.5)
    ax.set_yticklabels(labels_y)
    ax.grid(False)

    #fig.tight_layout()

    return fig
#def plot_fit_path_multifreq(path_pyoof_out, order, illum_func, telgeo, angle='deg', plim=None,
#    save=False):

def plot_fit_path(
    path_pyoof_out, order, illum_func, telgeo,wavel,  angle='deg', plim=None,
    save=False, i=0
        ):
    """
    Plot all important figures after a least squares minimization.
    TODO: Change all information to be read from the pyoof_out directory.

    Parameters
    ----------
    path_pyoof_out : `str`
        Path to the pyoof output, ``'pyoof_out/directory'``.
    order : `int`
        Order used for the Zernike circle polynomial, :math:`n`.
    illum_func : `function`
        Illumination function, :math:`E_\\mathrm{a}(x, y)`, to be evaluated
        with the key ``I_coeff``. The illumination functions available are
        `~pyoof.aperture.illum_pedestal` and `~pyoof.aperture.illum_gauss`.
    telgeo : `list`
        List that contains the blockage distribution, optical path difference
        (OPD) function, and the primary radius (`float`) in meters. The list
        must have the following order, ``telego = [block_dist, opd_func, pr]``.
    angle : `~astropy.units.quantity.Quantity` or `str`
        Angle unit. Power pattern axes.
    plim : `~astropy.units.quantity.Quantity`
        Contains the maximum values for the :math:`u` and :math:`v`
        wave-vectors in angle units. The `~astropy.units.quantity.Quantity`
        must be in the following order, ``plim = [umin, umax, vmin, vmax]``.
    save : `bool`
        If `True`, it stores all plots in the ``'pyoof_out/directory'``
        directory.

    Returns
    -------
    fig_beam : `~matplotlib.figure.Figure`
        The three beam maps plotted from the input parameters. Each map with a
        different offset :math:`d_z` value. From left to right, :math:`d_z^-`,
        :math:`0` and :math:`d_z^+`.
    fig_phase : `~matplotlib.figure.Figure`
        Aperture phase distribution for the Zernike circle polynomials for the
        telescope primary reflector.
    fig_res : `~matplotlib.figure.Figure`
        Figure from the three observed beam maps residual. Each map with a
        different offset :math:`d_z` value. From left to right, :math:`d_z^-`,
        :math:`0` and :math:`d_z^+`.
    fig_data : `~matplotlib.figure.Figure`
        Figure from the three observed beam maps. Each map with a different
        offset :math:`d_z` value. From left to right, :math:`d_z^-`, :math:`0`
        and :math:`d_z^+`.
    fig_cov : `~matplotlib.figure.Figure`
        Triangle figure representing Variance-Covariance matrix.
    fig_corr : `~matplotlib.figure.Figure`
        Triangle figure representing Correlation matrix.
    """

    try:
        path_pyoof_out
    except NameError:
        print(f'pyoof directory does not exist: {path_pyoof_out}')
    else:
        pass

    path_plot = os.path.join(path_pyoof_out, 'plots')
    print(path_plot)
    if not os.path.exists(path_plot):
        os.makedirs(path_plot)

    # Reading least squares minimization output
    n = order
    params = Table.read(
        os.path.join(path_pyoof_out, f'fitpar_n{n}.csv'), format='ascii'
        )

    with open(os.path.join(path_pyoof_out, 'pyoof_info.yml'), 'r') as infile:
        pyoof_info = yaml.load(infile, Loader=yaml.Loader)

    obs_object = pyoof_info['obs_object']
    meanel = round(pyoof_info['meanel'], 2)
    resolution = pyoof_info['fft_resolution']
    box_factor = pyoof_info['box_factor']

    # Beam and residual
    beam_data = np.genfromtxt(os.path.join(path_pyoof_out, f'beam_data_{wavel}.csv'))
    res = np.genfromtxt(os.path.join(path_pyoof_out, f'res_n{n}_{wavel}.csv'))
    u_data = np.genfromtxt(
        os.path.join(path_pyoof_out, f'u_data_{wavel}.csv')) * apu.rad
    v_data = np.genfromtxt(
        os.path.join(path_pyoof_out, f'v_data_{wavel}.csv')) * apu.rad
    d_z = np.array(pyoof_info['d_z']) * apu.m
    pr = pyoof_info['pr'] * apu.m

    K_coeff = params['parfit'][5:]*apu.m
    #for u_data, v_data, beam_data in zip(u_data_array, v_data_array,beam_data_array):
    # Covariance and Correlation matrix
    cov = np.genfromtxt(os.path.join(path_pyoof_out, f'cov_n{n}_{wavel}.csv'))
    corr = np.genfromtxt(os.path.join(path_pyoof_out, f'corr_n{n}_{wavel}.csv'))
    wavel = pyoof_info['wavel'] * apu.m

    if n == 1:
        fig_data = plot_beam_data(
            u_data=u_data,
            v_data=v_data,
            beam_data=beam_data,
            d_z=d_z,
            resolution=resolution,
            title='observed power pattern',
            angle=angle,
            res_mode=False
            )

    fig_beam = plot_beam(
        I_coeff=params['parfit'][:5],
        K_coeff=K_coeff,
        title='fit power patter',
        d_z=d_z,
        wavel=wavel,
        illum_func=illum_func,
        telgeo=telgeo,
        plim=plim,
        angle=angle,
        resolution=resolution,
        box_factor=box_factor
        )

    fig_phase = plot_phase(
        K_coeff=K_coeff,
        title='phase-error',
        pr=pr,
        piston=False,
        tilt=False,
        wavel = wavel
        )
    fig_res = plot_beam_data(
        u_data=u_data,
        v_data=v_data,
        beam_data=res,
        d_z=d_z,
        resolution=resolution,
        title='residual',
        angle=angle,
        res_mode=True
        )

    if save:
        fig_beam.savefig(os.path.join(path_plot, f'fitbeam_n{n}_{i}.png'))
        fig_phase.savefig(os.path.join(path_plot, f'fitphase_n{n}_{i}.png'))
        fig_res.savefig(os.path.join(path_plot, f'residual_n{n}_{i}.png'))
#       fig_cov.savefig(os.path.join(path_plot, f'cov_n{n}_{i}.png'))
#        fig_corr.savefig(os.path.join(path_plot, f'corr_n{n}_{i}.png'))

        if n == 1:
            fig_data.savefig(os.path.join(path_plot, f'obsbeam_{i}.png'))

            """
    fig_cov = plot_variance(
        matrix=cov,
        order=n,
        title='variance-covariance matrix',
        cbtitle='sigma',
        diag=True,
        )

    fig_corr = plot_variance(
        matrix=corr,
        order=n,
        title='correlation matrix',
        cbtitle='rho',
        diag=True,
        )
"""
