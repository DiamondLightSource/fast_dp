from __future__ import absolute_import, division, print_function

import os
import shutil

from fast_dp.xds_writer import write_xds_inp_correct
from fast_dp.run_job import run_job
from fast_dp.cell_spacegroup import spacegroup_number_to_name

def scale(unit_cell, metadata, space_group_number, resolution_high):
    '''Perform the scaling with the spacegroup and unit cell calculated
    from pointless and correct. N.B. this scaling is done by CORRECT.'''

    assert(unit_cell)
    assert(metadata)
    assert(space_group_number)

    if resolution_high:
        resolution_high = resolution_high
    else:
        resolution_high = 0.0

    xds_inp = 'CORRECT.INP'

    write_xds_inp_correct(metadata, unit_cell,
                          space_group_number, xds_inp,
                          resolution_high = resolution_high)

    shutil.copyfile(xds_inp, 'XDS.INP')

    run_job('xds_par')

    # once again should check on the general happiness of everything...

    for step in ['CORRECT']:
        lastrecord = open('%s.LP' % step).readlines()[-1]
        if '!!! ERROR !!!' in lastrecord:
            raise RuntimeError('error in %s: %s' % \
                  (step, lastrecord.replace('!!! ERROR !!!', '').strip()))

    # and get the postrefined cell constants from GXPARM.XDS - but continue
    # to work for the old format too...

    if 'XPARM.XDS' in open('GXPARM.XDS', 'r').readline():
        # new format
        gxparm = open('GXPARM.XDS', 'r').readlines()
        space_group = spacegroup_number_to_name(int(gxparm[3].split()[0]))
        unit_cell = tuple(map(float, gxparm[3].split()[1:]))
    else:
        # old format:
        gxparm = open('GXPARM.XDS', 'r').readlines()
        space_group = spacegroup_number_to_name(int(gxparm[7].split()[0]))
        unit_cell = tuple(map(float, gxparm[7].split()[1:]))

    # FIXME also get the postrefined mosaic spread out...

    space_group = space_group
    unit_cell = unit_cell

    # and the total number of good reflections
    nref = 0

    # set the refined beam in case it was not refined correctly in the
    # global refinement (this probably indicates a bigger problem anyway)
    refined_beam = 0, 0

    for record in open('CORRECT.LP', 'r').readlines():
        if 'NUMBER OF ACCEPTED OBSERVATIONS' in record:
            nref = int(record.replace(')', ') ').split()[-1])
        if 'DETECTOR COORDINATES (PIXELS) OF DIRECT BEAM' in record:
            refined_beam = tuple(map(float, record.split()[-2:]))

    # hack in xdsstat (but don't cry if it fails)

    try:
        xdsstat_output = run_job('xdsstat', [], ['XDS_ASCII.HKL'])
        open('xdsstat.log', 'w').write(''.join(xdsstat_output))
    except:
        pass

    return unit_cell, space_group, nref, refined_beam
