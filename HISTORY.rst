=======
History
=======

1.6.3 (...)
-----------
* change default plugin for Eiger data to durin-plugin.so

1.6.2 (2020-03-14)
------------------
* bugfix for Python 3 error

1.6.1 (2020-02-25)
------------------
* add license file to release

1.6.0 (2020-02-25)
------------------
* fast_dp is no longer supported with DIALS 1.12 and older versions
* add support for DIALS 2.1+
* add support for Python 3.8

1.5.0 (2019-10-23)
------------------
* add support for DIALS 2.0
* use correct number of cores for integration with forkxds

1.4.0 (2019-06-10)
------------------
* Improved support for spacegroup names.
  (`#41 <https://github.com/DiamondLightSource/fast_dp/pull/41>`_)

1.3.0 (2019-03-28)
------------------
* Report beam centre correctly in ispyb.xml for multi-panel
  detectors.

1.2.0 (2018-12-03)
------------------
* fast_dp and fast_rdp return with a non-zero exit code
  when processing fails.

1.1.2 (2018-11-22)
------------------
* Catch case where diffraction strong to edge of detector.

1.1.1 (2018-11-21)
------------------

* Write out correct r_meas value in the fast_dp.json file.

1.1.0 (2018-11-15)
------------------

* fast_dp.json format has changed. Scaling statistics are now
  stored in a structured dictionary.
  (`#28 <https://github.com/DiamondLightSource/fast_dp/pull/28>`_)

* removed XDS.INP templates; now calculated on demand using dxtbx
  models from DIALS, thus allowing support for all beamlines
  currently understood by DIALS

1.0.0 (2018-10-31)
------------------

* First release on PyPI.
