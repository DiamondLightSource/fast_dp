from __future__ import absolute_import, division, print_function

import os
import shutil

from fast_dp.xds_reader import (
    read_xds_idxref_lp,
    read_correct_lp_get_resolution,
    read_xds_correct_lp,
)
from fast_dp.pointless_reader import read_pointless_xml
from fast_dp.run_job import run_job
from fast_dp.cell_spacegroup import (
    lattice_to_spacegroup,
    ersatz_pointgroup,
    spacegroup_to_lattice,
    check_spacegroup_name,
)

from fast_dp.logger import write
from fast_dp.autoindex import segment_text


def decide_pointgroup(p1_unit_cell, xds_inp, input_spacegroup=None):
    """Run POINTLESS to get the list of allowed pointgroups (N.B. will
    insist on triclinic symmetry for this scaling step) then run
    pointless on the resulting reflection file to get the idea of the
    best pointgroup to use. Then return the correct pointgroup and
    cell."""

    assert p1_unit_cell

    start, end = map(int, xds_inp["DATA_RANGE"].split())
    osc = float(xds_inp["OSCILLATION_RANGE"])
    if (end - start + 1) * osc > 360:
        end = start + int(round(360.0 / osc))
        xds_inp["DATA_RANGE"] = "%d %d" % (start, end)

    with open("P1.INP", "w") as fout:
        for k in sorted(xds_inp):
            if "SEGMENT" in k:
                continue
            v = xds_inp[k]
            if isinstance(v, list):
                for _v in v:
                    fout.write("%s=%s\n" % (k, _v))
            else:
                fout.write("%s=%s\n" % (k, v))

        fout.write("SPACE_GROUP_NUMBER=1\n")
        fout.write("UNIT_CELL_CONSTANTS=%f %f %f %f %f %f\n" % tuple(p1_unit_cell))

        fout.write("JOB=CORRECT\n")
        fout.write("REFINE(CORRECT)=CELL AXIS ORIENTATION POSITION BEAM\n")
        fout.write("%s\n" % segment_text(xds_inp))

    shutil.copyfile("P1.INP", "XDS.INP")

    run_job("xds_par")

    shutil.copyfile("CORRECT.LP", "P1.LP")

    # get the list of allowed lattices

    results = read_xds_idxref_lp("CORRECT.LP")

    # also read out the resolution limit

    resolution_high = read_correct_lp_get_resolution("CORRECT.LP")

    # run pointless, get the list of suggested lattices and pointgroups
    # FIXME should use the program manager for this... yes, this will
    # check that the executable is available too!

    xdsin = "XDS_ASCII.HKL"
    xmlout = "pointless.xml"

    pointless_log = run_job(
        "pointless",
        arguments=["xdsin", xdsin, "xmlout", xmlout],
        stdin=["systematicabsences off"],
    )

    fout = open("pointless.log", "w")

    for record in pointless_log:
        fout.write(record)

    fout.close()

    # now read the XML file

    pointless_results = read_pointless_xml(xmlout)

    # select the top solution which is allowed, return this

    if input_spacegroup:
        sg_accepted = False
        pointgroup = ersatz_pointgroup(input_spacegroup)
        if pointgroup.startswith("H"):
            pointgroup = pointgroup.replace("H", "R")
        lattice = spacegroup_to_lattice(input_spacegroup)
        for r in pointless_results:
            result_sg = "".join(check_spacegroup_name(r[1]).split(" "))
            if (
                lattice_to_spacegroup(lattice) in results
                and ersatz_pointgroup(result_sg) == pointgroup
            ):
                space_group_number = r[1]
                unit_cell = results[lattice_to_spacegroup(r[0])][1]
                write("Happy with sg# %d" % space_group_number)
                write("%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f" % unit_cell)
                sg_accepted = True
                break

        if not sg_accepted:
            write(
                "No indexing solution for spacegroup %s so ignoring" % input_spacegroup
            )
            input_spacegroup = None

    # if input space group obviously nonsense, allow to ignore just warn
    if not input_spacegroup:
        for r in pointless_results:
            if lattice_to_spacegroup(r[0]) in results:
                space_group_number = r[1]
                unit_cell = results[lattice_to_spacegroup(r[0])][1]
                write("Happy with sg# %d" % space_group_number)
                write("%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f" % unit_cell)

                break
            else:
                write("Rejected solution %s %3d" % r)

    # this should probably be a proper check...
    assert space_group_number

    # also save the P1 XDS_ASCII.HKL file see
    # http://trac.diamond.ac.uk/scientific_software/ticket/1106

    shutil.copyfile("XDS_ASCII.HKL", "XDS_P1.HKL")

    return unit_cell, space_group_number, resolution_high
