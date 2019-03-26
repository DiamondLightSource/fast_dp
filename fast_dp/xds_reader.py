from __future__ import absolute_import, division, print_function

import re

from fast_dp.cell_spacegroup import constrain_cell, lattice_to_spacegroup


def read_xds_idxref_lp(idxref_lp_file):
    """Read the XDS IDXREF.LP file and return a dictionary indexed by the
    spacegroup number (ASSERT: this is the lowest symmetry spacegroup for
    the corresponding lattice) containing unit cell constants and a
    penalty. N.B. this also works from CORRECT.LP for the autoindexing
    results."""

    # try doing this with regular expression: * int lattice...`

    regexp = re.compile(r"^ \*\ ")

    results = {}

    for record in open(idxref_lp_file, "r").readlines():
        if regexp.match(record):
            tokens = record.split()
            spacegroup = lattice_to_spacegroup(tokens[2])
            cell = tuple(map(float, tokens[4:10]))
            constrained_cell = constrain_cell(tokens[2][0], cell)
            penalty = float(tokens[3])

            if spacegroup in results:
                if penalty < results[spacegroup][0]:
                    results[spacegroup] = penalty, constrained_cell
            else:
                results[spacegroup] = penalty, constrained_cell

        if "DETECTOR COORDINATES (PIXELS) OF DIRECT BEAM" in record:
            results["beam centre pixels"] = map(float, record.split()[-2:])

    assert "beam centre pixels" in results

    return results


def read_xds_correct_lp(correct_lp_file):
    """Read the XDS CORRECT.LP file and get out the spacegroup and
    unit cell constants it decided on."""

    unit_cell = None
    space_group_number = None

    for record in open(correct_lp_file, "r").readlines():
        if "SPACE_GROUP_NUMBER=" in record:
            try:
                space_group_number = int(record.split()[-1])
            except BaseException:
                space_group_number = 0
        if "UNIT_CELL_CONSTANTS=" in record and "used" not in record:
            unit_cell = tuple(map(float, record.split()[-6:]))

    return unit_cell, space_group_number


def read_correct_lp_get_resolution(correct_lp_file):
    """Read the CORRECT.LP file and get an estimate of the resolution limit.
    This should then be recycled to a rerun of CORRECT, from which the
    reflections will be merged to get the statistics."""

    correct_lp = open(correct_lp_file, "r").readlines()

    rec = -1

    for j in range(len(correct_lp)):
        record = correct_lp[j]

        if "RESOLUTION RANGE  I/Sigma  Chi^2  R-FACTOR  R-FACTOR" in record:
            rec = j + 3
            break

    if rec < 0:
        raise RuntimeError("resolution information not found")

    j = rec

    while "--------" not in correct_lp[j]:
        isigma = float(correct_lp[j].split()[2])
        if isigma < 1:
            return float(correct_lp[j].split()[1])
        j += 1

    # this will assume that strong reflections go to the edge of the detector
    # => do not need to feed back a resolution limit...

    return 0.0


def read_xparm_get_refined_beam(xparm_file):
    import dxtbx

    models = dxtbx.load(xparm_file)
    detector = models.get_detector()
    beam = models.get_beam()
    s0 = beam.get_s0()

    x, y = (None, None)
    for panel_id, panel in enumerate(detector):
        try:
            x, y = panel.get_ray_intersection(s0)
        except RuntimeError:
            continue
        else:
            if panel.is_coord_valid_mm((x, y)):
                break
            else:
                x, y = (None, None)

    if x is not None and y is not None:
        panel = detector[panel_id]
        x_px, y_px = panel.millimeter_to_pixel((x, y))
        offset = panel.get_raw_image_offset()
        x, y = (x_px + offset[0], y_px + offset[1])

    return x, y
