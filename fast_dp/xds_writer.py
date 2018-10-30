from __future__ import absolute_import, division, print_function

import os
import pkg_resources

from fast_dp.run_job import get_number_cpus

# XDS.INP writer functions - two (three) of these, to write out commands
# for autoindexing, integration then postrefinement and scaling. Split
# up thus because XDS will frequently stop after autoindexing complaining
# that your data are not perfect, and then you probably want to run post-
# refinement and scaling a couple of times. With the latter need to be able
# to control the scale factors applied. N.B. these calculate the image
# ranges to use from the input metadata.

def get_template(detector, instruction):
  '''Read the template for a given detector from the package resource files.'''
  template = 'templates/%s_%s.INP' % (detector, instruction)
  if not pkg_resources.resource_exists('fast_dp', template):
    raise RuntimeError('{instruction} template for {detector} not found'.format(
        instruction=instruction, detector=detector))

  return pkg_resources.resource_string('fast_dp', template).decode('utf-8').strip()


def write_xds_inp_autoindex(metadata, xds_inp):
  template_str = get_template(metadata['detector'], 'INDEX')
  with open(xds_inp, 'w') as fout:

    # should somehow hang this from an anomalous flag

    friedels_law = 'FALSE'

    fout.write('%s\n' % template_str.format(
        extra_text = metadata.get('extra_text', '!PARAMETER=VALUE'),
        no_processors = get_number_cpus(),
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
        template = os.path.join(metadata['directory'],
                                metadata['template'].replace('#', '?')),
        starting_angle = metadata['oscillation'][0],
        starting_image = metadata['start']))

    # then we get the non-template stuff

    fout.write('DATA_RANGE=%d %d\n' % (metadata['start'],
                                       metadata['end']))

    # compute the background range as min(all, 5) #TODO maybe 5 degrees?

    if metadata['end'] - metadata['start'] > 5:
        fout.write('BACKGROUND_RANGE=%d %d\n' % \
                   (metadata['start'], metadata['start'] + 5))
    else:
        fout.write('BACKGROUND_RANGE=%d %d\n' % (metadata['start'],
                                                 metadata['end']))

    # REFINE(IDXREF)=
    fout.write('REFINE(IDXREF)=CELL AXIS ORIENTATION POSITION BEAM\n')

    # by default autoindex off all images - can make this better later on.
    # Ok: I think it is too slow already. Three wedges, as per xia2...
    # that would be 5 images per wedge, then. Erk. Should be *degrees*

    images = range(metadata['start'], metadata['end'] + 1)

    wedge_size = int(round(5.0  / metadata['oscillation'][1])) - 1

    wedge = (images[0], images[0] + wedge_size)
    fout.write('SPOT_RANGE=%d %d\n' % wedge)

    # if we have more than 90 degrees of data, use wedges at the start,
    # 45 degrees in and 90 degrees in, else use a wedge at the start,
    # one in the middle and one at the end.

    # if less than 15 degrees of data, use all of the images

    if (metadata['end'] - metadata['start']) * metadata['oscillation'][1] < 15:
        fout.write('SPOT_RANGE=%d %d\n' % (metadata['start'],
                                           metadata['end']))

    elif int(90.0 / metadata['oscillation'][1]) + wedge_size in images:
        wedge = (int(45.0 / metadata['oscillation'][1]),
                 int(45.0 / metadata['oscillation'][1]) + wedge_size)
        fout.write('SPOT_RANGE=%d %d\n' % wedge)
        wedge = (int(90.0 / metadata['oscillation'][1]),
                 int(90.0 / metadata['oscillation'][1]) + wedge_size)
        fout.write('SPOT_RANGE=%d %d\n' % wedge)

    else:
        mid = (len(images) / 2) - wedge_size + images[0] - 1
        wedge = (mid, mid + wedge_size)
        fout.write('SPOT_RANGE=%d %d\n' % wedge)
        wedge = (images[-wedge_size], images[-1])
        fout.write('SPOT_RANGE=%d %d\n' % wedge)


def write_xds_inp_autoindex_p1_cell(metadata, xds_inp, cell):
  template_str = get_template(metadata['detector'], 'INDEX')
  with open(xds_inp, 'w') as fout:
    # should somehow hang this from an anomalous flag

    friedels_law = 'FALSE'

    fout.write('%s\n' % template_str.format(
        extra_text = metadata.get('extra_text', '!PARAMETER=VALUE'),
        no_processors = get_number_cpus(),
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
        template = os.path.join(metadata['directory'],
                                metadata['template'].replace('#', '?')),
        starting_angle = metadata['oscillation'][0],
        starting_image = metadata['start']))

    # cell, spacegroup

    fout.write('SPACE_GROUP_NUMBER=1\n')
    fout.write('UNIT_CELL_CONSTANTS=%f %f %f %f %f %f\n' % tuple(cell))

    # then we get the non-template stuff

    fout.write('DATA_RANGE=%d %d\n' % (metadata['start'],
                                       metadata['end']))

    # compute the background range as min(all, 5)

    if metadata['end'] - metadata['start'] > 5:
        fout.write('BACKGROUND_RANGE=%d %d\n' % \
                   (metadata['start'], metadata['start'] + 5))
    else:
        fout.write('BACKGROUND_RANGE=%d %d\n' % (metadata['start'],
                                                 metadata['end']))

    # by default autoindex off all images - can make this better later on.
    # Ok: I think it is too slow already. Three wedges, as per xia2...
    # that would be 5 images per wedge, then. Erk. Should be *degrees*

    images = range(metadata['start'], metadata['end'] + 1)

    wedge_size = int(round(5.0  / metadata['oscillation'][1])) - 1

    wedge = (images[0], images[0] + wedge_size)
    fout.write('SPOT_RANGE=%d %d\n' % wedge)

    # if we have more than 90 degrees of data, use wedges at the start,
    # 45 degrees in and 90 degrees in, else use a wedge at the start,
    # one in the middle and one at the end.

    # if less than 15 degrees of data, use all of the images

    if (metadata['end'] - metadata['start']) * metadata['oscillation'][1] < 15:
        fout.write('SPOT_RANGE=%d %d\n' % (metadata['start'],
                                           metadata['end']))

    elif int(90.0 / metadata['oscillation'][1]) + wedge_size in images:
        wedge = (int(45.0 / metadata['oscillation'][1]),
                 int(45.0 / metadata['oscillation'][1]) + wedge_size)
        fout.write('SPOT_RANGE=%d %d\n' % wedge)
        wedge = (int(90.0 / metadata['oscillation'][1]),
                 int(90.0 / metadata['oscillation'][1]) + wedge_size)
        fout.write('SPOT_RANGE=%d %d\n' % wedge)

    else:
        mid = (len(images) / 2) - wedge_size + images[0] - 1
        wedge = (mid, mid + wedge_size)
        fout.write('SPOT_RANGE=%d %d\n' % wedge)
        wedge = (images[-5], images[-1])
        fout.write('SPOT_RANGE=%d %d\n' % wedge)


def write_xds_inp_integrate(metadata, xds_inp, resolution_low, no_jobs=1, no_processors=0):
  template_str = get_template(metadata['detector'], 'INTEGRATE')
  with open(xds_inp, 'w') as fout:

    # FIXME in here calculate the maximum number of jobs to correspond at the
    # least to 5 degree wedges / job.

    # should somehow hang this from an anomalous flag

    friedels_law = 'FALSE'

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
        friedels_law = friedels_law,
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
        fout.write('DATA_RANGE=%d %d\n' % (metadata['start'], metadata['end']))


def write_xds_inp_correct_no_cell(metadata,
                                  xds_inp, scale = True,
                                  resolution_low = 30, resolution_high = 0.0):
  template_str = get_template(metadata['detector'], 'CORRECT_NO_CELL')
  with open(xds_inp, 'w') as fout:
    # should somehow hang this from an anomalous flag

    friedels_law = 'FALSE'

    if scale:
        corrections = 'ALL'
    else:
        corrections = '!'

    fout.write('%s\n' % template_str.format(
        extra_text = metadata.get('extra_text', '!PARAMETER=VALUE'),
        no_processors = get_number_cpus(),
        resolution_low = resolution_low,
        resolution_high = resolution_high,
        nx = metadata['size'][0],
        ny = metadata['size'][1],
        qx = metadata['pixel'][0],
        qy = metadata['pixel'][1],
        orgx = metadata['beam'][0] / metadata['pixel'][0],
        orgy = metadata['beam'][1] / metadata['pixel'][1],
        distance = metadata['distance'],
        sensor = metadata['sensor'],
        wavelength = metadata['wavelength'],
        oscillation = metadata['oscillation'][1],
        friedels_law = friedels_law,
        corrections = corrections,
        template = os.path.join(metadata['directory'],
                                metadata['template'].replace('#', '?')),
        starting_angle = metadata['oscillation'][0],
        starting_image = metadata['start']))

    # then we get the non-template stuff

    fout.write('DATA_RANGE=%d %d\n' % (metadata['start'],
                                       metadata['end']))
