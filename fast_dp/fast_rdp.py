#!/usr/bin/env python
# fast_rdp.py
#
# Re-data-process i.e. repeat the finishing stages of a fast_dp job, to adjust
# the resolution limit or assign some other symmetry.
from __future__ import annotations

import copy
import json
import os
import sys
import time
import traceback

import fast_dp
import fast_dp.output
from fast_dp.cell_spacegroup import (
    check_spacegroup_name,
    check_split_cell,
    generate_primitive_cell,
)
from fast_dp.logger import set_filename, write
from fast_dp.merge import merge
from fast_dp.pointgroup import decide_pointgroup
from fast_dp.scale import scale

set_filename("fast_rdp.log")


class FastRDP:
    """A class to implement fast data processing for MX beamlines (at Diamond)
    which uses XDS, Pointless, Scala and a couple of other CCP4 odds and
    ends to provide integrated and scaled data in a couple of minutes.
    """

    def __init__(self) -> None:
        with open("fast_dp.state") as fh:
            json_stuff = json.load(fh)

        for prop in json_stuff:
            # do not want to pass this along since that will limit what we
            # can reindex to...
            if prop == "_input_spacegroup":
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
        """Set the heavy atom, if appropriate. Use "-" to unset."""
        if atom == "-":
            if "atom" in self._params:
                del self._params["atom"]
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

        # FIXME for reprocessing purposes verify here that the input unit cell
        # matches the one which was used for previous fast_dp job - check
        # self._p1_unit_cell

    def reprocess(self):
        """Main routine, chain together last few steps of processing i.e.
        pointgroup, scale and merge.
        """
        write("Running on: %s" % str(os.getenv("HOSTNAME")).split(".")[0])

        # check input frame limits

        start, end = map(int, self._xds_inp["DATA_RANGE"].split())
        osc = float(self._xds_inp["OSCILLATION_RANGE"])
        osc_start = float(self._xds_inp["STARTING_ANGLE"])

        if self._first_image is not None and start < self._first_image:
            osc_start += osc * (self._first_image - start)
            start = self._first_image
            self._xds_inp["STARTING_ANGLE"] = str(osc_start)
            self._xds_inp["STARTING_FRAME"] = str(start)

        if self._last_image is not None:
            end = min(end, self._last_image)

        self._xds_inp["DATA_RANGE"] = f"{start} {end}"

        step_time = time.time()

        write("Processing images: %d -> %d" % (start, end))

        osc_end = osc_start + (end - start + 1) * osc
        write(f"Rotation range: {osc_start:.2f} -> {osc_end:.2f}")

        template = self._xds_inp["NAME_TEMPLATE_OF_DATA_FRAMES"]

        write("Template: %s" % os.path.split(template)[-1].replace("?", "#"))
        write("Wavelength: %.5f" % float(self._xds_inp["X-RAY_WAVELENGTH"]))
        write("Working in: %s" % os.getcwd())

        # just for information for the user, print all options for indexing
        # FIXME should be able to run the same from CORRECT.LP which would
        # work better....

        from fast_dp.cell_spacegroup import spacegroup_to_lattice
        from fast_dp.xds_reader import read_xds_idxref_lp

        results = read_xds_idxref_lp("IDXREF.LP")

        write("For reference, all indexing results:")
        write(
            "%3s %6s %6s %6s %6s %6s %6s"
            % ("Lattice", "a", "b", "c", "alpha", "beta", "gamma")
        )

        for r in sorted((r for r in results if isinstance(r, int)), reverse=True):
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
            self._scaling_statistics = merge(
                hklout="fast_rdp.mtz", aimless_log="aimless_rerun.log"
            )
        except RuntimeError:
            write("Merging failed")
            raise

        write("Merging point group: %s" % self._space_group)
        write(
            "Unit cell: {:6.2f} {:6.2f} {:6.2f} {:6.2f} {:6.2f} {:6.2f}".format(
                *self._unit_cell
            )
        )

        duration = time.time() - step_time
        write(
            "Reprocessing took %s (%d s) [%d reflections]"
            % (
                time.strftime("%Hh %Mm %Ss", time.gmtime(duration)),
                duration,
                self._nref,
            )
        )

        # write out json and xml
        for func, filename in [
            (fast_dp.output.write_json, "fast_rdp.json"),
            (fast_dp.output.write_ispyb_xml, "fast_rdp.xml"),
        ]:
            func(
                self._commandline,
                self._space_group,
                self._unit_cell,
                self._scaling_statistics,
                self._start_image,
                self._refined_beam,
                filename=filename,
            )


def main():
    """Main routine for fast_rdp."""
    from optparse import OptionParser

    commandline = " ".join(sys.argv)

    parser = OptionParser()

    parser.add_option("-a", "--atom", dest="atom", help="Atom type (e.g. Se)")

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
        "-N", "--last-image", dest="last_image", help="Last image for processing"
    )

    parser.add_option(
        "-r", "--resolution-high", dest="resolution_high", help="High resolution limit"
    )
    parser.add_option(
        "-R", "--resolution-low", dest="resolution_low", help="Low resolution limit"
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
        print("Fast_RDP version %s" % fast_dp.__version__)
        sys.exit(0)

    # if arg given then assume that this is a directory with a fast_dp
    # job it in, but where $user does not have access to write - so first
    # copy the files needed across

    if len(args) == 1:
        if not os.path.isdir(args[0]):
            raise RuntimeError("in this mode, provide /path/to/fast_dp/dir")
        from_dir = args[0]
        for filename in os.listdir(from_dir):
            if os.path.isdir(os.path.join(from_dir, filename)):
                continue
            import shutil

            shutil.copyfile(
                os.path.join(from_dir, filename), os.path.join(os.getcwd(), filename)
            )
    else:
        from_dir = None

    try:
        write("Fast_RDP version %s" % fast_dp.__version__)
        fast_rdp = FastRDP()
        fast_rdp._commandline = commandline
        write("Working in: %s" % os.getcwd())
        if from_dir:
            write("Working from: %s" % from_dir)

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
                write("Set spacegroup: %s" % spacegroup)
            except RuntimeError:
                write("Spacegroup %s not recognised: ignoring" % options.spacegroup)

        if options.cell:
            assert options.spacegroup
            cell = check_split_cell(options.cell)
            write("Set cell: {:.2f} {:.2f} {:.2f} {:.2f} {:.2f} {:.2f}".format(*cell))
            fast_rdp.set_input_cell(cell)

        fast_rdp.reprocess()

    except Exception as e:
        with open("fast_rdp.error", "w") as fh:
            traceback.print_exc(file=fh)
        write("Fast RDP error: %s" % str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
