from __future__ import annotations

import os
import shutil
import subprocess


def run_job(
    executable: str,
    arguments: list[str] = [],
    stdin=[],
    working_directory: str | None = None,
) -> list[str]:
    """Run a program with some command-line arguments and some input,
    then return the standard output when it is finished.
    """
    if working_directory is None:
        working_directory = os.getcwd()

    command_line = [shutil.which(executable)] + arguments
    if command_line[0] is None:
        raise RuntimeError(f"Cannot find executable {executable!r}")

    proc = subprocess.run(
        command_line,
        bufsize=1,
        input="\n".join(stdin),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
    )

    return proc.stdout.splitlines()


if __name__ == "__main__":
    print("".join(run_job("env")))
