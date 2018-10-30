# header2edna_xml - a jiffy to read a Diffraction Image from an instrument
# here at Diamond Light Source and generate EDNA xml.

from __future__ import absolute_import, division, print_function

import os
import pkg_resources
import sys

from image_readers import read_image_metadata

from image_names import image2image

# need to be sure that I have the following:
#
# binning e.g. 2x2
# image saturation i.e. 65535
# detector name i.e. ADSC Q315 bin 2x2
# image dimensions in pixels
# pixel sizes in mm
# oscillation start and width
# exposure time
# distance
# wavelength
# beam position in mm in the mosflm reference frame


# FIXME add a hash table here for the detector long names and short names...

detector_short_names = {
    ('PILATUS_2M', 1679):'p2m',
    ('PILATUS_6M', 2527):'p6m',
    ('ADSC', 3072):'q315-2x',
    ('RIGAKU', 3000):'raxis4',
}

detector_long_names = {
    ('PILATUS_2M', 1679):'PILATUS 2M',
    ('PILATUS_6M', 2527):'PILATUS 6M',
    ('ADSC', 3072):'ADSC Q315 bin 2x2',
    ('RIGAKU', 3000):'RIGAKU RAXIS IV',
}

def header2edna_xml(image_file, minosc, mintime):
    '''Read an image header, generate EDNA xml. DLS #1295.'''

    template = 'templates/EDNA_HEADER_XML.INP'
    if not pkg_resources.resource_exists('fast_dp', template):
      raise RuntimeError('template for EDNA_HEADER_XML.INP cannot be found')
    edna_xml_for_subwedge = pkg_resources.resource_string('fast_dp', template).decode('utf-8').strip()

    header = read_image_metadata(image_file)

    long_name = detector_long_names[(header['detector'], header['size'][0])]
    short_name = detector_short_names[(header['detector'], header['size'][0])]

    xml = edna_xml_for_subwedge.format(
        exposure_time = header['exposure_time'],
        minexptime = mintime,
        wavelength = header['wavelength'],
        beam_x = header['beam'][0],
        beam_y = header['beam'][1],
        bin = header.get('bin', '1x1'),
        distance = header['distance'],
        saturation = header.get('saturation', 65535),
        detector_name = long_name,
        pixel_x = header['size'][0],
        pixel_y = header['size'][1],
        pixel_size_x = header['pixel'][0],
        pixel_size_y = header['pixel'][1],
        detector_type = short_name,
        maxoscspeed = 10.0,
        minoscwidth = minosc,
        osc_width = header['phi_width'],
        oscaxis = 'phi',
        osc_end = header['phi_end'],
        osc_start = header['phi_start'],
        image_number = image2image(image_file),
        image_name = image_file)

    return xml

if __name__ == '__main__':

    if len(sys.argv) == 4:
        minosc = float(sys.argv[2])
        mintime = float(sys.argv[3])
    else:
        minosc = 0.1
        mintime = 0.067

    xml = header2edna_xml(sys.argv[1], minosc, mintime)

    print(xml)
    # .replace('><', '>\n<')
