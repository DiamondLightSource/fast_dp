from __future__ import absolute_import, division, print_function

import os
import time

from fast_dp.logger import write

from fast_dp.image_names import (
    image2template_directory,
    find_matching_images,
    template_directory_number2image,
)

from fast_dp.run_job import run_job


def check_file_readable(filename):
    """Check that the file filename exists and that it can be read. Returns
    only if everything is OK."""

    if not os.path.exists(filename):
        raise RuntimeError("file %s not found" % filename)

    if not os.access(filename, os.R_OK):
        raise RuntimeError("file %s not readable" % filename)

    return


def get_dectris_serial_no(record):
    if "S/N" not in record:
        return "0"
    tokens = record.split()
    return tokens[tokens.index("S/N") + 1]


def find_hdf5_lib(lib_name=None):
    if not hasattr(find_hdf5_lib, "cache"):
        lib_name = lib_name or "dectris-neggia.so"
        for d in os.environ["PATH"].split(os.pathsep):
            if os.path.exists(os.path.join(d, lib_name)):
                library = os.path.join(d, lib_name)
                break
        else:
            library = ""
        setattr(find_hdf5_lib, "cache", library)
    return getattr(find_hdf5_lib, "cache")


try:
    import bz2
except BaseException:  # intentional
    bz2 = None

try:
    import gzip
except BaseException:  # intentional
    gzip = None


def is_bz2(filename):
    if ".bz2" not in filename[-4:]:
        return False
    return "BZh" in open(filename, "rb").read(3)


def is_gzip(filename):
    if ".gz" not in filename[-3:]:
        return False
    magic = open(filename, "rb").read(2)
    return ord(magic[0]) == 0x1F and ord(magic[1]) == 0x8B


def open_file(filename, mode="rb", url=False):
    if is_bz2(filename):
        if bz2 is None:
            raise RuntimeError("bz2 file provided without bz2 module")

        def fh_func():
            return bz2.BZ2File(filename, mode)

    elif is_gzip(filename):
        if gzip is None:
            raise RuntimeError("gz file provided without gzip module")

        def fh_func():
            return gzip.GzipFile(filename, mode)

    else:

        def fh_func():
            return open(filename, mode)

    return fh_func()


def XDS_INP_to_dict(inp_text):
    result = {}
    for record in inp_text.split("\n"):
        useful = record.split("!")[0].strip()
        if not useful:
            continue
        if useful.count("=") > 1:
            # assume tokens of form key=value key=value
            tokens = useful.replace("=", " ").split()
            for j in range(useful.count("=")):
                key = tokens[2 * j].strip()
                value = tokens[2 * j + 1].strip()
                # handle multiples gracelessly
                if key in result:
                    if not isinstance(result[key], list):
                        result[key] = [result[key]]
                        result[key].append(value)
                    else:
                        result[key].append(value)
                else:
                    result[key] = value
        else:
            tokens = useful.split("=")
            key = tokens[0].strip()
            value = tokens[1].strip()
            # handle multiples gracelessly
            if key in result:
                if not isinstance(result[key], list):
                    result[key] = [result[key]]
                    result[key].append(value)
                else:
                    result[key].append(value)
            else:
                result[key] = value

    # add neggia-type plugin if needed
    if result["NAME_TEMPLATE_OF_DATA_FRAMES"].endswith(".h5"):
        global __lib_name
        result["LIB"] = find_hdf5_lib(lib_name=__lib_name)

    return result


def failover_cbf(cbf_file):
    """CBF files from the latest update to the PILATUS detector cause a
    segmentation fault in diffdump. This is a workaround."""

    header = {}

    header["two_theta"] = 0.0

    for record in open_file(cbf_file):
        if "_array_data.data" in record:
            break

        if "EIGER 1M" in record.upper():
            header["detector_class"] = "eiger 1M"
            header["detector"] = "dectris"
            header["size"] = (1065, 1030)
            header["serial_number"] = get_dectris_serial_no(record)
            continue

        if "EIGER 4M" in record.upper():
            header["detector_class"] = "eiger 4M"
            header["detector"] = "dectris"
            header["size"] = (2176, 2070)
            header["serial_number"] = get_dectris_serial_no(record)
            continue

        if "EIGER 9M" in record.upper():
            header["detector_class"] = "eiger 9M"
            header["detector"] = "dectris"
            header["size"] = (3269, 3110)
            header["serial_number"] = get_dectris_serial_no(record)
            continue

        if "EIGER 16M" in record.upper():
            header["detector_class"] = "eiger 16M"
            header["detector"] = "dectris"
            header["size"] = (4371, 4150)
            header["serial_number"] = get_dectris_serial_no(record)
            continue

        if "PILATUS 2M" in record:
            header["detector_class"] = "pilatus 2M"
            header["detector"] = "dectris"
            header["size"] = (1679, 1475)
            header["serial_number"] = get_dectris_serial_no(record)
            continue

        if "PILATUS 6M" in record:
            header["detector_class"] = "pilatus 6M"
            header["detector"] = "dectris"
            header["size"] = (2527, 2463)
            header["serial_number"] = get_dectris_serial_no(record)
            continue

        if "PILATUS3 6M" in record:
            header["detector_class"] = "pilatus 6M"
            header["detector"] = "dectris"
            header["size"] = (2527, 2463)
            header["serial_number"] = get_dectris_serial_no(record)
            continue

        if "PILATUS 12M" in record:
            header["detector_class"] = "pilatus 12M"
            header["detector"] = "dectris"
            header["size"] = (5071, 2463)
            header["serial_number"] = get_dectris_serial_no(record)
            continue

        if "Detector: ADSC HF-4M" in record:
            header["detector_class"] = "adsc 4M"
            header["detector"] = "adsc-pad"
            header["size"] = (2290, 2100)
            header["serial_number"] = record.replace(",", "").split()[-1]
            continue

        if "Start_angle" in record:
            header["phi_start"] = float(record.split()[-2])
            continue

        if "Angle_increment" in record:
            header["phi_width"] = float(record.split()[-2])
            header["phi_end"] = header["phi_start"] + header["phi_width"]
            header["oscillation"] = header["phi_start"], header["phi_width"]
            continue

        if "Exposure_period" in record:
            header["exposure_time"] = float(record.split()[-2])
            continue

        if "Detector_distance" in record:
            header["distance"] = 1000 * float(record.split()[2])
            continue

        if "Oscillation_axis" in record:
            header["oscillation_axis"] = record.split("axis")[-1].strip()

        if "Wavelength" in record:
            header["wavelength"] = float(record.split()[-2])
            continue

        if "Pixel_size" in record:
            header["pixel"] = (
                1000 * float(record.split()[2]),
                1000 * float(record.split()[5]),
            )
            continue

        if "Count_cutoff" in record:
            header["saturation"] = int(record.split()[2])

        if "Silicon sensor" in record:
            header["sensor"] = 1000 * float(record.split()[4])

        if "Beam_xy" in record:
            beam_pixels = map(
                float,
                record.replace("(", "").replace(")", "").replace(",", "").split()[2:4],
            )

            # for CBF images need to swap these to put in XDS mosflm
            # coordinate frame...
            header["beam"] = (
                beam_pixels[0] * header["pixel"][0],
                beam_pixels[1] * header["pixel"][1],
            )

            continue

        # try to get the date etc. literally.

        try:
            datestring = record.split()[-1].split(".")[0]
            format = "%Y-%b-%dT%H:%M:%S"
            struct_time = time.strptime(datestring, format)
            header["date"] = time.asctime(struct_time)
            header["epoch"] = time.mktime(struct_time)

        except BaseException:
            pass

        try:
            datestring = record.split()[-1].split(".")[0]
            format = "%Y-%m-%dT%H:%M:%S"
            struct_time = time.strptime(datestring, format)
            header["date"] = time.asctime(struct_time)
            header["epoch"] = time.mktime(struct_time)

        except BaseException:
            pass

        try:
            datestring = record.replace("#", "").strip().split(".")[0]
            format = "%Y/%b/%d %H:%M:%S"
            struct_time = time.strptime(datestring, format)
            header["date"] = time.asctime(struct_time)
            header["epoch"] = time.mktime(struct_time)

        except BaseException:
            pass

    # cope with vertical goniometer on I24 @ DLS from 2015/1/1
    # and possible alternative horizontal gonio if +FAST
    if (
        header.get("serial_number", "0") == "60-0119"
        and int(header["date"].split()[-1]) >= 2015
    ):
        if "+FAST" in header.get("oscillation_axis", ""):
            header["goniometer_is_vertical"] = False
        else:
            header["goniometer_is_vertical"] = True

    else:
        if "goniometer_is_vertical" not in header:
            header["goniometer_is_vertical"] = False

    return header


__lib_name = None


def set_lib_name(lib_name):
    global __lib_name
    __lib_name = lib_name


def read_image_metadata_dxtbx(image):
    """Read the image header and send back the resulting metadata in a
    dictionary. Read this using dxtbx - for a sequence of images use the
    first image in the sequence to derive the metadata, for HDF5 files
    just get on an read."""

    check_file_readable(image)

    if image.endswith(".h5"):
        # XDS can literally only handle master files called (prefix)_master.h5
        assert "master" in image
        from dxtbx.datablock import DataBlockFactory

        db = DataBlockFactory.from_filenames([image])[0]
        sweep = db.extract_sweeps()[0]

    else:
        from dxtbx.datablock import DataBlockTemplateImporter

        template, directory = image2template_directory(image)
        full_template = os.path.join(directory, template)
        importer = DataBlockTemplateImporter(
            [full_template], allow_incomplete_sweeps=True
        )
        sweep = importer.datablocks[0].extract_sweeps()[0]

    from dxtbx.serialize.xds import to_xds

    XDS_INP = to_xds(sweep).XDS_INP(as_str=True)
    params = XDS_INP_to_dict(XDS_INP)

    # detector type specific parameters - minimum spot size, trusted region
    # and so on.

    d = sweep.get_detector()
    from dxtbx.model.detector_helpers import detector_helper_sensors

    sensor_type = d[0].get_type()
    if False:
        if sensor_type == detector_helper_sensors.SENSOR_PAD:
            params["MINIMUM_NUMBER_OF_PIXELS_IN_A_SPOT"] = "2"
        else:
            params["MINIMUM_NUMBER_OF_PIXELS_IN_A_SPOT"] = "4"

    # remove things we will want to guarantee we set in fast_dp
    for name in ["BACKGROUND_RANGE", "SPOT_RANGE", "JOB"]:
        if name in params:
            del (params[name])

    return params


if __name__ == "__main__":
    import sys

    md = read_image_metadata(sys.argv[1])
    for name in sorted(md):
        print(name, md[name])
