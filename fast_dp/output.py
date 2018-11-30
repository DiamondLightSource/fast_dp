from __future__ import absolute_import, division, print_function

import json
import os
import pkg_resources


def write_json(
    commandline,
    spacegroup,
    unit_cell,
    scaling_statistics,
    start_image,
    refined_beam,
    filename="fast_dp.json",
):
    """Write out nice JSON for downstream processing."""

    with open(filename, "w") as fh:
        json.dump(
            {
                "commandline": commandline,
                "refined_beam": refined_beam,
                "spacegroup": spacegroup,
                "unit_cell": unit_cell,
                "scaling_statistics": scaling_statistics,
            },
            fh,
            sort_keys=True,
            indent=2,
            separators=(",", ": "),
        )


def get_ispyb_template():
    """Read the ispyb.xml template from the package resources."""
    xml_template = pkg_resources.resource_string(
        "fast_dp", "templates/ispyb.xml"
    ).decode("utf-8")
    assert xml_template, "Error retrieving XML template"
    return xml_template


def write_ispyb_xml(
    commandline,
    spacegroup,
    unit_cell,
    scaling_statistics,
    start_image,
    refined_beam,
    filename="fast_dp.xml",
):
    """Write out big lump of XML for ISPyB import."""

    xml_template = get_ispyb_template()

    with open(filename, "w") as fh:
        fh.write(
            xml_template.format(
                commandline=commandline,
                spacegroup=spacegroup,
                cell_a=unit_cell[0],
                cell_b=unit_cell[1],
                cell_c=unit_cell[2],
                cell_alpha=unit_cell[3],
                cell_beta=unit_cell[4],
                cell_gamma=unit_cell[5],
                results_directory=os.getcwd(),
                scaling_statistics=scaling_statistics,
                refined_beam_x=refined_beam[0],
                refined_beam_y=refined_beam[1],
                filename=os.path.split(start_image)[-1],
                directory=os.path.split(start_image)[0],
            )
        )
