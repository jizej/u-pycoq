""" test script agent in pycoq
"""
from pathlib import Path


# todo: fix hack? does pycoq really need this?
def create_default_pycoq_log(pycoq_log_path: str = '~/.local/share/pycoq/'):
    """
    Create the default place where we save things to.
    """
    log_root: Path = Path(pycoq_log_path).expanduser()
    # args.current_time = datetime.now().strftime('%b%d_%H-%M-%S')
    # args.log_root = args.log_root / f'logs_{args.current_time}_jobid_{args.jobid}'

    log_root.mkdir(parents=True, exist_ok=True)


create_default_pycoq_log()

import time

import concurrent

import sys

import asyncio
import os

from typing import Iterable

import pycoq.opam
import pycoq.common
import pycoq.agent
from pycoq.test.test_serapi import with_prefix, _query_goals

from pdb import set_trace as st


def get_filenames(coq_package: str,
                  coq_package_pin: str,
                  coq_serapi: str,
                  coq_serapi_pin: str,
                  compiler: str
                  ) -> list[str]:
    switch = pycoq.opam_switch_name(compiler, coq_serapi, coq_serapi_pin)

    pycoq.opam_pin_package(coq_package, coq_package_pin, coq_serapi, coq_serapi_pin, compiler)

    executable = pycoq.opam_executable('coqc', switch)
    if executable is None:
        pycoq.log.critical("coqc executable is not found in {switch}")
        return []

    regex = pycoq.pycoq_trace_config.REGEX

    workdir = None

    command = (['opam', 'reinstall']
               + pycoq.root_option()
               + ['--yes']
               + ['--switch', switch]
               + ['--keep-build-dir']
               + [coq_package])

    pycoq.log.info(f"{executable}, {regex}, {workdir}, {command}")

    strace_logdir = pycoq.config.strace_logdir()
    return pycoq.trace.strace_build(executable, regex, workdir, command, strace_logdir)


def go_through_proofs_in_file_and_print_proof_info(coq_package: str, coq_package_pin=None, write=False):
    print(f'ENTERED {go_through_proofs_in_file_and_print_proof_info}...')
    with concurrent.futures.ProcessPoolExecutor() as executor:
        print(f'create executor obj: {executor=}')
        # for coq_filename in coq_project.filenames():
        for filename in pycoq.opam.opam_strace_build(coq_package, coq_package_pin):
            print(f'{filename=}')
            ctxt = pycoq.common.load_context(filename)
            print(f'{ctxt=}')
            # Schedules fn, to be executed as fn(*args, **kwargs) and returns a Future object representing the execution of the callable.
            steps = executor.submit(_query_goals, ctxt)
            print(f'{steps=}')
            # steps = asyncio.run(pycoq.opam.opam_coq_serapi_query_goals(ctxt))
            st()


def main_coq_file():
    """
    My debug example executing the commands in a script.
    :return:
    """
    print(f'Starting main: {main_coq_file}')
    # from pycoq.test.test_serapi import aux_lf_query_goals
    # aux_lf_query_goals()
    # sys.setrecursionlimit(10000)
    # print("recursion limit", sys.getrecursionlimit())
    # aux_query_goals("lf", f"file://{with_prefix('lf')}", write=write)

    sys.setrecursionlimit(10000)
    print("recursion limit", sys.getrecursionlimit())

    # write: bool = False
    # coq_package = 'lf'
    # coq_package_pin = f"file://{with_prefix('lf')}"
    write: bool = False
    coq_package = 'debug_proj'
    coq_package_pin = str(Path('~/pycoq/debug_proj/').expanduser())

    # print(f'{coq_package=}')
    # print(f'{coq_package_pin=}')
    go_through_proofs_in_file_and_print_proof_info(coq_package, coq_package_pin, write)


if __name__ == '__main__':
    start_time = time.time()
    main_coq_file()
    duration = time.time() - start_time
    print(f"Duration {duration} seconds")
