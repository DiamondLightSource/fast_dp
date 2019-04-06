from __future__ import absolute_import, division, print_function

import xml.dom.minidom

from fast_dp.cell_spacegroup import lauegroup_to_lattice
from cctbx import sgtbx


def read_pointless_xml(pointless_xml_file):
    """Read through the pointless xml output, return as a list of spacegroup
    numbers in order of likelihood, corresponding to the pointgroup of the
    data."""

    dom = xml.dom.minidom.parse(pointless_xml_file)

    scorelist = dom.getElementsByTagName("LaueGroupScoreList")[0]
    scores = scorelist.getElementsByTagName("LaueGroupScore")

    results = []

    for s in scores:
        lauegroup = str(
            s.getElementsByTagName("LaueGroupName")[0].childNodes[0].data
        ).strip()
        if lauegroup[0] == "H":
            lauegroup = "R%s" % lauegroup[1:]
        pointgroup = (
            sgtbx.space_group_type(lauegroup)
            .group()
            .build_derived_acentric_group()
            .type()
            .number()
        )
        netzc = float(s.getElementsByTagName("NetZCC")[0].childNodes[0].data)

        # record this as a possible lattice... if it's Z score
        # is positive, anyway - except this does kinda bias towards
        # those lattices which have all symops => no Z-.

        lattice = lauegroup_to_lattice(lauegroup)
        if netzc >= 0.0:
            results.append((lattice, pointgroup))

    return results
