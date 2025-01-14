*****
pyoof
*****

- *Version: 0.3*
- *Author: Tomas Cassanelli*
- *User manual:* `stable <http://pyoof.readthedocs.io/en/stable/>`__ |
  `developer <http://pyoof.readthedocs.io/en/latest/>`__

.. image:: https://img.shields.io/pypi/v/pyoof.svg
    :target: https://pypi.python.org/pypi/pyoof
    :alt: PyPI tag

.. image:: https://img.shields.io/badge/License-BSD%203--Clause-blue.svg
    :target: https://opensource.org/licenses/BSD-3-Clause
    :alt: License

.. image:: http://img.shields.io/badge/arXiv-2109.00006-blue.svg
    :target: https://arxiv.org/abs/2109.00006
    :alt: Publication

pyoof is a Python package that contains all needed tools to perform out-of-focus (OOF) holography on astronomical beam maps for single-dish radio telescopes. It is based on the original OOF holography papers,

* `Out-of-focus holography at the Green Bank Telescope <https://www.aanda.org/articles/aa/ps/2007/14/aa5765-06.ps.gz>`_
* `Measurement of antenna surfaces from in- and out-of-focus beam maps using astronomical sources <https://www.aanda.org/articles/aa/ps/2007/14/aa5603-06.ps.gz>`_

and `software <https://github.com/bnikolic/oof>`_ developed by `Bojan Nikolic <http://www.mrao.cam.ac.uk/~bn204/oof/>`_.

In brief, the pyoof package calculates the aperture phase distribution map from a set of beam maps (telescope observations), at a relatively good signal-to-noise as described by B. Nikolic. By using a nonlinear least squares minimization a convenient set of polynomials can be used to reconstruct the aperture distribution. The representation can also be used to compute the aperture phase distribution or simply phase-error, which contains vital information related to the aberrations in the telescope primary dish surface. Knowing the dish aberrations means that they can be potentially corrected, hence improve the telescope sensitivity [K/Jy].

We are currently testing the pyoof package at the `Effelsberg radio telescope <https://en.wikipedia.org/wiki/Effelsberg_100-m_Radio_Telescope>`_ :satellite:.

Project Status
==============
.. image:: https://travis-ci.org/tcassanelli/pyoof.svg?branch=master
    :target: https://travis-ci.org/tcassanelli/pyoof
    :alt: Pyoof's Travis CI Status

.. image:: https://coveralls.io/repos/github/tcassanelli/pyoof/badge.svg?branch=master
    :target: https://coveralls.io/github/tcassanelli/pyoof?branch=master
    :alt: Pyoof's Coveralls Status

.. image:: https://readthedocs.org/projects/pyoof/badge/?version=latest
    :target: https://pyoof.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

pyoof is still in the early-development stage. While much of the
functionality is already working as intended, the API is not yet stable.
Nevertheless, we kindly invite you to use and test the library and we are
grateful for feedback.

Installation
============
**Note**: Currently the package installation is not working without a prior installation of the `miniconda <https://conda.io/miniconda.html>`_ distribution (or anaconda distribution). In the mean time please install miniconda and follow the instructions below.

The easiest and more convenient way to install the pyoof package is via ``pip``

.. code-block:: bash

    pip install pyoof

The installation is also possible from the source. Clone the GitHub repository and execute!

.. code-block:: bash

    python setup.py install

From the source you can install developer versions, be aware of that. For further installation details and troubleshooting visit the documentation `Installation <http://pyoof.readthedocs.io/en/latest/install.html>`_.
I believe in the future :smile:, so please install Python 3.
Unfortunately, a windows version of the package is currently not available.

Dependencies
============
So far the pyoof package uses the common Python packages, it is recommended to install the `anaconda <https://www.anaconda.com>`_ distribution first, although using `pip` is also fine.

pyoof has the following strict requirements:

- `Python <http://www.python.org/>`__ 3.6 or later.

- `setuptools <https://pypi.python.org/pypi/setuptools>`__: Used for the
  package installation.

- `NumPy <http://www.numpy.org/>`__ 1.4 or later.

- `SciPy <https://scipy.org/>`__: 0.15 or later.

- `Astropy <http://www.astropy.org/>`__: 2.4 or later.

- `pytest <https://pypi.python.org/pypi/pytest>`__ 2.6 or later.

- `matplotlib <http://matplotlib.org/>`__ 1.5 or later: To provide plotting
  functionality.

- `PyYAML <http://pyyaml.org>`__ 5.3.1 or later.

For future versions dependencies will be reduced.

Usage
=====
To use the pyoof package is straight forward. First define your observational data in the established FITS file format and then execute!

.. code-block:: python

    import pyoof
    from astropy import units as u

    # Extracting observation data and important information
    oofh_data = 'path/to/file.fits'  # FITS file with special format
    data_info, data_obs = pyoof.extract_data_pyoof(oofh_data)

    # Effelsberg telescope definition
    effelsberg_telescope = [
        pyoof.telgeometry.block_effelsberg(),  # blockage distribution
        pyoof.telgeometry.opd_effelsberg,    # OPD function
        50. * u.m,                           # primary reflector radius
        'effelsberg'                         # telescope name
        ]

    pyoof.fit_zpoly(
        data_info=data_info,                       # information
        data_obs=data_obs,                         # observed beam
        order_max=5,                               # computes up to order_max
        illum_func=pyoof.aperture.illum_pedestal,  # or illum_gauss
        telescope=effelsberg_telescope,            # telescope properties
        resolution=2 ** 8,                         # standard is 2 ** 8
        box_factor=5,                              # box_size = 5 * pr, pixel resolution
        )

For the impatient :hushed: , see the Jupyter notebook example, `oof_holography.ipynb <https://github.com/tcassanelli/pyoof/blob/master/notebooks/oof_holography.ipynb>`_.

License
=======
pyoof is licensed under a 3-clause BSD style license - see the `LICENSE <https://github.com/tcassanelli/pyoof/blob/master/LICENSE.rst>`_ file.

Improvements future versions
============================
- Include plot routines tests
- Inlcude actuators module tests
- Reduce the size of the test files
- Integrate Astropy units :white_check_mark:
- Include automatic setup for the FFT resolution ``pyoof.fit_zpoly(resolution)``
- Add actuator correction (sub-package) and its translation from phase-error (specific for Effelsberg) :white_check_mark:
- Add option for 2 or more beam maps (option for multiple ``d_z``)

Contact
=======
If you have any questions about the code or theory sections, do not hesitate and raise an issue. You can also send me an email directly:

- tcassanelli  *at*  protonmail.com

Preferred citation method
=========================

To cite the code used in pyoof as well as the method please see `Acknowledgments and references <https://pyoof.readthedocs.io/en/latest/#acknowledgments-and-references>`_.

Please cite the paper Out-of-focus at the Effelsberg telescope (submitted to A&A) if you used the method and code:

.. code-block:: latex

    @ARTICLE{2021arXiv210900006C,
           author = {{Cassanelli}, T. and {Bach}, U. and {Winkel}, B. and {Kraus}, A.},
            title = "{Out-of-focus holography at the Effelsberg telescope}",
          journal = {arXiv e-prints},
         keywords = {Astrophysics - Instrumentation and Methods for Astrophysics, Physics - Optics},
             year = 2021,
            month = aug,
              eid = {arXiv:2109.00006},
            pages = {arXiv:2109.00006},
    archivePrefix = {arXiv},
           eprint = {2109.00006},
     primaryClass = {astro-ph.IM},
           adsurl = {https://ui.adsabs.harvard.edu/abs/2021arXiv210900006C},
          adsnote = {Provided by the SAO/NASA Astrophysics Data System}
    }
