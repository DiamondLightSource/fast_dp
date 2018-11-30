from __future__ import absolute_import, division, print_function

import os
import shutil

from fast_dp.run_job import run_job

from fast_dp.autoindex import segment_text


def integrate(xds_inp, p1_unit_cell, resolution_low, n_jobs, n_processors):
    """Peform the integration with a triclinic basis."""

    assert xds_inp
    assert p1_unit_cell

    with open("INTEGRATE.INP", "w") as fout:
        for k in sorted(xds_inp):
            if "SEGMENT" in k:
                continue
            v = xds_inp[k]
            if isinstance(v, list):
                for _v in v:
                    fout.write("%s=%s\n" % (k, _v))
            else:
                fout.write("%s=%s\n" % (k, v))

        fout.write("REFINE(INTEGRATE)= POSITION BEAM ORIENTATION CELL\n")
        fout.write("JOB=DEFPIX INTEGRATE\n")
        fout.write("%s\n" % segment_text(xds_inp))

        if n_processors:
            fout.write("MAXIMUM_NUMBER_OF_PROCESSORS=%d\n" % n_processors)
        if n_jobs:
            fout.write("MAXIMUM_NUMBER_OF_JOBS=%d\n" % n_jobs)
        fout.write("INCLUDE_RESOLUTION_RANGE= %f 0.0\n" % resolution_low)

    shutil.copyfile("INTEGRATE.INP", "XDS.INP")

    run_job("xds_par")

    # FIXME need to check that all was hunky-dory in here!

    for step in ["DEFPIX", "INTEGRATE"]:
        if not os.path.exists("%s.LP" % step):
            continue
        lastrecord = open("%s.LP" % step).readlines()[-1]
        if "!!! ERROR !!!" in lastrecord:
            raise RuntimeError(
                "error in %s: %s"
                % (step, lastrecord.replace("!!! ERROR !!!", "").strip().lower())
            )

    if not os.path.exists("INTEGRATE.LP"):
        step = "INTEGRATE"
        for record in open("LP_01.tmp").readlines():
            if "!!! ERROR !!! AUTOMATIC DETERMINATION OF SPOT SIZE " in record:
                raise RuntimeError(
                    "error in %s: %s"
                    % (step, record.replace("!!! ERROR !!!", "").strip().lower())
                )
            elif "!!! ERROR !!! CANNOT OPEN OR READ FILE LP_01.tmp" in record:
                raise RuntimeError("integration error: cluster error")

    # check for some specific errors

    for step in ["INTEGRATE"]:
        for record in open("%s.LP" % step).readlines():
            if "!!! ERROR !!! AUTOMATIC DETERMINATION OF SPOT SIZE " in record:
                raise RuntimeError(
                    "error in %s: %s"
                    % (step, record.replace("!!! ERROR !!!", "").strip().lower())
                )
            elif "!!! ERROR !!! CANNOT OPEN OR READ FILE LP_01.tmp" in record:
                raise RuntimeError("integration error: cluster error")

    # if all was ok, look in the working directory for files named
    # forkintegrate_job.o341858 &c. and remove them. - N.B. this is site
    # specific!

    for f in os.listdir(os.getcwd()):
        if "forkintegrate_job." in f[:18]:
            try:
                os.remove(f)
            except BaseException:
                pass

    # get the mosaic spread ranges

    mosaics = []

    for record in open("INTEGRATE.LP"):
        if "CRYSTAL MOSAICITY (DEGREES)" in record:
            mosaics.append(float(record.split()[-1]))

    mosaic = sum(mosaics) / len(mosaics)

    return min(mosaics), mosaic, max(mosaics)
