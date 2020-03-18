#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Author: Tomas Cassanelli
import time
import numpy as np
from astropy import units as apu
from astropy.table import QTable
from astropy.utils.data import get_pkg_data_filename
from scipy import interpolate, optimize
from ..aperture import phase

__all__ = ['EffelsbergActuator']

path_lookup = get_pkg_data_filename('../data/lookup_effelsberg.txt')


class EffelsbergActuator():
    """
    Several tasks for the Effelsberg telescope and the active surface control
    system located in the 6.5 m sub-reflector. The purpose of all these
    functions is to transform the phase-error maps obtained from the core
    `~pyoof` routines, to an equivalent actuator perpendicular displacement to
    correct those effects seen in the main phase-error maps.

    Parameters
    ----------
    wavel : `~astropy.units.quantity.Quantity`
        Wavelength, :math:`\\lambda`, of the observation in meters.
    nrot : `int`
        This is a required rotation to apply to the phase maps (obtained
        from `~pyoof.fit_zpoly`) to get the right orientation of the active
        surface lookup table in the active surface control system.
    sign : `int`
        It is the value of the phase-error amplitude as seen from the active
        surface, same as ``nrot`` is a convention for the Effelsberg telescope.
    resolution : `int`
        Resolution for the phase-error map, usually used ``resolution = 1000``
        in the `~pyoof` package.
    path_lookup : `str`
        Path for the current look up table that controls the active surface
        with the Finite Element Method (FEM) model.
    """

    def __init__(
        self, wavel, nrot=3, sign=-1, order=5, sr=3.25 * apu.m, pr=50 * apu.m,
        resolution=1000, path_lookup=path_lookup
            ):
        self.wavel = wavel
        self.nrot = nrot
        self.sign = sign
        self.sr = sr
        self.pr = pr
        self.n = order
        self.N_K_coeff = (self.n + 1) * (self.n + 2) // 2
        self.resolution = resolution
        self.path_lookup = path_lookup

        self.alpha_lookup, self.actuator_sr_lookup = self.read_lookup()
        self.phase_pr_lookup = self.transform(self.actuator_sr_lookup)

    def read_lookup(self):
        """
        Simple reader for the Effelsberg active surface look-up table.

        Returns
        -------
        alpha_lookup : `~astropy.units.quantity.Quantity`
            List of angles from the look-up table.
        actuator_sr_lookup : `~astropy.units.quantity.Quantity`
            Actuators surface perpendicular displacement as seen from the
            sub-reflector in the standard grid format from `~pyoof`.
        """

        alpha_lookup = [7, 10, 20, 30, 32, 40, 50, 60, 70, 80, 90] * apu.deg
        names = [
            'NR', 'N', 'ffff'
            ] + alpha_lookup.value.astype(int).astype(str).tolist()

        lookup_table = QTable.read(
            self.path_lookup, names=names, format='ascii'
            )

        for n in names[3:]:
            lookup_table[n] = lookup_table[n] * apu.um

        # Generating the mesh from technical drawings
        theta = np.linspace(7.5, 360 - 7.5, 24) * apu.deg
        R = np.array([3250, 2600, 1880, 1210]) * apu.mm

        # Actuator positions
        act_x = np.outer(R, np.cos(theta)).reshape(-1)
        act_y = np.outer(R, np.sin(theta)).reshape(-1)

        # Generating new grid same as pyoof output
        x_ng = np.linspace(-self.sr, self.sr, self.resolution)
        y_ng = x_ng.copy()
        xx, yy = np.meshgrid(x_ng, y_ng)
        circ = [(xx ** 2 + yy ** 2) >= (self.sr) ** 2]

        # actuators displacement in the new grid
        actuator_sr_lookup = np.zeros(
            shape=(alpha_lookup.size, self.resolution, self.resolution)
            ) << apu.um

        for j, _alpha in enumerate(names[3:]):
            actuator_sr_lookup[j, :, :] = interpolate.griddata(
                # coordinates of grid points to interpolate from
                points=(act_x.to_value(apu.m), act_y.to_value(apu.m)),
                values=lookup_table[_alpha].to_value(apu.um),
                # coordinates of grid points to interpolate to
                xi=tuple(
                    np.meshgrid(x_ng.to_value(apu.m), y_ng.to_value(apu.m))
                    ),
                method='cubic'
                ) * apu.um
            actuator_sr_lookup = np.nan_to_num(actuator_sr_lookup)
            actuator_sr_lookup[j, :, :][tuple(circ)] = 0

        return alpha_lookup, actuator_sr_lookup

    def grav_deformation_model(self, G, alpha):
        """
        Simple decomposition of the telescope elastic structure and
        gravitational force into a gravitational deformation model. The model
        takes into account only the elevation angle and not azimuth (since it
        cancels out).

        Parameters
        ----------
        G : `~np.ndarray` or `list`
            It has the list of three gravitational/elastic coefficients to
            supply the model.
        alpha : `~astropy.units.quantity.Quantity`
            Single angle related to the three ``G`` coefficients.

        Returns
        -------
        K : `float`
            Single Zernike circle polynomial coefficient related to a single
            elevation angle ``alpha``.
        """

        if type(alpha) == apu.Quantity:
            alpha = alpha.to_value(apu.rad)

        K = G[0] * np.sin(alpha) + G[1] * np.cos(alpha) + G[2]

        return K

    def transform(self, actuator_sr):
        """
        Transformation required to get from the actuators displacement in the
        sub-reflector to the phase-error map in the primary dish.

        Parameters
        ----------
        actuator_sr : `~astropy.units.quantity.Quantity`
            Two dimensional array, in the `~pyoof` format, for the actuators
            displacement in the sub-reflector. It must have shape
            ``(alpha.size, resolution, resolution)``

        Returns
        -------
        phase_pr : `~astropy.units.quantity.Quantity`
            Phase-error map for the primary dish. It must have shape
            ``(alpha.size, resolution, resolution)``.
        """
        factor = self.sign * 4 * np.pi * apu.rad / self.wavel

        phase_pr = (
            factor * np.rot90(m=actuator_sr, axes=(1, 2), k=self.nrot)
            ).to(apu.rad)

        return phase_pr

    def itransform(self, phase_pr):
        """
        Inverse transformation for
        `~pyoof.actuator.EffeslbergActuator.transform`.

        Parameters
        ----------
        phase_pr : `~astropy.units.quantity.Quantity`
            Phase-error map for the primary dish. It must have shape
            ``(alpha.size, resolution, resolution)``.

        Returns
        -------
        actuator_sr : `~astropy.units.quantity.Quantity`
            Two dimensional array, in the `~pyoof` format, for the actuators
            displacement in the sub-reflector. It must have shape
            ``(alpha.size, resolution, resolution)``
        """

        factor = self.wavel / (self.sign * 4 * np.pi * apu.rad)

        actuator_sr = np.rot90(
            m=(phase_pr * factor).to(apu.um),
            axes=(1, 2),
            k=-self.nrot
            )

        return actuator_sr

    def write_lookup(self, fname, actuator_sr):
        """
        Easy writer for the active surface standard formatting at the
        Effelsberg telescope. The writer admits the actuator sub-reflector
        perpendicular displacement in the same shape as the `~pyoof` format,
        then it grids the data to the active surface look-up format.

        Parameters
        ----------
        fname : `str`
            String to the name and path for the look-up table to be stored.
        actuator_sr : `~astropy.units.quantity.Quantity`
            Two dimensional array, in the `~pyoof` format, for the actuators
            displacement in the sub-reflector. It must have shape
            ``(alpha.size, resolution, resolution)``
        """

        # Generating the mesh from technical drawings
        theta = np.linspace(7.5, 360 - 7.5, 24) * apu.deg

        # slightly different at the edge
        R = np.array([3245, 2600, 1880, 1210]) * apu.mm

        # Actuator positions
        act_x = np.outer(R, np.cos(theta)).reshape(-1)
        act_y = np.outer(R, np.sin(theta)).reshape(-1)

        # Generating new grid same as pyoof output
        x = np.linspace(-self.sr, self.sr, self.resolution)
        y = x.copy()

        lookup_table = np.zeros((11, 96))
        for j in range(11):

            intrp = interpolate.RegularGridInterpolator(
                points=(x.to_value(apu.mm), y.to_value(apu.mm)),
                values=actuator_sr.to_value(apu.um)[j, :, :].T,
                method='linear'
                )

            lookup_table[j, :] = intrp(np.array([act_x, act_y]).T)

        # writing the file row per row
        with open(fname, 'w') as file:
            for k in range(96):
                row = np.around(
                    lookup_table[:, k], 0).astype(np.int).astype(str)
                print(row)
                file.write(f'NR {k + 1} ffff ' + '  '.join(tuple(row)) + '\n')

    def fit_zpoly(self, phase_pr, alpha):
        """
        Simple Zernike circle polynomial fit to a single phase-error map. Do
        not confuse with the `~pyoof.fit_zpoly`, the later calculates the
        phase-error maps from a set of beam maps, in this case we only adjust
        polynomials to the phase, an easier process.

        Parameters
        ----------
        phase_pr : `~astropy.units.quantity.Quantity`
            Phase-error map for the primary dish. It must have shape
            ``(alpha.size, resolution, resolution)``.
        alpha : `~astropy.units.quantity.Quantity`
            List of elevation angles related to ``phase_pr.shape[0]``.

        Returns
        -------
        K_coeff_alpha : `~numpy.ndarray`
            Two dimensional array for the Zernike circle polynomials
            coefficients. The shape is ``(alpha.size, N_K_coeff)``.
        """
        start_time = time.time()
        print('\n ***** PYOOF FIT POLYNOMIALS ***** \n')

        def residual_phase(K_coeff, phase_data):
            phase_model = phase(
                K_coeff=K_coeff,
                notilt=False,
                pr=self.pr,
                resolution=self.resolution
                )[2].to_value(apu.rad).flatten()
            return phase_data - phase_model

        K_coeff_alpha = np.zeros((alpha.size, self.N_K_coeff))
        for _alpha in range(alpha.size):
            res_lsq_K = optimize.least_squares(
                fun=residual_phase,
                x0=np.array([0.1] * self.N_K_coeff),
                args=(phase_pr[_alpha, :, :].to_value(apu.rad).flatten(),)
                )
            K_coeff_alpha[_alpha, :] = res_lsq_K.x

        final_time = np.round((time.time() - start_time) / 60, 2)
        print(
            '\n***** PYOOF FIT COMPLETED AT {} mins *****\n'.format(final_time)
            )

        return K_coeff_alpha

    def fit_grav_deformation_model(self, K_coeff_alpha, alpha):
        """
        Finds the full set for a gravitational deformation model given a list
        of elevations in ``alpha``. The list of Zernike circle polynomials
        coefficients, ``K_coeff_alpha``, must be given in the same order as
        ``alpha``.

        Parameters
        ----------
        K_coeff_alpha : `~numpy.ndarray`
            Two dimensional array for the Zernike circle polynomials
            coefficients. The shape is ``(alpha.size, N_K_coeff)``.
        alpha : `~astropy.units.quantity.Quantity`
            List of elevation angles related to ``phase_pr.shape[0]``.

        Returns
        -------
        G_coeff : `~numpy.ndarray`
            Two dimensional array for the gravitational deformation
            coefficients found in the least-squares minimization. The shape of
            the array will be given by the Zernike circle polynomial order
            ``n``.
        """
        start_time = time.time()
        print('\n ***** PYOOF FIT GRAVITATIONAL DEFORMATION MODEL ***** \n')

        def residual_grav_deformation_model(G, Knl, alpha):
            Knl_model = self.grav_deformation_model(G, alpha)
            return Knl - Knl_model

        G_coeff = np.zeros((self.N_K_coeff, 3))
        for N in range(self.N_K_coeff):

            res_lsq_G = optimize.least_squares(
                fun=residual_grav_deformation_model,
                x0=[0, 0, 0],
                args=(K_coeff_alpha[:, N], alpha,)
                )
            G_coeff[N, :] = res_lsq_G.x

        final_time = np.round((time.time() - start_time) / 60, 2)
        print(
            '\n***** PYOOF FIT COMPLETED AT {} mins *****\n'.format(final_time)
            )

        return G_coeff

    def fit_all(self, phase_pr, alpha):
        """
        Wrapper for all least-squares minimizations, Zernike circle
        polynomials (`~pyoof.actuator.EffelsbergActuator.fit_zpoly`) and
        gravitational deformation model
        (`~pyoof.actuator.EffelsbergActuator.fit_grav_deformation_model`).
        """

        K_coeff_alpha = self.fit_zpoly(phase_pr=phase_pr, alpha=alpha)
        G_coeff = self.fit_grav_deformation_model(
            K_coeff_alpha=K_coeff_alpha,
            alpha=alpha
            )
        return G_coeff, K_coeff_alpha

    def generate_phase_pr(self, G_coeff, alpha):
        """
        Generate a set of phase for the primary reflector ``phase_pr``, given
        the gravitational deformation coefficients ``G_coeff`` for a new set
        of elevations ``alpha``.

        Parameters
        ----------
        G_coeff : `~numpy.ndarray`
            Two dimensional array for the gravitational deformation
            coefficients found in the least-squares minimization. The shape of
            the array will be given by the Zernike circle polynomial order
            ``n``.
        alpha : `~astropy.units.quantity.Quantity`
            List of new elevation angles.

        Returns
        -------
        phase_pr : `~astropy.units.quantity.Quantity`
            Phase-error map for the primary dish. It must have shape
            ``(alpha.size, resolution, resolution)``.
        """

        phases = np.zeros(
            shape=(alpha.size, self.resolution, self.resolution)
            ) << apu.rad

        for a, _alpha in enumerate(alpha):

            K_coeff = np.zeros((self.N_K_coeff))
            for k in range(self.N_K_coeff):

                K_coeff[k] = self.grav_deformation_model(
                    G=G_coeff[k, :],
                    alpha=_alpha
                    )

            phases[a, :, :] = phase(
                K_coeff=K_coeff,
                notilt=False,
                pr=self.pr
                )[2]

        return phases
