# Fast DP: Fast Data Processsing with XDS

[![PYPI release](https://img.shields.io/pypi/v/fast_dp.svg)](https://pypi.python.org/pypi/fast_dp)
[![Build Status](https://travis-ci.com/DiamondLightSource/fast_dp.svg?branch=master)](https://travis-ci.com/DiamondLightSource/fast_dp)
[![Updates](https://pyup.io/repos/github/DiamondLightSource/fast_dp/shield.svg)](https://pyup.io/repos/github/DiamondLightSource/fast_dp/)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/fast_dp.svg)](https://pypi.org/project/fast-dp/)
[![Python 3](https://pyup.io/repos/github/DiamondLightSource/fast_dp/python-3-shield.svg)](https://pyup.io/repos/github/DiamondLightSource/fast_dp/)

### 0. Introduction

Fast DP is a small Python program which uses XDS, CCP4 & CCTBX to deliver
data processing results very quickly: quite how quickly will depend on the
operating environment. In essence, the first image in the sweep is passed
to the program, it's header read and then XDS used to index with a triclinic
lattice using spots drawn from small wedges of data around the start, 45
degrees in and 90 degrees in (or as close as possible to this). Integration
is then performed in parallel, either using multiple cores or multiple
processors if the XDS forkintegrate script is appropriately configured. The
data are then scaled with XDS, still in P1, before analysis with Pointless.
Finally the analysis from Pointless and the global postrefinement results
from the XDS CORRECT step are then used to select a pointgroup, after which
the data are re-scaled with XDS in this pointgroup and merged with Aimless.

At Diamond Light Source, using an appropriately configured cluster with a
parallel file store, this process typically takes up to two minutes for any
number of images.

##### Usage:

```
fast_dp -h
Usage: fast_dp.py [options]

Options:
  -h, --help            show this help message and exit
  -b BEAM, --beam=BEAM  Beam centre: x, y (mm)
  -a ATOM, --atom=ATOM  Atom type (e.g. Se)
  -j NUMBER_OF_JOBS, --number-of-jobs=NUMBER_OF_JOBS
                        Number of jobs for integration
  -k NUMBER_OF_CORES, --number-of-cores=NUMBER_OF_CORES
                        Number of cores for integration
  -J MAXIMUM_NUMBER_OF_JOBS, --maximum-number-of-jobs=MAXIMUM_NUMBER_OF_JOBS
                        Maximum number of jobs for integration
  -c CELL, --cell=CELL  Cell constants for processing, needs spacegroup
  -s SPACEGROUP, --spacegroup=SPACEGROUP
                        Spacegroup for scaling and merging
  -1 FIRST_IMAGE, --first-image=FIRST_IMAGE
                        First image for processing
  -N LAST_IMAGE, --last-image=LAST_IMAGE
                        First image for processing
  -r RESOLUTION_HIGH, --resolution-high=RESOLUTION_HIGH
                        High resolution limit
  -R RESOLUTION_LOW, --resolution-low=RESOLUTION_LOW
                        Low resolution limit
```

Conventional usage, e.g. on laptop, would be e.g:

```
fast_dp ~/data/i04-BAG-training/th_8_2_0001.cbf
```

giving the following output on a 2011 Macbook Pro:

>     Fast_DP installed in: /Users/graeme/svn/fast_dp
>     Starting image: /Users/graeme/data/i04-BAG-training/th_8_2_0001.cbf
>     Number of jobs: 1
>     Number of cores: 0
>     Processing images: 1 -> 540
>     Phi range: 82.00 -> 163.00
>     Template: th_8_2_####.cbf
>     Wavelength: 0.97625
>     Working in: /private/tmp/fdp
>     All autoindexing results:
>     Lattice      a      b      c  alpha   beta  gamma
>          tP  57.80  57.80 150.00  90.00  90.00  90.00
>          oC  81.80  81.70 150.00  90.00  90.00  90.00
>          oP  57.80  57.80 150.00  90.00  90.00  90.00
>          mC  81.80  81.70 150.00  90.00  90.00  90.00
>          mP  57.80  57.80 150.00  90.00  90.00  90.00
>          aP  57.80  57.80 150.00  90.00  90.00  90.00
>     Mosaic spread: 0.04 < 0.06 < 0.07
>     Happy with sg# 89
>      57.80  57.80 150.00  90.00  90.00  90.00
>     --------------------------------------------------------------------------------
>           Low resolution  28.89  28.89   1.37
>          High resolution   1.34   5.99   1.34
>                   Rmerge  0.062  0.024  0.420
>                  I/sigma  13.40  44.70   1.60
>             Completeness   99.6   98.9   96.1
>             Multiplicity    5.3    5.0    2.8
>       Anom. Completeness   96.5  100.0   71.4
>       Anom. Multiplicity    2.6    3.1    1.2
>        Anom. Correlation   99.9   99.9   76.0
>                    Nrefl 306284   3922  11217
>                  Nunique  57886    786   4030
>                Mid-slope  1.007
>                     dF/F  0.075
>               dI/sig(dI)  0.823
>     --------------------------------------------------------------------------------
>     Merging point group: P 4 2 2
>     Unit cell:  57.78  57.78 150.01  90.00  90.00  90.00
>     Processing took 00h 03m 59s (239 s) [306284 reflections]
>     RPS: 1277.6

The main result is the file fast_dp.mtz containing the scaled and merged
intensities, a log file from Aimless for plotting the merging statistics
and the information above in fast_dp.log.

See also fast_rdp to rerun last steps to change choices.

If you find fast_dp useful please cite 10.5281/zenodo.13039 as a DOI for the
source code and / or:

> Winter, G. & McAuley, K. E. "Automated data collection for macromolecular
> crystallography." Methods 55, 81-93, doi:10.1016/j.ymeth.2011.06.010 (2011).

Please also cite XDS, CCTBX & CCP4:

> Kabsch, W. "XDS." Acta Cryst. D66, 125-132 (2010)

> R. W. Grosse-Kunstleve, N. K. Sauter, N. W. Moriarty and P. D. Adams
> "The Computational Crystallography Toolbox: crystallographic algorithms
> in a reusable software framework" J. Appl. Cryst. (2002). 35, 126-136

> M. D. Winn et al. "Overview of the CCP4 suite and current developments"
> Acta. Cryst. D67, 235-242 (2011)

### 1. Dependencies

fast_dp depends on:

 - XDS
 - CCP4
 - CCTBX

If all of these are installed and configured no further work is needed. For
parallel operation in integration a forkintegrate script is needed to send
jobs to your queuing system.

### 2. Installation

You can install the latest release version of fast_dp from PyPI by loading
your CCTBX environment and then running

    libtbx.pip install fast_dp

and update an existing installation to a newer version with

    libtbx.pip install --upgrade fast_dp

You will then have to run eg.

    libtbx.configure libtbx

to make sure all command line programs are set up correctly.

#### Developer instructions

If you are a developer then you can run

    libtbx.install fast_dp

instead. This will check out a development copy of fast_dp into the cctbx
modules directory and then install that to the system. To update your
development copy you will need to update the repository as usual and then
run

    libtbx.python setup.py develop

in the source directory.

### 3. Assumptions

The XDS.INP files generated by fast_dp make the following assumptions:

 - All scans are about a single axis, approximately parallel to the detector
   "fast" axis (multi-axis goniometers are fine provided the axis for the
   scan is fixed)
 - The detector is not offset in two-theta i.e. the beam is approximately
   perpendicular to the detector face.
 - Currently templates are included for Pilatus 2M & 6M, ADSC and Rayonix CCD
   detectors - modification to other detectors may be possible.

### 4. Support

fast_dp is provided with no guarantee of support however "best effort" support
will be provided on contacting scientificsoftware@diamond.ac.uk. Users may be
asked to provide example data in the event of a bug report.

### 5. Acknowledgements

fast_dp was developed at Diamond Light Source with the specific purpose of
providing feedback to users about the merging statistics of their data in the
shortest possible time. Clearly, however, it is very much dependent on XDS
and it's intrinsic parallelisation as well as CCP4 and CCTBX to operate, and
without these fast_dp could not exist.

### 6. License

Copyright 2014 Diamond Light Source

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

### 7. Release Process

To prepare a new fast_dp release you need to install
[bumpversion](https://pypi.org/project/bumpversion/), for example by running

    pip install bumpversion

or using libtbx.pip in an CCTBX environment, followed by a libtbx.configure.
Releases can then be made by

```
# Assuming current version is 1.1.1
bumpversion major  # 1.1.1 -> 2.0.0
    # or
bumpversion minor  # 1.1.1 -> 1.2.0
    # or
bumpversion patch  # 1.1.1 -> 1.1.2

git push
git push --tags
```

The release tag, once pushed to Github, will be picked up by Travis
which will generate a new package and upload it directly to PyPI.
