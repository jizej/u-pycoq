"""

"""
from pprint import pprint

import shutil

import json
from collections import defaultdict

from pathlib import Path

from tutorial.utils import cat_file

import time

import concurrent

import sys

import asyncio
import os

from typing import Iterable

import pycoq.opam as opam
import pycoq.config
import pycoq.common
import pycoq.agent
from pycoq.test.test_serapi import with_prefix, _query_goals, format_query_goals

import logging

from pdb import set_trace as st
from pprint import pprint


def get_switch_name() -> str:
    """
    bot@18f71e53b3f5:~$ opam switch list
    #   switch             compiler                    description
    ->  debug_proj_4.09.1  ocaml-base-compiler.4.09.1  debug_proj_4.09.1
    """
    # todo: improve with current name, currently hardcoded wrt what is activated in my docker file.
    return 'debug_proj_4.09.1'


def get_filenames_from_coq_proj(coq_package: str,
                                coq_package_pin: str,
                                ) -> list[str]:
    switch: str = get_switch_name()

    opam.opam_pin_package_to_switch(coq_package, coq_package_pin, switch)

    executable = pycoq.opam.opam_executable('coqc', switch)
    if executable is None:
        logging.critical("coqc executable is not found in {switch}")
        return []

    regex = pycoq.pycoq_trace_config.REGEX

    workdir = None

    command = (['opam', 'reinstall']
               + opam.root_option()
               + ['--yes']
               + ['--switch', switch]
               + ['--keep-build-dir']
               + [coq_package])

    logging.info(f"{executable}, {regex}, {workdir}, {command}")

    strace_logdir = pycoq.config.get_strace_logdir()
    return pycoq.trace.strace_build(executable, regex, workdir, command, strace_logdir)


def go_through_proofs_in_file_and_print_proof_info(coq_package: str,
                                                   coq_package_pin: str,
                                                   write=False,
                                                   ):
    # - for coq_filename in coq_project.filenames():
    # filenames = get_filenames_from_coq_proj(coq_package, coq_package_pin)  # for filename in pycoq.opam.opam_strace_build(coq_package, coq_package_pin)
    filenames = pycoq.opam.opam_strace_build(coq_package, coq_package_pin)
    logging.info(f'\n ALL files: {filenames=}')
    pprint(filenames)
    # assert '/home/bot/.opam/debug_proj_4.09.1/.opam-switch/build/lf.dev/TwoGoals.v._pycoq_context' in filenames
    # filenames = ['/home/bot/.opam/debug_proj_4.09.1/.opam-switch/build/lf.dev/TwoGoals.v._pycoq_context']
    # for filename in filenames:
    #     logging.info(f"PROCESSING {filename}")
    #     ctxt = pycoq.common.load_context(filename)
    #     logging.info(f'{ctxt=}')
    #     steps = asyncio.run(pycoq.opam.opam_coq_serapi_query_goals(ctxt))
    #     pprint(steps)
    #     logging.info(f'{steps=}')
        #
        # ans = format_query_goals(steps)
        # logging.info(f'{ans=}')
        # check_ans(ans, coq_package, ctxt.target + '._pytest_signature_query_goals',
        #           write=write)

        # - for thm in get_thms(coq_filename):
            # - for i, stmt in enumerate(thm.tt.proof.stmts):


def main():
    """
    My debug example executing the commands in a script.

    opam pin -y --switch debug_proj_4.09.1 debug_proj file:///home/bot/pycoq/debug_proj
    :return:
    """
    # print(f'Starting main: {main=}')
    sys.setrecursionlimit(10000)
    # print("recursion limit", sys.getrecursionlimit())

    write: bool = False
    coq_package = 'lf'
    coq_package_pin = f"file://{with_prefix('lf')}"
    # write: bool = False
    # coq_package = 'debug_proj'
    # # coq_package_pin = f"file://{os.path.expanduser('~/pycoq/debug_proj')}"
    # coq_package_pin = f"{os.path.expanduser('~/pycoq/debug_proj')}"

    # print(f'{coq_package=}')
    # print(f'{coq_package_pin=}')
    go_through_proofs_in_file_and_print_proof_info(coq_package, coq_package_pin, write)


if __name__ == '__main__':
    print()
    print('------------------------ output of python to terminal --------------------------\n')
    start_time = time.time()
    main()
    duration = time.time() - start_time
    logging.info(f"Duration {duration} seconds.\n\a")

    # print('------------------------ output of logfile --------------------------\n')
    # cat_file(pycoq.config.get_var('log_filename'))
    # print(f'{pycoq.config.get_var("log_filename")=}')
    # logging.info(f'{pycoq.config.get_var("log_filename")=}')
    os.remove(pycoq.config.get_var('log_filename'))
