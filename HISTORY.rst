=======
History
=======

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
