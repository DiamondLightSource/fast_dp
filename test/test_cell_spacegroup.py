from __future__ import absolute_import, division, print_function

import os
import pytest

pytest.importorskip("cctbx.sgtbx")

from cctbx import sgtbx
from fast_dp import cell_spacegroup

def ersatz_pointgroup_old(spacegroup_name):
    """Guess the pointgroup for the spacegroup by mapping from short to
    long name, then taking 1st character from each block."""

    pg = None

    for record in open(os.path.join(os.environ["CLIBD"], "symop.lib"), "r").readlines():
        if " " in record[:1]:
            continue
        if spacegroup_name == record.split()[3]:
            pg = record.split()[4][2:]
        elif spacegroup_name == record.split("'")[1].replace(" ", ""):
            pg = record.split()[4][2:]

    if not pg:
        raise RuntimeError("spacegroup %s unknown" % spacegroup_name)

    # FIXME this is probably not correct for small molecule work...
    # just be aware of this, in no danger right now of handling non-chiral
    # spacegroups

    if "/" in pg:
        pg = pg.split("/")[0]

    result = spacegroup_name[0] + pg

    if "H3" in result:
        result = result.replace("H3", "R3")

    return result


@pytest.fixture
def acentric_space_groups():
    acentric = []
    for i in range(1, 231):
        sg = sgtbx.space_group_info(number=i).group()
        if sg.is_chiral():
            acentric.append(sg)
    return acentric


def test_ersatz_pointgroup(acentric_space_groups):
    for sg in acentric_space_groups:
        symbol = sg.type().lookup_symbol()
        symbol = symbol.split(":")[0]
        if symbol.count(" 1") == 2:
            symbol = symbol.replace(" 1", "")
        symbol = symbol.replace(" ", "")
        assert (
            cell_spacegroup.ersatz_pointgroup(symbol)
            == sgtbx.space_group_symbols(
                ersatz_pointgroup_old(symbol)
            ).hermann_mauguin()
        )
