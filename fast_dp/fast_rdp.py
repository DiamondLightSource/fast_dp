#!/usr/bin/env python
# fast_rdp.py
#
# Re-data-process i.e. repeat the finishing stages of a fast_dp job, to adjust
# the resolution limit or assign some other symmetry.

from __future__ import absolute_import, division, print_function

import json
import sys
import os
import time
import copy
import traceback

import fast_dp
from fast_dp.run_job import get_number_cpus
from fast_dp.cell_spacegroup import check_spacegroup_name, check_split_cell, \
     generate_primitive_cell
import fast_dp.output

from fast_dp.image_readers import read_image_metadata, check_file_readable

from fast_dp.autoindex import autoindex
from fast_dp.integrate import integrate
from fast_dp.scale import scale
from fast_dp.merge import merge
from fast_dp.pointgroup import decide_pointgroup
from fast_dp.logger import write, set_filename
set_filename('fast_rdp.log')

class FastRDP:
    '''A class to implement fast data processing for MX beamlines (at Diamond)
    which uses XDS, Pointless, Scala and a couple of other CCP4 odds and
    ends to provide integrated and scaled data in a couple of minutes.'''

    def __init__(self):

        with open('fast_dp.state', 'rb') as fh:
            json_stuff = json.load(fh)

        for prop in json_stuff:
            # do not want to pass this along since that will limit what we
            # can reindex to...
            if prop == '_input_spacegroup':
                self._input_spacegroup = None
                continue
            setattr(self, prop, json_stuff[prop])

    def set_first_image(self, first_image):
        self._first_image = first_image

    def set_last_image(self, last_image):
        self._last_image = last_image

    def set_resolution_low(self, resolution_low):
        self._resolution_low = resolution_low

    def set_resolution_high(self, resolution_high):
        self._resolution_high = resolution_high

    def set_atom(self, atom):
        '''Set the heavy atom, if appropriate.'''

        assert(self._metadata)

        self._metadata['atom'] = atom

    # N.B. these two methods assume that the input unit cell etc.
    # has already been tested at the option parsing stage...

    def set_input_spacegroup(self, input_spacegroup):
        self._input_spacegroup = input_spacegroup

    def set_input_cell(self, input_cell):

        self._input_cell = input_cell

        # convert this to a primitive cell based on the centring
        # operation implied by the spacegroup

        assert(self._input_spacegroup)

        self._input_cell_p1 = generate_primitive_cell(
            self._input_cell, self._input_spacegroup).parameters()

        # FIXME for reprocessing purposes verify here that the input unit cell
        # matches the one which was used for previous fast_dp job - check
        # self._p1_unit_cell

    def get_metadata_item(self, item):
        '''Get a specific item from the metadata.'''

        assert(self._metadata)
        assert(item in self._metadata)

        return self._metadata[item]

    def reprocess(self):
        '''Main routine, chain together last few steps of processing i.e.
        pointgroup, scale and merge.'''

        try:

            hostname = os.environ['HOSTNAME'].split('.')[0]
            write('Running on: %s' % hostname)

        except Exception:
            pass

        # check input frame limits

        if not self._first_image is None:
            if self._metadata['start'] < self._first_image:
                start = self._metadata['start']
                self._metadata['start'] = self._first_image
                self._metadata['phi_start'] += self._metadata['phi_width'] * \
                                               (self._first_image - start)

        if not self._last_image is None:
            if self._metadata['end'] > self._last_image:
                self._metadata['end'] = self._last_image

        step_time = time.time()

        write('Processing images: %d -> %d' % (self._metadata['start'],
                                               self._metadata['end']))

        phi_end = self._metadata['phi_start'] + self._metadata['phi_width'] * \
                  (self._metadata['end'] - self._metadata['start'] + 1)

        write('Phi range: %.2f -> %.2f' % (self._metadata['phi_start'],
                                           phi_end))

        write('Template: %s' % self._metadata['template'])
        write('Wavelength: %.5f' % self._metadata['wavelength'])
        write('Working in: %s' % os.getcwd())

        # just for information for the user, print all options for indexing
        # FIXME should be able to run the same from CORRECT.LP which would
        # work better....

        from fast_dp.xds_reader import read_xds_idxref_lp
        from fast_dp.cell_spacegroup import spacegroup_to_lattice

        results = read_xds_idxref_lp('IDXREF.LP')

        write('For reference, all indexing results:')
        write('%3s %6s %6s %6s %6s %6s %6s' % \
            ('Lattice', 'a', 'b', 'c', 'alpha', 'beta', 'gamma'))

        for r in reversed(sorted(results)):
            if not type(r) == type(1):
                continue
            cell = results[r][1]
            write('%7s %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % \
                (spacegroup_to_lattice(r), cell[0], cell[1], cell[2],
                cell[3], cell[4], cell[5]))

        try:

            # FIXME in here will need a mechanism to take the input
            # spacegroup, determine the corresponding pointgroup
            # and then apply this (or verify that it is allowed then
            # select)

            metadata = copy.deepcopy(self._metadata)

            cell, sg_num, resol = decide_pointgroup(
                self._p1_unit_cell, metadata,
                input_spacegroup = self._input_spacegroup)
            self._unit_cell = cell
            self._space_group_number = sg_num

            if not self._resolution_high:
                self._resolution_high = resol

        except RuntimeError as e:
            write('Pointgroup error: %s' % e)
            return

        try:
            self._unit_cell, self._space_group, self._nref, beam_pixels = \
            scale(self._unit_cell, self._metadata, self._space_group_number, \
                   self._resolution_high)
            self._refined_beam = (self._metadata['pixel'][1] * beam_pixels[1],
                                  self._metadata['pixel'][0] * beam_pixels[0])

        except RuntimeError as e:
            write('Scaling error: %s' % e)
            return

        try:
            n_images = self._metadata['end'] - self._metadata['start'] + 1
            self._xml_results = merge(hklout='fast_rdp.mtz',
                                      aimless_log='aimless_rerun.log')
        except RuntimeError as e:
            write('Merging error: %s' % e)
            return

        write('Merging point group: %s' % self._space_group)
        write('Unit cell: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % \
              self._unit_cell)

        duration = time.time() - step_time
        write('Reprocessing took %s (%d s) [%d reflections]' %
              (time.strftime('%Hh %Mm %Ss',
                             time.gmtime(duration)), duration,
               self._nref))

        # write out json and xml
        for func, filename in [ (fast_dp.output.write_json, 'fast_rdp.json'),
                                (fast_dp.output.write_ispyb_xml, 'fast_rdp.xml') ]:
          func(self._commandline, self._space_group,
               self._unit_cell, self._xml_results,
               self._start_image, self._refined_beam,
               filename=filename)

def main():
    '''Main routine for fast_rdp.'''

    os.environ['FAST_DP_FORKINTEGRATE'] = '1'

    from optparse import OptionParser

    commandline = ' '.join(sys.argv)

    parser = OptionParser()

    parser.add_option('-a', '--atom', dest = 'atom',
                      help = 'Atom type (e.g. Se)')

    parser.add_option('-c', '--cell', dest = 'cell',
                      help = 'Cell constants for processing, needs spacegroup')
    parser.add_option('-s', '--spacegroup', dest = 'spacegroup',
                      help = 'Spacegroup for scaling and merging')

    parser.add_option('-1', '--first-image', dest = 'first_image',
                      help = 'First image for processing')
    parser.add_option('-N', '--last-image', dest = 'last_image',
                      help = 'First image for processing')

    parser.add_option('-r', '--resolution-high', dest = 'resolution_high',
                      help = 'High resolution limit')
    parser.add_option('-R', '--resolution-low', dest = 'resolution_low',
                      help = 'Low resolution limit')

    parser.add_option('--version', dest='version', action='store_true',
                      default=False, help='Print fast_dp version')

    (options, args) = parser.parse_args()

    if options.version:
        print('Fast_RDP version %s' % fast_dp.__version__)
        sys.exit(0)

    # if arg given then assume that this is a directory with a fast_dp
    # job it in, but where $user does not have access to write - so first
    # copy the files needed across

    if len(args) == 1:
        if not os.path.isdir(args[0]):
            raise RuntimeError('in this mode, provide /path/to/fast_dp/dir')
        from_dir = args[0]
        for filename in os.listdir(from_dir):
            if os.path.isdir(os.path.join(from_dir, filename)):
                continue
            import shutil
            shutil.copyfile(os.path.join(from_dir, filename),
                            os.path.join(os.getcwd(), filename))
    else:
        from_dir = None

    try:
        write('Fast_DP version %s' % fast_dp.__version__)
        fast_rdp = FastRDP()
        fast_rdp._commandline = commandline
        write('Working in: %s' % os.getcwd())
        if from_dir:
            write('Working from: %s' % from_dir)

        if options.atom:
            fast_rdp.set_atom(options.atom)

        if options.first_image:
            first_image = int(options.first_image)
            fast_rdp.set_first_image(first_image)

        if options.last_image:
            last_image = int(options.last_image)
            fast_rdp.set_last_image(last_image)

        if options.resolution_low:
            fast_rdp.set_resolution_low(float(options.resolution_low))

        if options.resolution_high:
            fast_rdp.set_resolution_high(float(options.resolution_high))

        # must input spacegroup first as unpacking of the unit cell
        # will depend on the centering operation...

        if options.spacegroup:
            try:
                spacegroup = check_spacegroup_name(options.spacegroup)
                fast_rdp.set_input_spacegroup(spacegroup)
                write('Set spacegroup: %s' % spacegroup)
            except RuntimeError as e:
                write('Spacegroup %s not recognised: ignoring' % \
                      options.spacegroup)

        if options.cell:
            assert(options.spacegroup)
            cell = check_split_cell(options.cell)
            write('Set cell: %.2f %.2f %.2f %.2f %.2f %.2f' % cell)
            fast_rdp.set_input_cell(cell)

        fast_rdp.reprocess()

    except Exception as e:
        traceback.print_exc(file = open('fast_rdp.error', 'w'))
        write('Fast RDP error: %s' % str(e))

if __name__ == '__main__':
    main()
