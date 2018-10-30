from __future__ import absolute_import, division, print_function

from fast_dp.run_job import run_job

from fast_dp.logger import write

def anomalous_signals(hklin):
    '''
    Compute some measures of anomalous signal: df / f and di / sig(di).
    '''

    from iotbx import mtz

    m = mtz.object(hklin)
    mas = m.as_miller_arrays()

    data = None

    for ma in mas:
        if not ma.anomalous_flag():
            continue
        if str(ma.observation_type()) != 'xray.intensity':
            continue
        data = ma

    if not data:
        raise RuntimeError('no data found')

    df_f = data.anomalous_signal()
    differences = data.anomalous_differences()
    di_sigdi = (sum(abs(differences.data())) /
                sum(differences.sigmas()))

    return df_f, di_sigdi

def merge(hklout='fast_dp.mtz', aimless_log='aimless.log'):
    '''Merge the reflections from XDS_ASCII.HKL with Aimless to get
    statistics - this will use pointless for the reflection file format
    mashing.'''

    run_job('pointless',
            ['-c', 'xdsin', 'XDS_ASCII.HKL', 'hklout', 'xds_sorted.mtz'])

    log = run_job('aimless',
                  ['hklin', 'xds_sorted.mtz', 'hklout', hklout,
                   'xmlout', 'aimless.xml'],
                  ['bins 20', 'run 1 all', 'scales constant',
                   'anomalous on', 'cycles 0', 'output unmerged',
                   'sdcorrection norefine full 1 0 0'])

    fout = open(aimless_log, 'w')

    for record in log:
        fout.write(record)

    fout.close()

    # check for errors

    for record in log:
        if '!!!! No data !!!!' in record:
            raise RuntimeError('aimless complains no data')


    return parse_aimless_log(log)

def parse_aimless_log(log):

    for record in log:
        if 'Low resolution limit  ' in record:
            lres = tuple(map(float, record.split()[-3:]))
        elif 'High resolution limit  ' in record:
            hres = tuple(map(float, record.split()[-3:]))
        elif 'Rmerge  (within I+/I-)  ' in record:
            rmerge = tuple(map(float, record.split()[-3:]))
        elif 'Rmeas (within I+/I-) ' in record:
            rmeas = tuple(map(float, record.split()[-3:]))
        elif 'Mean((I)/sd(I))  ' in record:
            isigma = tuple(map(float, record.split()[-3:]))
        elif 'Completeness  ' in record:
            comp = tuple(map(float, record.split()[-3:]))
        elif 'Multiplicity  ' in record:
            mult = tuple(map(float, record.split()[-3:]))
        elif 'Anomalous completeness  ' in record:
            acomp = tuple(map(float, record.split()[-3:]))
        elif 'Anomalous multiplicity  ' in record:
            amult = tuple(map(float, record.split()[-3:]))
        elif 'Mid-Slope of Anom Normal Probability  ' in record:
            slope = float(record.split()[-3])
        elif 'Total number of observations' in record:
            nref = tuple(map(int, record.split()[-3:]))
        elif 'Total number unique' in record:
            nuniq = tuple(map(int, record.split()[-3:]))
        elif 'DelAnom correlation between half-sets' in record:
            ccanom = tuple(map(float, record.split()[-3:]))
        elif 'Mn(I) half-set correlation CC(1/2)' in record:
            cchalf = tuple(map(float, record.split()[-3:]))

    # copy to internal storage for XML output
    xml_results = {}
    xml_results['rmerge_overall'] = rmerge[0]
    xml_results['rmeas_overall'] = rmeas[0]
    xml_results['resol_high_overall'] = hres[0]
    xml_results['resol_low_overall'] = lres[0]
    xml_results['isigma_overall'] = isigma[0]
    xml_results['completeness_overall'] = comp[0]
    xml_results['multiplicity_overall'] = mult[0]
    xml_results['acompleteness_overall'] = acomp[0]
    xml_results['amultiplicity_overall'] = amult[0]
    xml_results['cchalf_overall'] = cchalf[0]
    xml_results['ccanom_overall'] = ccanom[0]
    xml_results['nref_overall'] = nref[0]
    xml_results['nunique_overall'] = nuniq[0]

    xml_results['rmerge_inner'] = rmerge[1]
    xml_results['rmeas_inner'] = rmeas[1]
    xml_results['resol_high_inner'] = hres[1]
    xml_results['resol_low_inner'] = lres[1]
    xml_results['isigma_inner'] = isigma[1]
    xml_results['completeness_inner'] = comp[1]
    xml_results['multiplicity_inner'] = mult[1]
    xml_results['acompleteness_inner'] = acomp[1]
    xml_results['amultiplicity_inner'] = amult[1]
    xml_results['cchalf_inner'] = cchalf[1]
    xml_results['ccanom_inner'] = ccanom[1]
    xml_results['nref_inner'] = nref[1]
    xml_results['nunique_inner'] = nuniq[1]

    xml_results['rmerge_outer'] = rmerge[2]
    xml_results['rmeas_outer'] = rmeas[2]
    xml_results['resol_high_outer'] = hres[2]
    xml_results['resol_low_outer'] = lres[2]
    xml_results['isigma_outer'] = isigma[2]
    xml_results['completeness_outer'] = comp[2]
    xml_results['multiplicity_outer'] = mult[2]
    xml_results['acompleteness_outer'] = acomp[2]
    xml_results['amultiplicity_outer'] = amult[2]
    xml_results['cchalf_outer'] = cchalf[2]
    xml_results['ccanom_outer'] = ccanom[2]
    xml_results['nref_outer'] = nref[2]
    xml_results['nunique_outer'] = nuniq[2]

    # compute some additional results

    df_f, di_sigdi = anomalous_signals('fast_dp.mtz')
    # print out the results...

    write(80 * '-')

    write('%20s ' % 'Low resolution'     + '%6.2f %6.2f %6.2f' % lres)
    write('%20s ' % 'High resolution'    + '%6.2f %6.2f %6.2f' % hres)
    write('%20s ' % 'Rmerge'             + '%6.3f %6.3f %6.3f' % rmerge)
    write('%20s ' % 'I/sigma'            + '%6.2f %6.2f %6.2f' % isigma)
    write('%20s ' % 'Completeness'       + '%6.1f %6.1f %6.1f' % comp)
    write('%20s ' % 'Multiplicity'       + '%6.1f %6.1f %6.1f' % mult)
    write('%20s ' % 'CC 1/2'             + '%6.3f %6.3f %6.3f' % cchalf)
    write('%20s ' % 'Anom. Completeness' + '%6.1f %6.1f %6.1f' % acomp)
    write('%20s ' % 'Anom. Multiplicity' + '%6.1f %6.1f %6.1f' % amult)
    write('%20s ' % 'Anom. Correlation'  + '%6.3f %6.3f %6.3f' % ccanom)
    write('%20s ' % 'Nrefl'              + '%6d %6d %6d' % nref)
    write('%20s ' % 'Nunique'            + '%6d %6d %6d' % nuniq)
    write('%20s ' % 'Mid-slope'          + '%6.3f' % slope)
    write('%20s ' % 'dF/F'               + '%6.3f' % df_f)
    write('%20s ' % 'dI/sig(dI)'         + '%6.3f' % di_sigdi)

    write(80 * '-')

    return xml_results

if __name__ == '__main__':

    import sys
    parse_aimless_log(open(sys.argv[1]).readlines())
