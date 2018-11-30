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
from fast_dp.cell_spacegroup import (
    check_spacegroup_name,
    check_split_cell,
    generate_primitive_cell,
)
from fast_dp.image_names import find_matching_images
import fast_dp.image_readers
import fast_dp.output

from fast_dp.autoindex import autoindex
from fast_dp.integrate import integrate
from fast_dp.scale import scale
from fast_dp.merge import merge
from fast_dp.pointgroup import decide_pointgroup
from fast_dp.logger import write

from optparse import SUPPRESS_HELP, OptionParser


class FastDP:
    """A class to implement fast data processing for MX beamlines (at Diamond)
    which uses XDS, Pointless, Scala and a couple of other CCP4 odds and
    ends to provide integrated and scaled data in a couple of minutes."""

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
        self._params = {}

        # these are the resulting not input ones... clarify this?
        self._p1_unit_cell = None
        self._unit_cell = None
        self._space_group_number = None

        # two additional results

        self._nref = 0
        self._scaling_statistics = None
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
            if ":" in host:
                max_n_jobs += int(host.split(":")[1])
        if max_n_jobs:
            self._max_n_jobs = max_n_jobs
        else:
            self._max_n_jobs = len(execution_hosts)
        self._n_jobs = 0
        self._xds_inp["CLUSTER_NODES"] = " ".join(execution_hosts)

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
        """Set the image to work from: in the majority of cases this will
        be sufficient. This returns a list of image numbers which may be
        missing."""

        assert self._start_image is None

        # check input is image file, and exists
        if not os.path.exists(start_image):
            raise RuntimeError("%s does not exist" % start_image)
        if not os.path.isfile(start_image):
            raise ValueError("%s is not a file" % start_image)

        fast_dp.image_readers.check_file_readable(start_image)

        self._start_image = start_image
        self._xds_inp = fast_dp.image_readers.read_image_metadata_dxtbx(
            self._start_image
        )

        missing = []
        # list image numbers which are missing from this sequence - iff ! h5
        template = self._xds_inp["NAME_TEMPLATE_OF_DATA_FRAMES"]
        if template.split(".")[-1] != "h5":
            directory, template = os.path.split(template.replace("?", "#"))
            matching = find_matching_images(template, directory)
            every = set(range(min(matching), max(matching) + 1))
            missing = list(sorted(every - set(matching)))

        return missing

    def set_beam(self, beam):
        """Set the beam centre, in mm, in the Mosflm reference frame."""

        assert self._xds_inp
        assert len(beam) == 2

        # use XDS_INP parameters to map these to XDS description
        orgx = beam[1] / self._xds_inp["QX"]
        orgy = beam[0] / self._xds_inp["QY"]
        self._xds_inp["ORGX"] = orgx
        self._xds_inp["ORGY"] = orgy

    def set_distance(self, distance):
        """Set the detector distance, in mm."""

        assert self._xds_inp
        self._xds_inp["DETECTOR_DISTANCE"] = distance

    def set_atom(self, atom):
        """Set the heavy atom, if appropriate. Use "-" to unset"""
        if atom == "-":
            if "atom" in self._params:
                del (self._params["atom"])
        else:
            self._params["atom"] = atom

    # N.B. these two methods assume that the input unit cell etc.
    # has already been tested at the option parsing stage...

    def set_input_spacegroup(self, input_spacegroup):
        self._input_spacegroup = input_spacegroup

    def set_input_cell(self, input_cell):

        self._input_cell = input_cell

        # convert this to a primitive cell based on the centring
        # operation implied by the spacegroup

        assert self._input_spacegroup

        self._input_cell_p1 = generate_primitive_cell(
            self._input_cell, self._input_spacegroup
        ).parameters()

    def process(self):
        """Main routine, chain together all of the steps imported from
        autoindex, integrate, pointgroup, scale and merge."""

        write("Running on: %s" % str(os.getenv("HOSTNAME")).split(".")[0])

        # check input frame limits

        start, end = map(int, self._xds_inp["DATA_RANGE"].split())
        osc = float(self._xds_inp["OSCILLATION_RANGE"])
        osc_start = float(self._xds_inp["STARTING_ANGLE"])

        if osc == 0.0:
            raise RuntimeError("grid scan data")

        if self._first_image is not None:
            if start < self._first_image:
                osc_start += osc * (self._first_image - start)
                start = self._first_image
                self._xds_inp["STARTING_ANGLE"] = str(osc_start)
                self._xds_inp["STARTING_FRAME"] = str(start)

        if self._last_image is not None:
            end = min(end, self._last_image)

        self._xds_inp["DATA_RANGE"] = "%s %s" % (start, end)

        # first if the number of jobs was set to 0, decide something sensible.
        # this should be jobs of a minimum of 5 degrees, 10 frames.

        wedge = max(10, int(round(5.0 / osc)))
        wedge = min(wedge, end - start)

        self._xds_inp["BACKGROUND_RANGE"] = "%d %d" % (start, start + wedge)

        if self._n_jobs == 0:
            frames = end - start + 1
            n_jobs = int(round(frames / wedge))
            if self._max_n_jobs > 0:
                if n_jobs > self._max_n_jobs:
                    n_jobs = self._max_n_jobs
            self.set_n_jobs(n_jobs)

        write("Number of jobs: %d" % self._n_jobs)
        write("Number of cores: %d" % self._n_cores)

        step_time = time.time()

        write("Processing images: %d -> %d" % (start, end))
        osc_end = osc_start + (end - start + 1) * osc
        write("Rotation range: %.2f -> %.2f" % (osc_start, osc_end))

        template = self._xds_inp["NAME_TEMPLATE_OF_DATA_FRAMES"]

        write("Template: %s" % os.path.split(template)[-1].replace("?", "#"))
        write("Wavelength: %.5f" % float(self._xds_inp["X-RAY_WAVELENGTH"]))
        write("Working in: %s" % os.getcwd())

        try:
            self._p1_unit_cell = autoindex(
                self._xds_inp, input_cell=self._input_cell_p1
            )
        except Exception:
            write("Autoindexing failed")
            raise

        try:
            mosaics = integrate(
                self._xds_inp,
                self._p1_unit_cell,
                self._resolution_low,
                self._n_jobs,
                self._n_cores,
            )
            write("Mosaic spread: %.2f < %.2f < %.2f" % tuple(mosaics))
        except RuntimeError:
            write("Integration failed")
            raise

        try:
            metadata = copy.deepcopy(self._xds_inp)

            cell, sg_num, resol = decide_pointgroup(
                self._p1_unit_cell, metadata, input_spacegroup=self._input_spacegroup
            )
            self._unit_cell = cell
            self._space_group_number = sg_num

            if not self._resolution_high:
                self._resolution_high = resol
        except RuntimeError:
            write("Pointgroup determination failed")
            raise

        try:
            if self._params.get("atom", None):
                self._xds_inp["FRIEDEL'S_LAW"] = "FALSE"
            else:
                self._xds_inp["FRIEDEL'S_LAW"] = "TRUE"
            self._unit_cell, self._space_group, self._nref, beam_pixels = scale(
                self._unit_cell,
                self._xds_inp,
                self._space_group_number,
                self._resolution_high,
            )
            self._refined_beam = (
                beam_pixels[1] * float(self._xds_inp["QY"]),
                beam_pixels[0] * float(self._xds_inp["QX"]),
            )
        except RuntimeError:
            write("Scaling failed")
            raise

        try:
            self._scaling_statistics = merge()
        except RuntimeError:
            write("Merging failed")
            raise

        write("Merging point group: %s" % self._space_group)
        write("Unit cell: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f" % self._unit_cell)

        duration = time.time() - step_time
        write(
            "Processing took %s (%d s) [%d reflections]"
            % (
                time.strftime("%Hh %Mm %Ss", time.gmtime(duration)),
                duration,
                self._nref,
            )
        )
        write("RPS: %.1f" % (float(self._nref) / duration))

        # write out json and xml
        for func in (fast_dp.output.write_json, fast_dp.output.write_ispyb_xml):
            func(
                self._commandline,
                self._space_group,
                self._unit_cell,
                self._scaling_statistics,
                self._start_image,
                self._refined_beam,
            )


def main():
    """Main routine for fast_dp."""

    os.environ["FAST_DP_FORKINTEGRATE"] = "1"

    commandline = " ".join(sys.argv)

    parser = OptionParser(usage="fast_dp [options] imagefile")

    parser.add_option("-?", action="help", help=SUPPRESS_HELP)

    parser.add_option("-b", "--beam", dest="beam", help="Beam centre: x, y (mm)")

    parser.add_option(
        "-d", "--distance", dest="distance", help="Detector distance: d (mm)"
    )

    parser.add_option("-a", "--atom", dest="atom", help="Atom type (e.g. Se)")

    parser.add_option(
        "-j",
        "--number-of-jobs",
        dest="number_of_jobs",
        help="Number of jobs for integration",
    )
    parser.add_option(
        "-k",
        "--number-of-cores",
        dest="number_of_cores",
        help="Number of cores for integration",
    )
    parser.add_option(
        "-J",
        "--maximum-number-of-jobs",
        dest="maximum_number_of_jobs",
        help="Maximum number of jobs for integration",
    )
    parser.add_option(
        "-e",
        "--execution-hosts",
        dest="execution_hosts",
        help="names for execution hosts for forkxds",
    )

    parser.add_option(
        "-c",
        "--cell",
        dest="cell",
        help="Cell constants for processing, needs spacegroup",
    )
    parser.add_option(
        "-s",
        "--spacegroup",
        dest="spacegroup",
        help="Spacegroup for scaling and merging",
    )

    parser.add_option(
        "-1", "--first-image", dest="first_image", help="First image for processing"
    )
    parser.add_option(
        "-N", "--last-image", dest="last_image", help="First image for processing"
    )

    parser.add_option(
        "-r", "--resolution-high", dest="resolution_high", help="High resolution limit"
    )
    parser.add_option(
        "-R", "--resolution-low", dest="resolution_low", help="Low resolution limit"
    )

    parser.add_option(
        "-l",
        "--lib-name",
        dest="lib_name",
        help="HDF5 reader library (i.e. neggia etc.)",
    )

    parser.add_option(
        "--version",
        dest="version",
        action="store_true",
        default=False,
        help="Print fast_dp version",
    )

    (options, args) = parser.parse_args()

    if options.version:
        print("Fast_DP version %s" % fast_dp.__version__)
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
        fast_dp.image_readers.set_lib_name(options.lib_name)

    try:
        write("Fast_DP version %s" % fast_dp.__version__)
        finst = FastDP()
        finst._commandline = commandline
        write("Starting image: %s" % image)
        missing = finst.set_start_image(image)
        if options.beam:
            x, y = tuple(map(float, options.beam.split(",")))
            finst.set_beam((x, y))

        if options.distance:
            finst.set_distance(float(options.distance))

        if options.atom:
            finst.set_atom(options.atom)

        if options.maximum_number_of_jobs:
            finst.set_max_n_jobs(int(options.maximum_number_of_jobs))

        if options.execution_hosts:
            finst.set_execution_hosts(options.execution_hosts.split(","))
            write("Execution hosts: %s" % " ".join(finst.get_execution_hosts()))

        if options.number_of_jobs:
            if options.maximum_number_of_jobs:
                n_jobs = min(
                    int(options.number_of_jobs), int(options.maximum_number_of_jobs)
                )
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
            raise RuntimeError("images missing: %s" % " ".join(map(str, missing)))

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
                write("Set spacegroup: %s" % spacegroup)
            except RuntimeError:
                write("Spacegroup %s not recognised: ignoring" % options.spacegroup)

        if options.cell:
            assert options.spacegroup
            cell = check_split_cell(options.cell)
            write("Set cell: %.2f %.2f %.2f %.2f %.2f %.2f" % cell)
            finst.set_input_cell(cell)

        finst.process()

    except Exception as e:
        with open("fast_dp.error", "w") as fh:
            traceback.print_exc(file=fh)
        write("Fast DP error: %s" % str(e))
        sys.exit(1)

    finally:
        json_stuff = {}
        for prop in dir(finst):
            ignore = []
            if not prop.startswith("_") or prop.startswith("__"):
                continue
            if prop in ignore:
                continue
            json_stuff[prop] = getattr(finst, prop)
        with open("fast_dp.state", "wb") as fh:
            json.dump(json_stuff, fh)


if __name__ == "__main__":
    main()
