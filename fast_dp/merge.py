from __future__ import absolute_import, division, print_function

from fast_dp.logger import write
from fast_dp.run_job import run_job


def anomalous_signals(hklin):
    """
    Compute some measures of anomalous signal: df / f and di / sig(di).
    """

    from iotbx import mtz

    m = mtz.object(hklin)
    mas = m.as_miller_arrays()

    data = None

    for ma in mas:
        if not ma.anomalous_flag():
            continue
        if str(ma.observation_type()) != "xray.intensity":
            continue
        data = ma

    if not data:
        raise RuntimeError("no data found")

    df_f = data.anomalous_signal()
    differences = data.anomalous_differences()
    di_sigdi = sum(abs(differences.data())) / sum(differences.sigmas())

    return df_f, di_sigdi


def merge(hklout="fast_dp.mtz", aimless_log="aimless.log"):
    """Merge the reflections from XDS_ASCII.HKL with Aimless to get
    statistics - this will use pointless for the reflection file format
    mashing."""

    run_job("pointless", ["-c", "xdsin", "XDS_ASCII.HKL", "hklout", "xds_sorted.mtz"])

    log = run_job(
        "aimless",
        ["hklin", "xds_sorted.mtz", "hklout", hklout, "xmlout", "aimless.xml"],
        [
            "bins 20",
            "run 1 all",
            "scales constant",
            "anomalous on",
            "cycles 0",
            "output unmerged",
            "sdcorrection norefine full 1 0 0",
        ],
    )

    with open(aimless_log, "w") as fout:
        for record in log:
            fout.write(record)

    # check for errors
    for record in log:
        if "!!!! No data !!!!" in record:
            raise RuntimeError("aimless complains no data")

    return parse_aimless_log(log)


def parse_aimless_log(log):
    for record in log:
        if "Low resolution limit  " in record:
            lres = tuple(map(float, record.split()[-3:]))
        elif "High resolution limit  " in record:
            hres = tuple(map(float, record.split()[-3:]))
        elif "Rmerge  (within I+/I-)  " in record:
            rmerge = tuple(map(float, record.split()[-3:]))
        elif "Rmeas (all I+ & I-) " in record:
            rmeas = tuple(map(float, record.split()[-3:]))
        elif "Mean((I)/sd(I))  " in record:
            isigma = tuple(map(float, record.split()[-3:]))
        elif "Completeness  " in record:
            comp = tuple(map(float, record.split()[-3:]))
        elif "Multiplicity  " in record:
            mult = tuple(map(float, record.split()[-3:]))
        elif "Anomalous completeness  " in record:
            acomp = tuple(map(float, record.split()[-3:]))
        elif "Anomalous multiplicity  " in record:
            amult = tuple(map(float, record.split()[-3:]))
        elif "Mid-Slope of Anom Normal Probability  " in record:
            slope = float(record.split()[-3])
        elif "Total number of observations" in record:
            nref = tuple(map(int, record.split()[-3:]))
        elif "Total number unique" in record:
            nuniq = tuple(map(int, record.split()[-3:]))
        elif "DelAnom correlation between half-sets" in record:
            ccanom = tuple(map(float, record.split()[-3:]))
        elif "Mn(I) half-set correlation CC(1/2)" in record:
            cchalf = tuple(map(float, record.split()[-3:]))

    scaling_statistics = {
        shell: {
            "anom_completeness": acomp[index],
            "anom_multiplicity": amult[index],
            "cc_anom": ccanom[index],
            "cc_half": cchalf[index],
            "completeness": comp[index],
            "mean_i_sig_i": isigma[index],
            "multiplicity": mult[index],
            "n_tot_obs": nref[index],
            "n_tot_unique_obs": nuniq[index],
            "r_meas_all_iplusi_minus": rmeas[index],
            "r_merge": rmerge[index],
            "res_lim_high": hres[index],
            "res_lim_low": lres[index],
        }
        for index, shell in enumerate(("overall", "innerShell", "outerShell"))
    }

    # compute some additional results
    df_f, di_sigdi = anomalous_signals("fast_dp.mtz")

    # print out the results...
    write(80 * "-")

    write("%20s " % "Low resolution" + "%6.2f %6.2f %6.2f" % lres)
    write("%20s " % "High resolution" + "%6.2f %6.2f %6.2f" % hres)
    write("%20s " % "Rmerge" + "%6.3f %6.3f %6.3f" % rmerge)
    write("%20s " % "I/sigma" + "%6.2f %6.2f %6.2f" % isigma)
    write("%20s " % "Completeness" + "%6.1f %6.1f %6.1f" % comp)
    write("%20s " % "Multiplicity" + "%6.1f %6.1f %6.1f" % mult)
    write("%20s " % "CC 1/2" + "%6.3f %6.3f %6.3f" % cchalf)
    write("%20s " % "Anom. Completeness" + "%6.1f %6.1f %6.1f" % acomp)
    write("%20s " % "Anom. Multiplicity" + "%6.1f %6.1f %6.1f" % amult)
    write("%20s " % "Anom. Correlation" + "%6.3f %6.3f %6.3f" % ccanom)
    write("%20s " % "Nrefl" + "%6d %6d %6d" % nref)
    write("%20s " % "Nunique" + "%6d %6d %6d" % nuniq)
    write("%20s " % "Mid-slope" + "%6.3f" % slope)
    write("%20s " % "dF/F" + "%6.3f" % df_f)
    write("%20s " % "dI/sig(dI)" + "%6.3f" % di_sigdi)

    write(80 * "-")

    return scaling_statistics


if __name__ == "__main__":
    import sys

    parse_aimless_log(open(sys.argv[1]).readlines())
