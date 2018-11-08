from __future__ import absolute_import, division, print_function

import os
import pkg_resources

from fast_dp.run_job import get_number_cpus

def get_template(detector, instruction):
    '''Read the template for a given detector from the package resource
    files.'''
    template = 'templates/%s_%s.INP' % (detector, instruction)
    if not pkg_resources.resource_exists('fast_dp', template):
        raise RuntimeError('{template} not found'.format(template=template))

    return pkg_resources.resource_string('fast_dp', template).decode(
        'utf-8').strip()

def write_xds_inp_integrate(metadata, xds_inp, resolution_low, no_jobs=1,
                            no_processors=0):
    template_str = get_template(metadata['detector'], 'INTEGRATE')
    with open(xds_inp, 'w') as fout:

        # FIXME in here calculate the maximum number of jobs to correspond at
        # the least to 5 degree wedges / job.

        if no_processors == 0:
            no_processors = get_number_cpus()

        fout.write('%s\n' % template_str.format(
            extra_text = metadata.get('extra_text', '!PARAMETER=VALUE'),
            no_processors = no_processors,
            no_jobs = no_jobs,
            resolution_low = resolution_low,
            resolution_high = 0.0,
            nx = metadata['size'][0],
            ny = metadata['size'][1],
            qx = metadata['pixel'][0],
            qy = metadata['pixel'][1],
            orgx = metadata['beam'][0] / metadata['pixel'][0],
            orgy = metadata['beam'][1] / metadata['pixel'][1],
            distance = metadata['distance'],
            sensor = metadata.get('sensor', None),
            wavelength = metadata['wavelength'],
            oscillation = metadata['oscillation'][1],
            friedels_law = 'FALSE',
            template = os.path.join(metadata['directory'],
                                    metadata['template'].replace('#', '?')),
            starting_angle = metadata['oscillation'][0],
            starting_image = metadata['start']))

        # then we get the non-template stuff

        fout.write('DATA_RANGE=%d %d\n' % (metadata['start'],
                                           metadata['end']))

# N.B. this one is a little different to the others as the inclusion of
# the cell constants and symmetry are *mandatory*. N.B. default may be
# to use the triclinic solution in the first pass.

def write_xds_inp_correct(metadata, unit_cell, space_group_number,
                          xds_inp, scale = True,
                          resolution_low = 30, resolution_high = 0.0,
                          turn_subset = False):
    template_str = get_template(metadata['detector'], 'CORRECT')
    with open(xds_inp, 'w') as fout:
        # should somehow hang this from an anomalous flag

        if 'atom' in metadata:
            friedels_law = 'FALSE'
        else:
            friedels_law = 'TRUE'

        if scale:
            corrections = 'ALL'
        else:
            corrections = '!'

        fout.write('%s\n' % template_str.format(
            extra_text = metadata.get('extra_text', '!PARAMETER=VALUE'),
            no_processors = get_number_cpus(),
            resolution_low = resolution_low,
            resolution_high = resolution_high,
            unit_cell_a = unit_cell[0],
            unit_cell_b = unit_cell[1],
            unit_cell_c = unit_cell[2],
            unit_cell_alpha = unit_cell[3],
            unit_cell_beta = unit_cell[4],
            unit_cell_gamma = unit_cell[5],
            space_group_number = space_group_number,
            nx = metadata['size'][0],
            ny = metadata['size'][1],
            qx = metadata['pixel'][0],
            qy = metadata['pixel'][1],
            orgx = metadata['beam'][0] / metadata['pixel'][0],
            orgy = metadata['beam'][1] / metadata['pixel'][1],
            distance = metadata['distance'],
            sensor = metadata.get('sensor', None),
            wavelength = metadata['wavelength'],
            oscillation = metadata['oscillation'][1],
            friedels_law = friedels_law,
            corrections = corrections,
            template = os.path.join(metadata['directory'],
                                    metadata['template'].replace('#', '?')),
            starting_angle = metadata['oscillation'][0],
            starting_image = metadata['start']))

        # then we get the non-template stuff

        if turn_subset:
            # limit to 360 degrees...
            width = metadata['oscillation'][1]
            start, end = metadata['start'], metadata['end']
            if (end - start + 1) * width > 360:
                end = start + (360. / width) - 1
            fout.write('DATA_RANGE=%d %d\n' % (start, end))
        else:
            fout.write('DATA_RANGE=%d %d\n' % (metadata['start'],
                                               metadata['end']))

def detector_segment_text(segments):
    '''Convert a sequence of Segment descriptions to the XDS segment
    description.

    Input: list of segments
    Output: str'''

    result = []

    if len(segments) == 1:
        segment = segments[0]
        x0, y0 = segment.ofast + 1, segment.oslow + 1
        x1, y1 = x0 + segment.nfast - 1, y0 + segment.nslow - 1
        f0, f1, f2 = segment.fast.elems
        s0, s1, s2 = segment.slow.elems
        d = segment.origin.dot(segment.normal)
        ox = - segment.origin.dot(segment.fast) / segment.dfast
        oy = - segment.origin.dot(segment.slow) / segment.dslow
        result.append('''NX= %d NY= %d QX= %f QY= %f
DIRECTION_OF_DETECTOR_X-AXIS=  %f %f %f
DIRECTION_OF_DETECTOR_Y-AXIS=  %f %f %f
ORGX=  %f
ORGY=  %f
DETECTOR_DISTANCE=  %f
''' % (segment.nfast, segment.nslow, segment.dfast, segment.dslow,
       f0, f1, f2, s0, s1, s2, ox, oy, d))
        return '\n'.join(result)

    # XDS needs to know the total detector size so... the rest of this will
    # be effectively a datum position and let the segments fill in the rest

    nx = 0
    ny = 0
    for segment in segments:
        _nx, _ny = segment.ofast + segment.nfast, segment.oslow + segment.nslow
        if _nx > nx: nx = _nx
        if _ny > ny: ny = _ny

    result.append('''NX= %d NY= %d QX= %f QY= %f
DIRECTION_OF_DETECTOR_X-AXIS=  %f %f %f
DIRECTION_OF_DETECTOR_Y-AXIS=  %f %f %f
ORGX=  %f
ORGY=  %f
DETECTOR_DISTANCE=  %f
''' % (nx, ny, segments[0].dfast, segments[0].dslow,
       1, 0, 0, 0, 1, 0, 0, 0, 0))

    for segment in segments:
        x0, y0 = segment.ofast + 1, segment.oslow + 1
        x1, y1 = x0 + segment.nfast - 1, y0 + segment.nslow - 1
        f0, f1, f2 = segment.fast.elems
        s0, s1, s2 = segment.slow.elems
        d = segment.origin.dot(segment.normal)
        ox = - segment.origin.dot(segment.fast) / segment.dfast
        oy = - segment.origin.dot(segment.slow) / segment.dslow
        result.append('''SEGMENT=  %d %d %d %d
DIRECTION_OF_SEGMENT_X-AXIS=  %f %f %f
DIRECTION_OF_SEGMENT_Y-AXIS=  %f %f %f
SEGMENT_ORGX=  %f
SEGMENT_ORGY=  %f
SEGMENT_DISTANCE=  %f
''' % (x0, x1, y0, y1, f0, f1, f2, s0, s1, s2, ox, oy, d))

    return '\n'.join(result)
