from __future__ import absolute_import, division, print_function

import os
import subprocess


def run_job(executable, arguments=[], stdin=[], working_directory=None):
    """Run a program with some command-line arguments and some input,
    then return the standard output when it is finished."""

    if working_directory is None:
        working_directory = os.getcwd()

    command_line = "%s" % executable
    for arg in arguments:
        command_line += ' "%s"' % arg

    popen = subprocess.Popen(
        command_line,
        bufsize=1,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=working_directory,
        universal_newlines=True,
        shell=True,
    )

    for record in stdin:
        popen.stdin.write("%s\n" % record)

    popen.stdin.close()

    output = []

    while True:
        record = popen.stdout.readline()
        if not record:
            break

        output.append(record)

    return output


if __name__ == "__main__":
    print("".join(run_job("env")))
