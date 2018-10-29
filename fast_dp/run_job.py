from __future__ import absolute_import, division, print_function

import os
import subprocess

def run_job(executable, arguments = [], stdin = [], working_directory = None):
    '''Run a program with some command-line arguments and some input,
    then return the standard output when it is finished.'''

    if working_directory is None:
        working_directory = os.getcwd()

    command_line = '%s' % executable
    for arg in arguments:
        command_line += ' "%s"' % arg

    popen = subprocess.Popen(command_line,
                             bufsize = 1,
                             stdin = subprocess.PIPE,
                             stdout = subprocess.PIPE,
                             stderr = subprocess.STDOUT,
                             cwd = working_directory,
                             universal_newlines = True,
                             shell = True)

    for record in stdin:
        popen.stdin.write('%s\n' % record)

    popen.stdin.close()

    output = []

    while True:
        record = popen.stdout.readline()
        if not record:
            break

        output.append(record)

    return output

def get_number_cpus():
    '''Portably get the number of processor cores available.'''

    # Windows NT derived platforms

    if os.name == 'nt':
        return int(os.environ['NUMBER_OF_PROCESSORS'])

    # linux

    if os.path.exists('/proc/cpuinfo'):
        n_cpu = 0

        for record in open('/proc/cpuinfo', 'r').readlines():
            if not record.strip():
                continue
            if 'processor' in record.split()[0]:
                n_cpu += 1

        return n_cpu

    # os X

    output = subprocess.Popen(['system_profiler', 'SPHardwareDataType'],
                              stdout = subprocess.PIPE).communicate()[0]

    ht = 1

    for record in output.split('\n'):
        if 'Intel Core i7' in record:
            ht = 2
        if 'Total Number Of Cores' in record:
            return ht * int(record.split()[-1])
        if 'Total Number of Cores' in record:
            return ht * int(record.split()[-1])

    return -1

if __name__ == '__main__':
    os.environ['FAST_DP_FORKINTEGRATE'] = '1'
    print(''.join(run_job('env')))
