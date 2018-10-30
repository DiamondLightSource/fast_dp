from __future__ import absolute_import, division, print_function

import pkg_resources
import json
import os

def write_json(commandline, spacegroup, unit_cell,
               xml_results, start_image, refined_beam,
               filename='fast_dp.json'):
  '''Write out nice JSON for downstream processing.'''

  with open(filename, 'w') as fh:
    json.dump({ 'commandline': commandline,
                'refined_beam': refined_beam,
                'spacegroup': spacegroup,
                'unit_cell': unit_cell,
                'xml_results': xml_results,
              }, fh, sort_keys=True,
                 indent=2, separators=(',', ': '))

def get_ispyb_template():
  '''Read the ispyb.xml template from the package resources.'''
  xml_template = pkg_resources.resource_string('fast_dp', 'templates/ispyb.xml').decode('utf-8')
  assert xml_template, 'Error retrieving XML template'
  return xml_template

def write_ispyb_xml(commandline, spacegroup, unit_cell,
                    xml_results, start_image, refined_beam,
                    filename='fast_dp.xml'):
  '''Write out big lump of XML for ISPyB import.'''

  xml_template = get_ispyb_template()

  with open(filename, 'w') as fh:
    fh.write(xml_template.format(
        commandline = commandline,
        spacegroup = spacegroup,
        cell_a = unit_cell[0],
        cell_b = unit_cell[1],
        cell_c = unit_cell[2],
        cell_alpha = unit_cell[3],
        cell_beta = unit_cell[4],
        cell_gamma = unit_cell[5],
        results_directory = os.getcwd(),
        rmerge_overall = xml_results['rmerge_overall'],
        rmeas_overall = xml_results['rmeas_overall'],
        resol_high_overall = xml_results['resol_high_overall'],
        resol_low_overall = xml_results['resol_low_overall'],
        isigma_overall = xml_results['isigma_overall'],
        completeness_overall = xml_results['completeness_overall'],
        multiplicity_overall = xml_results['multiplicity_overall'],
        acompleteness_overall = xml_results['acompleteness_overall'],
        amultiplicity_overall = xml_results['amultiplicity_overall'],
        cchalf_overall = xml_results['cchalf_overall'],
        ccanom_overall = xml_results['ccanom_overall'],
        nref_overall = xml_results['nref_overall'],
        nunique_overall = xml_results['nunique_overall'],
        rmerge_inner = xml_results['rmerge_inner'],
        rmeas_inner = xml_results['rmeas_inner'],
        resol_high_inner = xml_results['resol_high_inner'],
        resol_low_inner = xml_results['resol_low_inner'],
        isigma_inner = xml_results['isigma_inner'],
        completeness_inner = xml_results['completeness_inner'],
        multiplicity_inner = xml_results['multiplicity_inner'],
        acompleteness_inner = xml_results['acompleteness_inner'],
        amultiplicity_inner = xml_results['amultiplicity_inner'],
        cchalf_inner = xml_results['cchalf_inner'],
        ccanom_inner = xml_results['ccanom_inner'],
        nref_inner = xml_results['nref_inner'],
        nunique_inner = xml_results['nunique_inner'],
        rmerge_outer = xml_results['rmerge_outer'],
        rmeas_outer = xml_results['rmeas_outer'],
        resol_high_outer = xml_results['resol_high_outer'],
        resol_low_outer = xml_results['resol_low_outer'],
        isigma_outer = xml_results['isigma_outer'],
        completeness_outer = xml_results['completeness_outer'],
        multiplicity_outer = xml_results['multiplicity_outer'],
        acompleteness_outer = xml_results['acompleteness_outer'],
        amultiplicity_outer = xml_results['amultiplicity_outer'],
        cchalf_outer = xml_results['cchalf_outer'],
        ccanom_outer = xml_results['ccanom_outer'],
        nref_outer = xml_results['nref_outer'],
        nunique_outer = xml_results['nunique_outer'],
        refined_beam_x = refined_beam[0],
        refined_beam_y = refined_beam[1],
        filename = os.path.split(start_image)[-1],
        directory = os.path.split(start_image)[0],
    ))
