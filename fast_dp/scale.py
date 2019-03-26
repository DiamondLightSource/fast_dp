from __future__ import absolute_import, division, print_function

import os
import shutil

from fast_dp.run_job import run_job
from fast_dp.cell_spacegroup import spacegroup_number_to_name
from fast_dp.autoindex import segment_text
from fast_dp.xds_reader import read_xparm_get_refined_beam


def scale(unit_cell, xds_inp, space_group_number, resolution_high=0.0):
    """Perform the scaling with the spacegroup and unit cell calculated
    from pointless and correct. N.B. this scaling is done by CORRECT."""

    assert unit_cell
    assert xds_inp
    assert space_group_number

    with open("CORRECT.INP", "w") as fout:
        for k in sorted(xds_inp):
            if "SEGMENT" in k:
                continue
            v = xds_inp[k]
            if isinstance(v, list):
                for _v in v:
                    fout.write("%s=%s\n" % (k, _v))
            else:
                fout.write("%s=%s\n" % (k, v))

        fout.write("SPACE_GROUP_NUMBER=%d\n" % space_group_number)
        fout.write("UNIT_CELL_CONSTANTS=%f %f %f %f %f %f\n" % tuple(unit_cell))

        fout.write("JOB=CORRECT\n")
        fout.write("REFINE(CORRECT)=CELL AXIS ORIENTATION POSITION BEAM\n")
        fout.write("INCLUDE_RESOLUTION_RANGE= 100 %f\n" % resolution_high)
        fout.write("%s\n" % segment_text(xds_inp))

    shutil.copyfile("CORRECT.INP", "XDS.INP")

    run_job("xds_par")

    # once again should check on the general happiness of everything...

    for step in ["CORRECT"]:
        lastrecord = open("%s.LP" % step).readlines()[-1]
        if "!!! ERROR !!!" in lastrecord:
            raise RuntimeError(
                "error in %s: %s"
                % (step, lastrecord.replace("!!! ERROR !!!", "").strip())
            )

    # and get the postrefined cell constants from GXPARM.XDS - but continue
    # to work for the old format too...

    if "XPARM.XDS" in open("GXPARM.XDS", "r").readline():
        # new format
        gxparm = open("GXPARM.XDS", "r").readlines()
        space_group = spacegroup_number_to_name(int(gxparm[3].split()[0]))
        unit_cell = tuple(map(float, gxparm[3].split()[1:]))
    else:
        # old format:
        gxparm = open("GXPARM.XDS", "r").readlines()
        space_group = spacegroup_number_to_name(int(gxparm[7].split()[0]))
        unit_cell = tuple(map(float, gxparm[7].split()[1:]))

    # FIXME also get the postrefined mosaic spread out...

    space_group = space_group
    unit_cell = unit_cell

    # and the total number of good reflections
    nref = 0

    refined_beam = read_xparm_get_refined_beam("GXPARM.XDS")

    # hack in xdsstat (but don't cry if it fails)

    try:
        xdsstat_output = run_job("xdsstat", [], ["XDS_ASCII.HKL"])
        open("xdsstat.log", "w").write("".join(xdsstat_output))
    except BaseException:
        pass

    return unit_cell, space_group, nref, refined_beam
