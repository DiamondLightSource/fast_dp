from __future__ import absolute_import, division, print_function

import os
import shutil

from fast_dp.xds_writer import write_xds_inp_integrate
from fast_dp.run_job import run_job

def integrate(metadata, p1_unit_cell, resolution_low, n_jobs, n_processors):
    '''Peform the integration with a triclinic basis.'''

    assert(metadata)
    assert(p1_unit_cell)

    xds_inp = 'INTEGRATE.INP'

    # FIXME in here make a calculation from the metadata of a sensible
    # maximum number of jobs, to give minimally 5 degree wedges.

    write_xds_inp_integrate(metadata, xds_inp, resolution_low,
                            no_jobs=n_jobs, no_processors=n_processors)

    shutil.copyfile(xds_inp, 'XDS.INP')

    run_job('xds_par')

    # FIXME need to check that all was hunky-dory in here!

    for step in ['DEFPIX', 'INTEGRATE']:
        if not os.path.exists('%s.LP' % step):
            continue
        lastrecord = open('%s.LP' % step).readlines()[-1]
        if '!!! ERROR !!!' in lastrecord:
            raise RuntimeError('error in %s: %s' % \
                  (step, lastrecord.replace(
                '!!! ERROR !!!', '').strip().lower()))

    if not os.path.exists('INTEGRATE.LP'):
        step = 'INTEGRATE'
        for record in open('LP_01.tmp').readlines():
            if '!!! ERROR !!! AUTOMATIC DETERMINATION OF SPOT SIZE ' in record:
                raise RuntimeError('error in %s: %s' % \
                      (step, record.replace(
                    '!!! ERROR !!!', '').strip().lower()))
            elif '!!! ERROR !!! CANNOT OPEN OR READ FILE LP_01.tmp' in record:
                raise RuntimeError('integration error: cluster error')

    # check for some specific errors

    for step in ['INTEGRATE']:
        for record in open('%s.LP' % step).readlines():
            if '!!! ERROR !!! AUTOMATIC DETERMINATION OF SPOT SIZE ' in record:
                raise RuntimeError('error in %s: %s' % \
                      (step, record.replace(
                    '!!! ERROR !!!', '').strip().lower()))
            elif '!!! ERROR !!! CANNOT OPEN OR READ FILE LP_01.tmp' in record:
                raise RuntimeError('integration error: cluster error')



    # if all was ok, look in the working directory for files named
    # forkintegrate_job.o341858 &c. and remove them. - N.B. this is site
    # specific!

    for f in os.listdir(os.getcwd()):
        if 'forkintegrate_job.' in f[:18]:
            try:
                os.remove(f)
            except:
                pass

    # get the mosaic spread ranges

    mosaics = []

    for record in open('INTEGRATE.LP'):
        if 'CRYSTAL MOSAICITY (DEGREES)' in record:
            mosaics.append(float(record.split()[-1]))

    mosaic = sum(mosaics) / len(mosaics)

    return min(mosaics), mosaic, max(mosaics)
