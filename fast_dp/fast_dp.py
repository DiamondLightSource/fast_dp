#!/usr/bin/env python
# fast_dp.py
#
# A *quick* data reduction jiffy, for the purposes of providing an estimate
# of the quality of a data set as fast as possible along with a set of
# intensities which have been scaled reasonably well. This relies heavily on
# XDS, and forkintegrate in particular.

from __future__ import absolute_import, division, print_function

import copy
import json
import os
import re
import sys
import time
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
from fast_dp.logger import write

from optparse import SUPPRESS_HELP, OptionParser

class FastDP:
    '''A class to implement fast data processing for MX beamlines (at Diamond)
    which uses XDS, Pointless, Scala and a couple of other CCP4 odds and
    ends to provide integrated and scaled data in a couple of minutes.'''

    def __init__(self):

        # unguessable input parameters
        self._start_image = None

        # optional user inputs - the unit cell is needed twice, once for the
        # correct lattice and once for the primitive lattice which will
        # be determined from this...

        self._input_spacegroup = None
        self._input_cell = None

        # this is assigned automatically from the input cell above
        self._input_cell_p1 = None

        # user controlled resolution limits
        self._resolution_low = 30.0
        self._resolution_high = 0.0

        # job control see -j -J -k command-line options below for node names
        # see fast_dp#9
        self._n_jobs = 1
        self._n_cores = 0
        self._max_n_jobs = 0
        self._n_cpus = get_number_cpus()
        self._execution_hosts = []

        # image ranges
        self._first_image = None
        self._last_image = None

        # internal data
        self._metadata = None

        # these are the resulting not input ones... clarify this?
        self._p1_unit_cell = None
        self._unit_cell = None
        self._space_group_number = None

        # two additional results

        self._nref = 0
        self._xml_results = None
        self._refined_beam = (0, 0)

    def set_n_jobs(self, n_jobs):
        self._n_jobs = n_jobs

    def set_n_cores(self, n_cores):
        self._n_cores = n_cores

    def set_max_n_jobs(self, max_n_jobs):
        self._max_n_jobs = max_n_jobs

    def set_execution_hosts(self, execution_hosts):
        self._execution_hosts = execution_hosts
        max_n_jobs = 0
        for host in execution_hosts:
            if ':' in host:
                max_n_jobs += int(host.split(':')[1])
        if max_n_jobs:
            self._max_n_jobs = max_n_jobs
        else:
            self._max_n_jobs = len(execution_hosts)
        self._n_jobs = 0

        # add this to the metadata as "extra text"
        et = self._metadata.get('extra_text', '')
        self._metadata['extra_text'] = et + 'CLUSTER_NODES=%s\n' % \
            ' '.join(execution_hosts)

    def get_execution_hosts(self):
        return self._execution_hosts

    def set_first_image(self, first_image):
        self._first_image = first_image

    def set_last_image(self, last_image):
        self._last_image = last_image

    def set_resolution_low(self, resolution_low):
        self._resolution_low = resolution_low

    def set_resolution_high(self, resolution_high):
        self._resolution_high = resolution_high

    def set_start_image(self, start_image):
        '''Set the image to work from: in the majority of cases this will
        be sufficient. This returns a list of image numbers which may be
        missing.'''

        assert(self._start_image is None)

        # check input is image file
        if not os.path.isfile(start_image):
            raise RuntimeError('no image provided: data collection cancelled?')

        check_file_readable(start_image)

        self._start_image = start_image
        self._metadata = read_image_metadata(self._start_image)

        # check that all of the images are present

        matching = self._metadata['matching']

        missing = []

        for j in range(min(matching), max(matching)):
            if not j in matching:
                missing.append(j)

        return missing

    def set_beam(self, beam):
        '''Set the beam centre, in mm, in the Mosflm reference frame.'''

        assert(self._metadata)
        assert(len(beam) == 2)

        self._metadata['beam'] = beam

    def set_distance(self, distance):
        '''Set the detector distance, in mm.'''

        assert(self._metadata)

        self._metadata['distance'] = distance

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

    def _read_image_metadata(self):
        '''Get the information from the start image to the metadata bucket.
        For internal use only.'''

        assert(self._start_image)

    def get_metadata_item(self, item):
        '''Get a specific item from the metadata.'''

        assert(self._metadata)
        assert(item in self._metadata)

        return self._metadata[item]

    def process(self):
        '''Main routine, chain together all of the steps imported from
        autoindex, integrate, pointgroup, scale and merge.'''

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

        # first if the number of jobs was set to 0, decide something sensible.
        # this should be jobs of a minimum of 5 degrees, 10 frames.

        if self._n_jobs == 0:
            phi = self._metadata['oscillation'][1]

            if phi == 0.0:
                raise RuntimeError('grid scan data')

            wedge = max(10, int(round(5.0 / phi)))
            frames = self._metadata['end'] - self._metadata['start'] + 1
            n_jobs = int(round(frames / wedge))
            if self._max_n_jobs > 0:
                if n_jobs > self._max_n_jobs:
                    n_jobs = self._max_n_jobs
            self.set_n_jobs(n_jobs)

        write('Number of jobs: %d' % self._n_jobs)
        write('Number of cores: %d' % self._n_cores)

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

        try:
            self._p1_unit_cell = autoindex(self._metadata,
                                           input_cell = self._input_cell_p1)
        except Exception as e:
            traceback.print_exc(file = open('fast_dp.error', 'w'))
            write('Autoindexing error: %s' % e)
            return

        try:
            mosaics = integrate(self._metadata, self._p1_unit_cell,
                                self._resolution_low, self._n_jobs,
                                self._n_cores)
            write('Mosaic spread: %.2f < %.2f < %.2f' % tuple(mosaics))
        except RuntimeError as e:
            traceback.print_exc(file = open('fast_dp.error', 'w'))
            write('Integration error: %s' % e)
            return

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
            self._xml_results = merge()
        except RuntimeError as e:
            write('Merging error: %s' % e)
            return

        write('Merging point group: %s' % self._space_group)
        write('Unit cell: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % \
              self._unit_cell)

        duration = time.time() - step_time
        write('Processing took %s (%d s) [%d reflections]' %
              (time.strftime('%Hh %Mm %Ss',
                             time.gmtime(duration)), duration,
               self._nref))
        write('RPS: %.1f' % (float(self._nref) / duration))

        # write out json and xml
        for func in (fast_dp.output.write_json, fast_dp.output.write_ispyb_xml):
          func(self._commandline, self._space_group,
               self._unit_cell, self._xml_results,
               self._start_image, self._refined_beam)

def main():
    '''Main routine for fast_dp.'''

    os.environ['FAST_DP_FORKINTEGRATE'] = '1'

    commandline = ' '.join(sys.argv)

    parser = OptionParser(usage="fast_dp [options] imagefile")

    parser.add_option("-?", action="help", help=SUPPRESS_HELP)

    parser.add_option('-b', '--beam', dest = 'beam',
                      help = 'Beam centre: x, y (mm)')

    parser.add_option('-d', '--distance', dest = 'distance',
                      help = 'Detector distance: d (mm)')

    parser.add_option('-a', '--atom', dest = 'atom',
                      help = 'Atom type (e.g. Se)')

    parser.add_option('-j', '--number-of-jobs', dest = 'number_of_jobs',
                      help = 'Number of jobs for integration')
    parser.add_option('-k', '--number-of-cores', dest = 'number_of_cores',
                      help = 'Number of cores for integration')
    parser.add_option('-J', '--maximum-number-of-jobs',
                      dest = 'maximum_number_of_jobs',
                      help = 'Maximum number of jobs for integration')
    parser.add_option('-e', '--execution-hosts',
                      dest = 'execution_hosts',
                      help = 'names for execution hosts for forkxds')

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

    parser.add_option('-l', '--lib-name', dest = 'lib_name',
                      help = 'HDF5 reader library (i.e. neggia etc.)')

    parser.add_option('--version', dest='version', action='store_true',
                      default=False, help='Print fast_dp version')

    (options, args) = parser.parse_args()

    if options.version:
      print('Fast_DP version %s' % fast_dp.__version__)
      sys.exit(0)

    if len(args) != 1:
      parser.error("You must point to one image of the dataset to process")

    image = args[0]

    xia2_format = re.match(r"^(.*):(\d+):(\d+)$", image)
    if xia2_format:
      # Image can be given in xia2-style format, ie.
      #   set_of_images_00001.cbf:1:5000
      # to select images 1 to 5000. Resolve any conflicts
      # with -1/-N in favour of the explicit arguments.
      image = xia2_format.group(1)
      if not options.first_image:
        options.first_image = xia2_format.group(2)
      if not options.last_image:
        options.last_image = xia2_format.group(3)

    if options.lib_name:
        from image_readers import set_lib_name
        set_lib_name(options.lib_name)

    try:
        write('Fast_DP version %s' % fast_dp.__version__)
        finst = FastDP()
        finst._commandline = commandline
        write('Starting image: %s' % image)
        missing = finst.set_start_image(image)
        if options.beam:
            x, y = tuple(map(float, options.beam.split(',')))
            finst.set_beam((x, y))

        if options.distance:
            finst.set_distance(float(options.distance))

        if options.atom:
            finst.set_atom(options.atom)

        if options.maximum_number_of_jobs:
            finst.set_max_n_jobs(int(options.maximum_number_of_jobs))

        if options.execution_hosts:
            finst.set_execution_hosts(options.execution_hosts.split(','))
            write('Execution hosts: %s' % ' '.join(finst.get_execution_hosts()))

        if options.number_of_jobs:
            if options.maximum_number_of_jobs:
                n_jobs = min(int(options.number_of_jobs),
                             int(options.maximum_number_of_jobs))
            else:
                n_jobs = int(options.number_of_jobs)
            finst.set_n_jobs(n_jobs)

        if options.number_of_cores:
            n_cores = int(options.number_of_cores)
            finst.set_n_cores(n_cores)

        if options.first_image:
            first_image = int(options.first_image)
            missing = [m for m in missing if m >= first_image]
            finst.set_first_image(first_image)

        if options.last_image:
            last_image = int(options.last_image)
            missing = [m for m in missing if m <= last_image]
            finst.set_last_image(last_image)

        if missing:
            raise RuntimeError('images missing: %s' % \
                ' '.join(map(str, missing)))

        if options.resolution_low:
            finst.set_resolution_low(float(options.resolution_low))

        if options.resolution_high:
            finst.set_resolution_high(float(options.resolution_high))

        # must input spacegroup first as unpacking of the unit cell
        # will depend on the centering operation...

        if options.spacegroup:
            try:
                spacegroup = check_spacegroup_name(options.spacegroup)
                finst.set_input_spacegroup(spacegroup)
                write('Set spacegroup: %s' % spacegroup)
            except RuntimeError:
                write('Spacegroup %s not recognised: ignoring' % \
                      options.spacegroup)

        if options.cell:
            assert(options.spacegroup)
            cell = check_split_cell(options.cell)
            write('Set cell: %.2f %.2f %.2f %.2f %.2f %.2f' % cell)
            finst.set_input_cell(cell)

        finst.process()

    except Exception as e:
        traceback.print_exc(file = open('fast_dp.error', 'w'))
        write('Fast DP error: %s' % str(e))

    json_stuff = { }
    for prop in dir(finst):
        ignore = ['_read_image_metadata']
        if not prop.startswith('_') or prop.startswith('__'):
            continue
        if prop in ignore:
            continue
        json_stuff[prop] = getattr(finst, prop)
    with open('fast_dp.state', 'wb') as fh:
      json.dump(json_stuff, fh)

if __name__ == '__main__':
    main()
