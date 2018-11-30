from __future__ import absolute_import, division, print_function

import os
import shutil

from fast_dp.xds_reader import read_xds_idxref_lp
from fast_dp.run_job import run_job

from fast_dp.cell_spacegroup import spacegroup_to_lattice

from fast_dp.logger import write

# TODO add pytests for this method


def add_spot_range(xds_inp):
    start, end = map(int, xds_inp["DATA_RANGE"].split())
    osc = float(xds_inp["OSCILLATION_RANGE"])
    wedge = max(10, int(round(5.0 / osc)))

    spot_ranges = []

    if (end - start + 1) * osc <= 15:
        spot_ranges.append("%d %d" % (start, end))

    elif int(90.0 / osc) + start + wedge <= end:
        half = int(0.5 * ((90 / osc) - wedge)) + start
        spot_ranges.append("%d %d" % (start, start + wedge - 1))
        spot_ranges.append("%d %d" % (half, half + wedge - 1))
        spot_ranges.append(
            "%d %d" % (int(90.0 / osc) + start, int(90.0 / osc) + start + wedge - 1)
        )
    else:
        half = int((start + end - wedge) / 2)
        spot_ranges.append("%d %d" % (start, start + wedge - 1))
        spot_ranges.append("%d %d" % (half, half + wedge - 1))
        spot_ranges.append("%d %d" % (end - wedge + 1, end))

    xds_inp["SPOT_RANGE"] = spot_ranges

    return xds_inp


def segment_text(xds_inp):
    if "SEGMENT" not in xds_inp:
        return ""

    result = []

    n = len(xds_inp["SEGMENT"])

    for j in range(n):
        for k in (
            "SEGMENT",
            "SEGMENT_DISTANCE",
            "SEGMENT_ORGX",
            "SEGMENT_ORGY",
            "DIRECTION_OF_SEGMENT_X-AXIS",
            "DIRECTION_OF_SEGMENT_Y-AXIS",
        ):
            result.append("%s=%s" % (k, xds_inp[k][j]))

    return "\n".join(result)


def autoindex(xds_inp, input_cell=None):
    """Perform the autoindexing, using metatdata, get a list of possible
    lattices and record / return the triclinic cell constants (get these from
    XPARM.XDS)."""

    assert xds_inp

    xds_inp = add_spot_range(xds_inp)

    with open("AUTOINDEX.INP", "w") as fout:
        for k in sorted(xds_inp):
            if "SEGMENT" in k:
                continue
            v = xds_inp[k]
            if isinstance(v, list):
                for _v in v:
                    fout.write("%s=%s\n" % (k, _v))
            else:
                fout.write("%s=%s\n" % (k, v))

        fout.write("%s\n" % segment_text(xds_inp))

        if input_cell:
            fout.write("SPACE_GROUP_NUMBER=1\n")
            fout.write("UNIT_CELL_CONSTANTS=%f %f %f %f %f %f\n" % tuple(input_cell))

        fout.write("JOB=XYCORR INIT COLSPOT IDXREF\n")
        fout.write("REFINE(IDXREF)=CELL AXIS ORIENTATION POSITION BEAM\n")
        fout.write("MAXIMUM_ERROR_OF_SPOT_POSITION= 2.0\n")
        fout.write("MINIMUM_FRACTION_OF_INDEXED_SPOTS= 0.5\n")

    shutil.copyfile("AUTOINDEX.INP", "XDS.INP")

    log = run_job("xds_par")

    with open("autoindex.log", "w") as fout:
        fout.write("".join(log))

    # sequentially check for errors... XYCORR INIT COLSPOT IDXREF

    for step in ["XYCORR", "INIT", "COLSPOT", "IDXREF"]:
        lastrecord = open("%s.LP" % step).readlines()[-1]
        if "!!! ERROR !!!" in lastrecord:
            raise RuntimeError(
                "error in %s: %s"
                % (step, lastrecord.replace("!!! ERROR !!!", "").strip())
            )

    results = read_xds_idxref_lp("IDXREF.LP")

    # FIXME if input cell was given, verify that this is an allowed
    # permutation. If it was not, raise a RuntimeError. This remains to be
    # fixed

    write("All autoindexing results:")
    write(
        "%3s %6s %6s %6s %6s %6s %6s"
        % ("Lattice", "a", "b", "c", "alpha", "beta", "gamma")
    )

    for r in reversed(sorted(results)):
        if not isinstance(r, type(1)):
            continue
        cell = results[r][1]
        write(
            "%7s %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f"
            % (
                spacegroup_to_lattice(r),
                cell[0],
                cell[1],
                cell[2],
                cell[3],
                cell[4],
                cell[5],
            )
        )

    # should probably print this for debugging

    try:
        return results[1][1]
    except BaseException:
        raise RuntimeError("getting P1 cell for autoindex")
