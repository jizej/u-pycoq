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
from pycoq.test.test_serapi import with_prefix, _query_goals

from pdb import set_trace as st

def create_config(create_clean_version_of_log_file: bool = True):
    pycoq_config = defaultdict(None, {
        "opam_root": os.getenv('OPAM_SWITCH_PREFIX'),
        "log_level": 4,
        "log_filename": os.path.join(os.getenv('OPAM_SWITCH_PREFIX'), 'pycoq.log')
    })
    # create a clean version of the log file
    if create_clean_version_of_log_file:
        os.remove(pycoq.config.get_var('log_filename'))
        Path(pycoq.config.get_var('log_filename')).touch()
        # with open(pycoq.config.get_var('log_filename'), 'w'):
        #     pass
        pycoq.log.info('-- start --')
    print(f'--> {pycoq.config.PYCOQ_CONFIG_FILE=}')
    with open(pycoq.config.PYCOQ_CONFIG_FILE, 'w+') as f:
        json.dump(pycoq_config, f, indent=4, sort_keys=True)
    pprint(pycoq_config)


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
    # # opam.opam_list()
    # pycoq.log.info('here')
    #
    # executable = pycoq.opam.opam_executable('coqc', switch)
    # pycoq.log.info('here2')
    # if executable is None:
    #     pycoq.log.critical("coqc executable is not found in {switch}")
    #     return []
    #
    # regex = pycoq.pycoq_trace_config.REGEX
    #
    # workdir = None
    #
    # command = (['opam', 'reinstall']
    #            + opam.root_option()
    #            + ['--yes']
    #            + ['--switch', switch]
    #            + ['--keep-build-dir']
    #            + [coq_package])
    #
    # pycoq.log.info(f"{executable}, {regex}, {workdir}, {command}")
    #
    # strace_logdir = pycoq.config.strace_logdir()
    # return pycoq.trace.strace_build(executable, regex, workdir, command, strace_logdir)


def go_through_proofs_in_file_and_print_proof_info(coq_package: str,
                                                   coq_package_pin: str,
                                                   write=False,
                                                   ):
    print(f'Your coq project is: {coq_package=} {coq_package_pin=}')
    print(f'ENTERED {go_through_proofs_in_file_and_print_proof_info}...')
    with concurrent.futures.ProcessPoolExecutor() as executor:
        print(f'create executor obj: {executor=}')
        # for coq_filename in coq_project.filenames():
        # for filename in pycoq.opam.opam_strace_build(coq_package, coq_package_pin):
        filenames = get_filenames_from_coq_proj(coq_package, coq_package_pin)
        # print(f'{filenames=}')
        # for filename in get_filenames_from_coq_proj(coq_package, coq_package_pin):
        #     print(f'{filename=}')
        #     ctxt = pycoq.common.load_context(filename)
        #     print(f'{ctxt=}')
        #     # Schedules fn, to be executed as fn(*args, **kwargs) and returns a Future object representing the execution of the callable.
        #     steps = executor.submit(_query_goals, ctxt)
        #     print(f'{steps=}')
        #     # steps = asyncio.run(pycoq.opam.opam_coq_serapi_query_goals(ctxt))


def main_coq_file():
    """
    My debug example executing the commands in a script.
    :return:
    """
    create_config()
    pycoq.log.info('created my config')

    print(f'Starting main: {main_coq_file}')
    sys.setrecursionlimit(10000)
    print("recursion limit", sys.getrecursionlimit())

    # write: bool = False
    # coq_package = 'lf'
    # coq_package_pin = f"file://{with_prefix('lf')}"
    write: bool = False
    coq_package = 'debug_proj'
    coq_package_pin = str(Path('~/pycoq/debug_proj/').expanduser())

    print(f'{coq_package=}')
    print(f'{coq_package_pin=}')
    go_through_proofs_in_file_and_print_proof_info(coq_package, coq_package_pin, write)


if __name__ == '__main__':
    start_time = time.time()
    main_coq_file()
    duration = time.time() - start_time
    print(f"Duration {duration} seconds")

    cat_file(pycoq.config.get_var('log_filename'))
