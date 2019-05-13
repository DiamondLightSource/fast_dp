from __future__ import absolute_import, division, print_function


from cctbx import crystal, sgtbx, uctbx
from cctbx.sgtbx.bravais_types import bravais_lattice


def ersatz_pointgroup(spacegroup_name):
    """Guess the pointgroup for the spacegroup by mapping from short to
    long name, then taking 1st character from each block."""

    pg = (
        sgtbx.space_group_info(spacegroup_name)
        .group()
        .build_derived_patterson_group()
        .build_derived_acentric_group()
        .type()
        .lookup_symbol()
    )
    return pg.split(":")[0].strip()


def spacegroup_to_lattice(input_spacegroup):
    """This generates a lattice from the imported file but chopping off
    the first letter of the cell type, changing to lowercase and then
    prepending it to the first letter of the spacegroup."""

    return str(bravais_lattice(group=sgtbx.space_group_info(input_spacegroup).group()))


def check_spacegroup_name(spacegroup_name):
    """Will return normalised name if spacegroup name is recognised,
    raise exception otherwise. For checking command-line options."""

    try:
        j = int(spacegroup_name)
        if j > 230 or j <= 0:
            raise RuntimeError("spacegroup number nonsense: %s" % spacegroup_name)
        space_group_info = sgtbx.space_group_info(number=j)

    except ValueError:
        space_group_info = sgtbx.space_group_info(symbol=spacegroup_name)

    return space_group_info.type().lookup_symbol()


def check_split_cell(cell_string):
    """Will return tuple of floats a, b, c, alpha, beta, gamma from input
    cell string which contains a,b,c,alpha,beta,gamma raising an exception
    if there is a problem."""

    ideal_string = "a,b,c,alpha,beta,gamma"

    if not cell_string.count(",") == 5:
        raise RuntimeError("%s should be of the form %s" % (cell_string, ideal_string))

    a, b, c, alpha, beta, gamma = tuple(map(float, cell_string.split(",")))

    return a, b, c, alpha, beta, gamma


def constrain_cell(lattice_class, cell):
    """Constrain cell to fit lattice class x."""

    a, b, c, alpha, beta, gamma = cell

    if lattice_class == "a":
        return (a, b, c, alpha, beta, gamma)
    elif lattice_class == "m":
        return (a, b, c, 90.0, beta, 90.0)
    elif lattice_class == "o":
        return (a, b, c, 90.0, 90.0, 90.0)
    elif lattice_class == "t":
        e = (a + b) / 2.0
        return (e, e, c, 90.0, 90.0, 90.0)
    elif lattice_class == "h":
        e = (a + b) / 2.0
        return (e, e, c, 90.0, 90.0, 120.0)
    elif lattice_class == "c":
        e = (a + b + c) / 3.0
        return (e, e, e, 90.0, 90.0, 90.0)

    raise RuntimeError("lattice class not recognised: %s" % lattice_class)


def spacegroup_number_to_name(spg_num):
    """Convert a spacegroup number to a more readable name."""
    return sgtbx.space_group_info(number=spg_num).type().lookup_symbol()


def lattice_to_spacegroup(lattice):
    """ Converts a lattice to the spacegroup with the lowest symmetry
    possible for that lattice"""
    l2s = {
        "aP": 1,
        "mP": 3,
        "mC": 5,
        "mI": 5,
        "oP": 16,
        "oC": 21,
        "oI": 23,
        "oF": 22,
        "tP": 75,
        "tI": 79,
        "hP": 143,
        "hR": 146,
        "hH": 146,
        "cP": 195,
        "cF": 196,
        "cI": 197,
    }

    return l2s[lattice]


def lauegroup_to_lattice(lauegroup):
    """Convert a Laue group representation (from pointless, e.g. I m m m)
    to something useful, like the implied crystal lattice (in this
    case, oI.)"""

    # this has been calculated from the results of Ralf GK's sginfo and a
    # little fiddling...
    #
    # 19/feb/08 added mI record as pointless has started producing this -
    # why??? this is not a "real" spacegroup... may be able to switch this
    # off...
    #                             'I2/m': 'mI',

    lauegroup_to_lattice = {
        "Ammm": "oA",
        "C2/m": "mC",
        "I2/m": "mI",
        "Cmmm": "oC",
        "Fm-3": "cF",
        "Fm-3m": "cF",
        "Fmmm": "oF",
        "H-3": "hR",
        "H-3m": "hR",
        "R-3:H": "hR",
        "R-3m:H": "hR",
        "R-3": "hR",
        "R-3m": "hR",
        "I4/m": "tI",
        "I4/mmm": "tI",
        "Im-3": "cI",
        "Im-3m": "cI",
        "Immm": "oI",
        "P-1": "aP",
        "P-3": "hP",
        "P-3m": "hP",
        "P2/m": "mP",
        "P4/m": "tP",
        "P4/mmm": "tP",
        "P6/m": "hP",
        "P6/mmm": "hP",
        "Pm-3": "cP",
        "Pm-3m": "cP",
        "Pmmm": "oP",
    }

    updated_laue = ""

    for l in lauegroup.split():
        if not l == "1":
            updated_laue += l

    return lauegroup_to_lattice[updated_laue]


def generate_primitive_cell(unit_cell_constants, space_group_name):
    """For a given set of unit cell constants and space group, determine the
    corresponding primitive unit cell..."""

    uc = uctbx.unit_cell(unit_cell_constants)
    sg = sgtbx.space_group_info(space_group_name).group()
    cs = crystal.symmetry(unit_cell=uc, space_group=sg)
    csp = cs.change_basis(cs.change_of_basis_op_to_primitive_setting())

    return csp.unit_cell()


if __name__ == "__main__":
    import sys

    for token in sys.argv[1:]:
        print(ersatz_pointgroup(token))
