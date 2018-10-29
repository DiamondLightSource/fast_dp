from __future__ import absolute_import, division, print_function

import os

from cctbx import xray
from cctbx.sgtbx import space_group
from cctbx.sgtbx import space_group_symbols
from cctbx.uctbx import unit_cell
from cctbx.crystal import symmetry

def ersatz_pointgroup(spacegroup_name):
    '''Guess the pointgroup for the spacegroup by mapping from short to
    long name, then taking 1st character from each block.'''

    pg = None

    for record in open(
        os.path.join(os.environ['CLIBD'], 'symop.lib'), 'r').readlines():
        if ' ' in record[:1]:
            continue
        if spacegroup_name == record.split()[3]:
            pg = record.split()[4][2:]
        elif spacegroup_name == record.split('\'')[1].replace(' ', ''):
            pg = record.split()[4][2:]

    if not pg:
        raise RuntimeError('spacegroup %s unknown' % spacegroup_name)

    # FIXME this is probably not correct for small molecule work...
    # just be aware of this, in no danger right now of handling non-chiral
    # spacegroups

    if '/' in pg:
        pg = pg.split('/')[0]

    result = spacegroup_name[0] + pg

    if 'H3' in result:
        result = result.replace('H3', 'R3')

    return result

def spacegroup_to_lattice(input_spacegroup):
    ''' This generates a lattics from a the imported file bu chopping off
    the first letter of the cell type, changing to lowercase and then
    prepending it to the first letter of the spacegroup.'''

    def fix_hH(lattice):
        if lattice != 'hH':
            return lattice
        return 'hR'

    mapping = {'TRICLINIC':'a',
               'MONOCLINIC':'m',
               'ORTHORHOMBIC':'o',
               'TETRAGONAL':'t',
               'TRIGONAL':'h',
               'HEXAGONAL':'h',
               'CUBIC':'c'}

    if type(input_spacegroup) == type(u''):
        input_spacegroup = str(input_spacegroup)

    if type(input_spacegroup) == type(''):
        for record in open(
            os.path.join(os.environ['CLIBD'], 'symop.lib'), 'r').readlines():
            if ' ' in record[:1]:
                continue
            if input_spacegroup == record.split()[3]:
                return fix_hH(mapping[record.split()[5]] + record.split()[3][0])

    elif type(input_spacegroup) == type(0):
        for record in open(
            os.path.join(os.environ['CLIBD'], 'symop.lib'), 'r').readlines():
            if ' ' in record[:1]:
                continue
            if input_spacegroup == int(record.split()[0]):
                return fix_hH(mapping[record.split()[5]] + record.split()[3][0])

    else:
        raise RuntimeError('bad type for input: %s' % type(input_spacegroup))

    return None

def check_spacegroup_name(spacegroup_name):
    '''Will return normalised name if spacegroup name is recognised,
    raise exception otherwise. For checking command-line options.'''

    try:
        j = int(spacegroup_name)
        if j > 230 or j <= 0:
            raise RuntimeError('spacegroup number nonsense: %s' \
                  % spacegroup_name)
        return spacegroup_number_to_name(j)

    except ValueError:
        pass

    found_spacegroup = None

    for record in open(
        os.path.join(os.environ['CLIBD'], 'symop.lib'), 'r').readlines():
        if ' ' in record[:1]:
            continue
        if spacegroup_name == record.split()[3]:
            return spacegroup_name

    raise RuntimeError('spacegroup name "%s" not recognised' % spacegroup_name)

def check_split_cell(cell_string):
    '''Will return tuple of floats a, b, c, alpha, beta, gamma from input
    cell string which contains a,b,c,alpha,beta,gamma raising an exception
    if there is a problem.'''

    ideal_string = 'a,b,c,alpha,beta,gamma'

    if not cell_string.count(',') == 5:
        raise RuntimeError('%s should be of the form %s' % \
              (cell_string, ideal_string))

    a, b, c, alpha, beta, gamma = tuple(
        map(float, cell_string.split(',')))

    return a, b, c, alpha, beta, gamma

def constrain_cell(lattice_class, cell):
    '''Constrain cell to fit lattice class x.'''

    a, b, c, alpha, beta, gamma = cell

    if lattice_class == 'a':
        return (a, b, c, alpha, beta, gamma)
    elif lattice_class == 'm':
        return (a, b, c, 90.0, beta, 90.0)
    elif lattice_class == 'o':
        return (a, b, c, 90.0, 90.0, 90.0)
    elif lattice_class == 't':
        e = (a + b) / 2.0
        return (e, e, c, 90.0, 90.0, 90.0)
    elif lattice_class == 'h':
        e = (a + b) / 2.0
        return (e, e, c, 90.0, 90.0, 120.0)
    elif lattice_class == 'c':
        e = (a + b + c) / 3.0
        return (e, e, e, 90.0, 90.0, 90.0)

    raise RuntimeError('lattice class not recognised: %s' % lattice_class)

def spacegroup_number_to_name(spg_num):
    '''Convert a spacegroup number to a more readable name.'''

    database = { }

    for record in open(
        os.path.join(os.environ['CLIBD'], 'symop.lib'), 'r').readlines():
        if ' ' in record[:1]:
            continue
        number = int(record.split()[0])
        name = record.split('\'')[1].strip()
        database[number] = name

    return database[spg_num]

def lattice_to_spacegroup(lattice):
    ''' Converts a lattice to the spacegroup with the lowest symmetry
    possible for that lattice'''
    l2s = {
        'aP':1,   'mP':3,   'mC':5,   'mI':5,
        'oP':16,  'oC':21,  'oI':23,  'oF':22,
        'tP':75,  'tI':79,  'hP':143, 'hR':146,
        'hH':146, 'cP':195, 'cF':196, 'cI':197
        }

    return l2s[lattice]

def lauegroup_to_lattice(lauegroup):
    '''Convert a Laue group representation (from pointless, e.g. I m m m)
    to something useful, like the implied crystal lattice (in this
    case, oI.)'''

    # this has been calculated from the results of Ralf GK's sginfo and a
    # little fiddling...
    #
    # 19/feb/08 added mI record as pointless has started producing this -
    # why??? this is not a "real" spacegroup... may be able to switch this
    # off...
    #                             'I2/m': 'mI',

    lauegroup_to_lattice = {'Ammm': 'oA',
                            'C2/m': 'mC',
                            'I2/m': 'mI',
                            'Cmmm': 'oC',
                            'Fm-3': 'cF',
                            'Fm-3m': 'cF',
                            'Fmmm': 'oF',
                            'H-3': 'hR',
                            'H-3m': 'hR',
                            'R-3:H': 'hR',
                            'R-3m:H': 'hR',
                            'R-3': 'hR',
                            'R-3m': 'hR',
                            'I4/m': 'tI',
                            'I4/mmm': 'tI',
                            'Im-3': 'cI',
                            'Im-3m': 'cI',
                            'Immm': 'oI',
                            'P-1': 'aP',
                            'P-3': 'hP',
                            'P-3m': 'hP',
                            'P2/m': 'mP',
                            'P4/m': 'tP',
                            'P4/mmm': 'tP',
                            'P6/m': 'hP',
                            'P6/mmm': 'hP',
                            'Pm-3': 'cP',
                            'Pm-3m': 'cP',
                            'Pmmm': 'oP'}

    updated_laue = ''

    for l in lauegroup.split():
        if not l == '1':
            updated_laue += l

    return lauegroup_to_lattice[updated_laue]

def generate_primitive_cell(unit_cell_constants, space_group_name):
    '''For a given set of unit cell constants and space group, determine the
    corresponding primitive unit cell...'''

    uc = unit_cell(unit_cell_constants)
    sg = space_group(space_group_symbols(space_group_name).hall())
    cs = symmetry(unit_cell = uc,
                  space_group = sg)
    csp = cs.change_basis(cs.change_of_basis_op_to_primitive_setting())

    return csp.unit_cell()

if __name__ == '__main__':

    import sys

    for token in sys.argv[1:]:
        print(ersatz_pointgroup(token))
