'''
functions to work with opam

Opam terms:
opam pin/pinning = ... why do we need this? difference with opam install?
'''
import sys
from pprint import pprint
from typing import Optional, List, Tuple

import subprocess
import os
import asyncio

import pycoq.config
import pycoq.pycoq_trace_config
import pycoq.trace
import pycoq.log
import pycoq.split
import pycoq.serapi
import pycoq.query_goals

# import serlib.parser

import logging

from pdb import set_trace as st

# refactor globals below to be loaded from a default config
# see e.g. https://tech.preferred.jp/en/blog/working-with-configuration-in-python/
from pycoq.common import LocalKernelConfig
from pycoq.project_splits import CoqProj

MIN_OPAM_VERSION = "2."
DEFAULT_OCAML = "ocaml-variants.4.07.1+flambda"
COQ_REPO = "coq-released"
COQ_REPO_SOURCE = "https://coq.inria.fr/opam/released"
SWITCH_INSTALLED_ERROR = "[ERROR] There already is an installed switch named"
COQ_SERAPI = "coq-serapi"
# COQ_SERAPI_PIN = "8.13.0+0.13.0"
COQ_SERAPI_PIN = "8.11.0+0.11.1"
COQ_EXTRA_WARNING = ['-w', '-projection-no-head-constant',
                     '-w', '-redundant-canonical-projection',
                     '-w', '-notation-overridden',
                     '-w', '-duplicate-clear',
                     '-w', '-ambiguous-paths',
                     '-w', '-undeclared-scope',
                     '-w', '-non-reversible-notation']


def opam_version() -> Optional[str]:
    ''' returns opam version available on the system '''
    try:
        command = ['opam', '--version']
        result = subprocess.run(command, check=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        return result.stdout.decode().strip()
    except FileNotFoundError:
        logging.critical("opam not found")
        return None
    except subprocess.CalledProcessError as error:
        logging.critical(f"{command} returned {error.returncode} {error.stdout.decode()} {error.stderr.decode()}")
        return None


def opam_check() -> bool:
    ''' checks if opam version is at least MIN_OPAM_VERSION '''
    version = opam_version()
    logging.info(f"checked opam_version={version}")
    return version and version.startswith(MIN_OPAM_VERSION)
    # it would be nicer to use
    # pkg_resources.parse_version(version) >= pkg_resources.parse_version(MIN_OPAM_VERSION)
    # but ^^^ breaks for ~rc versions of opam


def root_option() -> List[str]:
    ''' constructs root option arg to call opam '''
    root = pycoq.config.get_opam_root()
    return ['--root', root] if not root is None else []


def opam_init_root() -> bool:
    ''' returns True if opam inititalizes root successfully '''
    if not opam_check():
        return False

    command = (['opam', 'init']
               + ['--disable-sandboxing']
               + root_option()
               + ['--bare', '-n'])

    try:
        result = subprocess.run(command, check=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        logging.info(f"{command}: {result.stdout.decode()} {result.stderr.decode()}")
        return True
    except subprocess.CalledProcessError as error:
        logging.critical(f"{command} {error.returncode}: {error.stdout.decode()} {error.stderr.decode()}")
        return False


def opam_update() -> bool:
    '''
    returns True if opam update is successfull
    '''
    command = (['opam', 'update'] + root_option()
               + ['--all'])

    try:
        result = subprocess.run(command, check=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        logging.info(f"{command}: {result.stdout.decode()} {result.stderr.decode()}")
        return True

    except subprocess.CalledProcessError as error:
        logging.critical(f"{command} returned {error.returncode}: {error.stdout.decode()} {error.stderr.decode()}")
        return False


def opam_add_repo_coq() -> bool:
    ''' returns True if opam successfully adds coq repo '''
    if not opam_init_root():
        return False

    command = (['opam', 'repo'] + root_option()
               + ['--all-switches', 'add']
               + ['--set-default']
               + [COQ_REPO, COQ_REPO_SOURCE])

    try:
        result = subprocess.run(command, check=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        logging.info(f"{command}: {result.stdout.decode()} {result.stderr.decode()}")
        return opam_update()
    except subprocess.CalledProcessError as error:
        logging.critical(f"{command} returned {error.returncode}: {error.stdout.decode()} {error.stderr.decode()}")
        logging.critical(
            f"{' '.join(command)} returned {error.returncode}: {error.stdout.decode()} {error.stderr.decode()}")
        return False


def opam_set_base(switch: str, compiler) -> bool:
    ''' set base package in the switch;
    the usage of this function is not clear
    '''
    command = (['opam', 'switch'] + root_option()
               + ['--switch', switch]
               + ['-y']
               + ['set-base', compiler])
    try:
        result = subprocess.run(command, check=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        logging.info(f"{command}: {result.stdout.decode()} {result.stderr.decode()}")
        return True
    except subprocess.CalledProcessError as error:
        logging.critical(f"{command} returned {error.returncode}: {error.stdout.decode()} {error.stderr.decode()}")
        return False


def opam_install_package(switch: str, package: str) -> bool:
    ''' installs package into a selected switch or updates '''
    # todo: can be improved by having packages be a list with *package
    command = (['opam', 'install', '-y'] + root_option()
               + ['--switch', switch, package])
    logging.info(f"installing {package} in opam switch {switch} ...")
    try:
        result = subprocess.run(command, check=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        logging.info(f"{command}: {result.stdout.decode()} {result.stderr.decode()}")
        return True

    except subprocess.CalledProcessError as error:
        logging.critical(f"{command} returned {error.returncode}: {error.stdout.decode()} {error.stderr.decode()}")
        return False


def opam_create_switch(switch: str, compiler: str) -> bool:
    ''' returns True if opam can create or recreate
    switch successfully '''

    if not opam_add_repo_coq():
        return False
    logging.info(f"soft (re)creating switch {switch} with compiler {compiler} in {root_option()}")
    command = (['opam', 'switch'] + root_option()
               + ['--color', 'never']
               + ['create', switch, compiler])

    try:
        result = subprocess.run(command, check=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        logging.info(f"{command}: {result.stdout.decode()} {result.stderr.decode()}")
        return True
    except subprocess.CalledProcessError as error:
        if (error.returncode == 2 and
                error.stderr.decode().strip().startswith(SWITCH_INSTALLED_ERROR)):
            logging.warning(f"opam: the switch {switch} already exists")

            return opam_install_package(switch, compiler)
        logging.critical(f"{command} returned {error.returncode}: {error.stdout.decode()} {error.stderr.decode()}")
        return False


def opam_pin_package(coq_package: str,
                     coq_package_pin: str,
                     coq_serapi=COQ_SERAPI,
                     coq_serapi_pin=COQ_SERAPI_PIN,
                     compiler=DEFAULT_OCAML) -> bool:
    '''
    pins package to source in the switch
    '''
    logging.info('\n ----')
    logging.info(f'{opam_pin_package=}')
    switch = opam_switch_name(compiler, coq_serapi, coq_serapi_pin)
    logging.info(f"pinning package {coq_package=} to pin {coq_package_pin=} in switch {switch=}")
    command = (['opam', 'pin', '-y']
               + root_option()
               + ['--switch', switch]
               + [coq_package, coq_package_pin])

    try:
        logging.info(f"-> command={' '.join(command)}")

        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        logging.info(f'{result.stdout.decode()=}')
        logging.info(f'{result.stderr.decode()=}')
        return True
    except subprocess.CalledProcessError as error:
        logging.critical(f"{command} returned {error.returncode}: {error.stdout.decode()} | {error.stderr.decode()}")
        return False
    # I think bellow is a replacement for opam reinstall so it shouldn't go in opam pin...(but we are using our own anyway)
    # except Exception as e:
    #     logging.info(f"Attempt from VP didn't work so we are going to try make, VPs error was: {e=}")
    #     logging.info('-> Going to try make instead')
    #
    #     command: list = ['make', '-C', coq_package_pin]
    #     logging.info(f"-> command={' '.join(command)}")
    #
    #     result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #
    #     logging.info(f"-> command=[{' '.join(command)}]")
    #     logging.info(f'{result.stdout.decode()=}')
    #     logging.info(f'{result.stderr.decode()=}')
    #     return True


def opam_pin_proj():
    pass


def opam_pin_package_to_switch(coq_package: str,
                               coq_package_pin: str,
                               switch: str) -> bool:
    print(f"{opam_pin_package_to_switch}")
    return opam_pin_package(coq_package, coq_package_pin, compiler=switch, coq_serapi='', coq_serapi_pin='')


def opam_switch_name(compiler: str, coq_serapi: str,
                     coq_serapi_pin: str) -> str:
    ''' constructs switch name from compiler, coq_serapi and coq_serapi_pin '''
    if coq_serapi == '' and coq_serapi_pin == '':
        return compiler  # compiler should be the switch name
    return compiler + '_' + coq_serapi + '.' + coq_serapi_pin


def opam_install_serapi(coq_serapi=COQ_SERAPI,
                        coq_serapi_pin=COQ_SERAPI_PIN,
                        compiler=DEFAULT_OCAML) -> bool:
    ''' creates default switch and installs coq-serapi there
    '''

    switch = opam_switch_name(compiler, coq_serapi, coq_serapi_pin)
    if not opam_create_switch(switch, compiler):
        return False
    if not opam_pin_package(coq_serapi, coq_serapi_pin,
                            coq_serapi, coq_serapi_pin,
                            compiler):
        return False
    return opam_install_package(switch, coq_serapi)


def opam_install_coq_package(coq_package: str,
                             coq_package_pin=None,
                             coq_serapi=COQ_SERAPI,
                             coq_serapi_pin=COQ_SERAPI_PIN,
                             compiler=DEFAULT_OCAML) -> bool:
    ''' installs coq-package into default switch
    name constructed from (compiler version)_(serapi version)
    '''
    switch = opam_switch_name(compiler, coq_serapi, coq_serapi_pin)

    if not opam_install_serapi(coq_serapi,
                               coq_serapi_pin,
                               compiler):
        return False

    if ((not coq_package_pin is None) and
            not opam_pin_package(coq_package, coq_package_pin, coq_serapi, coq_serapi_pin, compiler)):
        return False

    return opam_install_package(switch, coq_package)


def opam_default_root() -> Optional[str]:
    '''
    returns default root of opam
    '''
    if not opam_check():
        return False

    command = (['opam', 'config', 'var', 'root'])
    try:
        result = subprocess.run(command, check=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        logging.info(result.stdout.decode(), result.stderr.decode())
        root = result.stdout.decode().strip()
        if os.path.isdir(root):
            return root
        else:
            logging.critical('missing opam default root directory {root}')
            return None
    except subprocess.CalledProcessError as error:
        logging.critical(f"{command} returned {error.returncode}: {error.stdout.decode()} {error.stderr.decode()}")
        return None


def opam_executable(name: str, switch: str) -> Optional[str]:
    ''' returns coqc name in a given opam root and switch '''
    if not opam_check():
        return None
    command = (['opam', 'exec']
               + root_option()
               + ['--switch', switch]
               + ['--', 'which', name])
    try:
        result = subprocess.run(command, check=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        logging.info(f"{command}: {result.stdout.decode()} {result.stderr.decode()}")
        ans = result.stdout.decode().strip()
        if not os.path.isfile(ans):
            err_mgs: str = f"{name} obtained executing {command} and resolved to {ans} was not found "
            logging.error(err_mgs)
            raise Exception(err_mgs)
        return ans

    except subprocess.CalledProcessError as error:
        logging.critical(f"{command} returned {error.returncode}: {error.stdout.decode()} {error.stderr.decode()}")
        return None


def opam_strace_build(coq_package: str,
                      coq_package_pin=None,
                      coq_serapi=COQ_SERAPI,
                      coq_serapi_pin=COQ_SERAPI_PIN,
                      compiler=DEFAULT_OCAML) -> List[str]:
    ''' returns a list of pycoq context files
    after opam build of a package; monitoring calls
    with strace

    legacy.
    '''

    switch = opam_switch_name(compiler, coq_serapi, coq_serapi_pin)

    if not opam_create_switch(switch, compiler):
        return False

    if not opam_pin_package(coq_serapi, coq_serapi_pin, coq_serapi, coq_serapi_pin, compiler):
        return False

    if not opam_install_package(switch, coq_serapi):
        return False

    if ((not coq_package_pin is None) and
            not opam_pin_package(coq_package, coq_package_pin, coq_serapi, coq_serapi_pin, compiler)):
        return False

    executable = opam_executable('coqc', switch)
    if executable is None:
        pycoq.log.critical("coqc executable is not found in {switch}")
        return []

    regex = pycoq.pycoq_trace_config.REGEX

    workdir = None

    command = (['opam', 'reinstall']
               + root_option()
               + ['--yes']
               + ['--switch', switch]
               + ['--keep-build-dir']
               + [coq_package])

    pycoq.log.info(f"{executable}, {regex}, {workdir}, {command}")

    strace_logdir = pycoq.config.strace_logdir()
    return pycoq.trace.strace_build(executable, regex, workdir, command, strace_logdir)


def opam_strace_command(command: List[str],
                        workdir: str,
                        coq_serapi=COQ_SERAPI,
                        coq_serapi_pin=COQ_SERAPI_PIN,
                        compiler=DEFAULT_OCAML) -> List[str]:
    ''' strace command
    '''

    switch = opam_switch_name(compiler, coq_serapi, coq_serapi_pin)
    root = pycoq.config.get_opam_root()
    if root is None:
        root = opam_default_root()

    if root is None:
        logging.critical("in opam_strace_build failed to determine opam root")
        return []

    executable = opam_executable('coqc', switch)
    if executable is None:
        logging.critical("coqc executable is not found")
        return []

    regex = pycoq.pycoq_trace_config.REGEX

    logging.info(f"{executable}, {regex}, {workdir}, {command}")

    return pycoq.trace.strace_build(executable, regex, workdir, command)


def opam_coqtop(coq_ctxt: pycoq.common.CoqContext,
                coq_serapi=COQ_SERAPI,
                coq_serapi_pin=COQ_SERAPI_PIN,
                compiler=DEFAULT_OCAML) -> int:
    '''
    runs coqtop with a given pycoq_context
    returns error code of coqtop with Coqtop Exit on Error flag
    '''
    iqr_args = pycoq.common.coqc_args(coq_ctxt.IQR())
    switch = opam_switch_name(compiler, coq_serapi, coq_serapi_pin)

    command = (['opam', 'exec']
               + root_option()
               + ['--switch', switch]
               + ['--', 'coqtop']
               + ['-q']
               + iqr_args
               + ['-set', 'Coqtop Exit On Error']
               + ['-topfile', coq_ctxt.target]
               + ['-batch', '-l', coq_ctxt.target])
    logging.info(f"{' '.join(command)} on {coq_ctxt.target}")
    try:
        result = subprocess.run(command,
                                cwd=coq_ctxt.pwd,
                                check=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        logging.info(f"{command}: {result.stdout.decode()} {result.stderr.decode()}")
        return 0
    except subprocess.CalledProcessError as error:
        logging.error(f"{command} returned {error.returncode}: {error.stdout.decode()} {error.stderr.decode()}")
        return error.returncode


async def opam_coqtop_stmts(coq_ctxt: pycoq.common.CoqContext,
                            coq_serapi=COQ_SERAPI,
                            coq_serapi_pin=COQ_SERAPI_PIN,
                            compiler=DEFAULT_OCAML) -> List[str]:
    '''
    feeds coqtop repls with a stream
    of coq staments derived from coq_context_fname

    returns a list of pairs: <input, output>
    '''
    print("entered opam_coqtop_stmts")

    iqr_args = pycoq.common.coqc_args(coq_ctxt.IQR())
    switch = opam_switch_name(compiler, coq_serapi, coq_serapi_pin)
    command = (['opam', 'exec']
               + root_option()
               + ['--switch', switch]
               + ['--', 'coqtop']
               + ['-q']
               + iqr_args
               + ['-set', 'Coqtop Exit On Error']
               + ['-topfile', coq_ctxt.target])

    logging.info(f"interactive {' '.join(command)}")

    ans = []
    proc = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        stdin=asyncio.subprocess.PIPE,
        cwd=coq_ctxt.pwd)
    print(f"proc {proc} is created")

    for stmt in pycoq.split.coq_stmts_of_context(coq_ctxt):
        print(f"writing {stmt}")
        proc.stdin.write(stmt.encode())
        print("waiting for drain")
        await proc.stdin.drain()
    proc.stdin.write_eof()

    while True:
        line = (await proc.stdout.readline()).decode()
        if line == '':
            break
        ans.append(line)
        print(f"response {line}")

    err = (await proc.stderr.read()).decode()
    print(f"error {err}")

    return ans, err, proc.returncode


def opam_serapi_cfg(coq_ctxt: pycoq.common.CoqContext = None,
                    coq_serapi=COQ_SERAPI,
                    coq_serapi_pin=COQ_SERAPI_PIN,
                    compiler=DEFAULT_OCAML,
                    debug=False) -> LocalKernelConfig:
    ''' returns serapi cfg from coq_ctxt '''
    if coq_ctxt == None:
        coq_ctxt = pycoq.common.CoqContext(pwd=os.getcwd(),
                                           executable='',
                                           target='default_shell')

    iqr_args = pycoq.common.serapi_args(coq_ctxt.IQR())
    switch = opam_switch_name(compiler, coq_serapi, coq_serapi_pin)
    debug_option = ['--debug'] if debug else []

    command = (['opam', 'exec']
               + root_option()
               + ['--switch', switch]
               + ['--', 'sertop']
               + iqr_args
               + ['--topfile', coq_ctxt.target]
               + debug_option)

    return pycoq.common.LocalKernelConfig(command=command,
                                          env=None,
                                          pwd=coq_ctxt.pwd)


def log_query_goals_error(_serapi_goals, serapi_goals, serapi_goals_legacy):
    dumpname = 'pycoq_opam_serapi_query_goals.dump'
    logging.info(f"ERROR discrepancy in serapi_goals\n"
                 f"source: {_serapi_goals}\n"
                 f"serapi_goals: {serapi_goals}\n"
                 f"serapi_goals_legacy: {serapi_goals_legacy}\n"
                 f"input source dumped into {dumpname}\n")
    open(dumpname, 'w').write(_serapi_goals)
    raise ValueError("ERROR serapi_goals discrepancy")


def _strace_build_with_opam_and_get_filenames_legacy(coq_proj: str,
                                                     coq_proj_path: str,
                                                     coq_serapi=COQ_SERAPI,
                                                     coq_serapi_pin=COQ_SERAPI_PIN,
                                                     compiler=DEFAULT_OCAML,
                                                     ) -> list[str]:
    """
    coq_package='lf'
    coq_package_pin='/dfs/scratch0/brando9/pycoq/pycoq/test/lf'
    coq_proj_path='/dfs/scratch0/brando9/pycoq/pycoq/test/lf'
    """
    switch = opam_switch_name(compiler, coq_serapi, coq_serapi_pin)
    # - tries to opam install coq_package
    if ((not coq_proj_path is None) and
            not opam_pin_package(coq_proj, coq_proj_path, coq_serapi, coq_serapi_pin, compiler)):
        raise Exception(f'Failed to pin pkg: {(coq_proj, coq_proj_path, coq_serapi, coq_serapi_pin, compiler)=}')
        # return False

    # logic bellow inside: strace_build_with_opam_reinstall(...)
    executable = opam_executable('coqc', switch)
    if executable is None:
        logging.critical(f"coqc executable is not found in {switch}")
        return []

    regex = pycoq.pycoq_trace_config.REGEX

    workdir = None

    command = (['opam', 'reinstall']
               + root_option()
               + ['--yes']
               + ['--switch', switch]
               + ['--keep-build-dir']
               + [coq_proj])

    logging.info(f"{executable}, {regex}, {workdir}, {command}")
    logging.info(f"{executable}, {regex}, {workdir}, {' '.join(command)}")

    strace_logdir = pycoq.config.get_strace_logdir()
    return pycoq.trace.strace_build(executable, regex, workdir, command, strace_logdir)


def opam_list():
    """shows packages in current switch: https://opam.ocaml.org/doc/man/opam-list.html """
    command = (['opam', 'list'])
    logging.info(f"Running {command=}.")
    try:
        result = subprocess.run(command,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        # print(f'{result.stdout.decode()}')
        logging.info(f"{command}: {result.stdout.decode()} {result.stderr.decode()}")
        return 0
    except subprocess.CalledProcessError as error:
        logging.error(f"{command} returned {error.returncode}: {error.stdout.decode()} {error.stderr.decode()}")
        return error.returncode


def opam_original_pycoq_pre_setup(coq_package: str,
                                  coq_package_pin: object = None,
                                  coq_serapi: object = COQ_SERAPI,
                                  coq_serapi_pin: object = COQ_SERAPI_PIN,
                                  compiler: object = DEFAULT_OCAML,
                                  switch: Optional = None,
                                  ):
    """
    Tries to set up PyCoq's original (hardcoded most likely) setup up. i.e.
        - creates switch
        - installs coq serapi
        - pins coq-serapi
        - install coq package to get coq files from
        - pin coq package to get coq files from
    """
    # PyCoq's original code created this switch with this name
    if switch is None:
        switch = opam_switch_name(compiler, coq_serapi, coq_serapi_pin)

    # - tries to create opam switch
    logging.info(f'-> about to install switch: {switch=}, {compiler=}')
    if not opam_create_switch(switch, compiler):
        raise Exception(f'Failed to create switch with args: {switch=}, {compiler=}')

    # - tries to pin install coq_serapi
    logging.info(f'-> about to pin coq pkg coq-serapi: coq_pkg={coq_serapi}')
    if not opam_pin_package(coq_serapi, coq_serapi_pin, coq_serapi, coq_serapi_pin, compiler):
        raise Exception(f'Failed to pin serapi: {(coq_serapi, coq_serapi_pin, coq_serapi, coq_serapi_pin, compiler)=}')
        # return False

    # - tries to install coq_serapi
    logging.info(f'-> about to install coq-serapi: package={coq_serapi}')
    if not opam_install_package(switch, coq_serapi):
        raise Exception(f'Failed to install serapi: {(switch, coq_serapi)=}')

    # - tries to opam install coq_package
    logging.info(f'--> about to install coq-package: {coq_package_pin=}')
    logging.info(f'{not coq_package_pin is None=}')
    logging.info(f'--> about to pin: {(coq_package, coq_package_pin, coq_serapi, coq_serapi_pin, compiler)=}')
    if ((not coq_package_pin is None) and
            not opam_pin_package(coq_package, coq_package_pin, coq_serapi, coq_serapi_pin, compiler)):
        logging.critical(
            'raises error if the coq pkg pin is not None (i.e. it is some pkg) and we failed to pin the pkg')
        err_msg: str = f'Failed to pin pkg: {(coq_package, coq_package_pin, coq_serapi, coq_serapi_pin, compiler)=}'
        logging.critical(err_msg)
        raise Exception(err_msg)


# - new opam commands that work with proverbots coq-projects

def strace_build_coq_project_and_get_filenames(coq_proj: CoqProj,
                                               regex_to_get_filenames: Optional[str] = None,
                                               ) -> list[str]:
    """
    Builds the give coq-project & returns a list of pycoq context filenames after opam build of a package;
    monitoring calls with (linux's) strace (to get the pycoq context filenames).

    Note:
        - we decided to force the CoqProj api instead of allowing ppl to pass the switch, coq_project_name,
        coq_project_name, build_command, etc. directly since it will force you to install/make the make files for each
        project & depnds properly. Perhaps, later work to remove this & install deps for users here. But we need to
        put that into in to coq_proj .json file anyway, so the coq_proj api would be needed still.

    coq_package='lf'
    coq_package_pin='/dfs/scratch0/brando9/pycoq/pycoq/test/lf'

        (iit_synthesis) brando9/afs/cs.stanford.edu/u/brando9/proverbot9001/coq-projects/CompCert $ source make.sh
        (iit_synthesis) brando9/afs/cs.stanford.edu/u/brando9/proverbot9001/coq-projects/CompCert $ source make.sh
    """
    logging.info(f'{strace_build_coq_project_and_get_filenames=}')
    logging.info(f'{root_option()=}')

    # - use switch corresponding to the coq proj
    logging.info(f'{coq_proj=}')
    switch: str = coq_proj.switch  # e.g. coq-8.10
    coq_project_name: str = coq_proj.project_name  # e.g. constructive-geometry
    coq_project_path: str = coq_proj.get_coq_proj_path()  # e.g. ~/proverbot9001/coq-projects/
    build_command: str = coq_proj.build_command  # e.g. configure x86_64-linux && make
    logging.info(f'{switch=}')
    logging.info(f'{coq_project_name=}')
    logging.info(f'{coq_project_path=}')
    logging.info(f'{build_command=}')

    # - activate opam switch for coq project
    get_active_opam_switch_according_to_bash_opam_switch_cmd(py_prints_on=False)
    opam_set_switch_via_opam_switch(switch)
    active_switch: str = get_active_opam_switch_according_to_bash_opam_switch_cmd(py_prints_on=False)
    logging.info(f'{active_switch=}')
    assert active_switch == switch, f'active_switch={active_switch} != switch={switch}, failed to set opam switch.'

    # -- get list of coq files from coq project
    # - since we are in the code that build the coq proj & gets list of filename pycoq contexts, we need to opam pin https://stackoverflow.com/questions/74777579/is-opam-pin-project-needed-when-one-wants-to-install-a-opam-project-with-opam-re
    # pin_coq_project(switch, coq_project_name, coq_proect_path)  # todo double check

    # - keep building & strace-ing until coq proj/pkg succeeds -- we'll know since the filenames list is not empty.
    regex: str = pycoq.pycoq_trace_config.REGEX if regex_to_get_filenames is None else regex_to_get_filenames
    logging.info(f'{regex=}')
    filenames: list[str] = []  # coq-proj/pkg filenames.
    logging.info(f'{filenames=}')
    if len(filenames) == 0:
        # else build with the coq-projs make file
        filenames: list[str] = strace_build_with_make_clean(switch, coq_project_name, coq_project_path, regex)
    logging.info(f'{filenames=}')
    if len(filenames) == 0:
        # try to build it with PyCoq's original opam reinstall
        filenames: list[str] = strace_build_opam_reinstall_opam_pin(switch, coq_project_name, coq_project_path, regex)
    logging.info(f'--> before return: {filenames=}')
    return filenames


def strace_build_opam_reinstall_opam_pin(switch: str,
                                         coq_project_name: str,
                                         coq_project_path: str,
                                         regex: str,
                                         workdir: Optional = None,
                                         ):
    """
    opam reinstall --yes --switch ocaml-variants.4.07.1+flambda_coq-serapi.8.11.0+0.11.1 --keep-build-dir lf

    note:
        - since I learned that opam pin ... works for local customizations of projs (which it seems we need to mine data
        or at least idk how to mine data using the "official" version from the authors, perhaps this way is better since
        we force reproducibility of the version of the data set we train with).
        Thus, this ref: https://discuss.ocaml.org/t/how-does-one-reinstall-an-opam-package-proj-using-the-absolute-path-to-the-project/10944
        - hypothesis: opam install is needed just like make clean -C is needed, we need to force opam to recompile so
        that strace can get us the files we need.
            - alternatively, re-write strace & instead loop through the compiled files in coq-proj & create the right
            pycoq context. Not effortless! Avoid!
    """
    logging.info(f'{strace_build_opam_reinstall_opam_pin=}')
    # - activate switch
    # activate_opam_switch_via_eval(switch)
    opam_set_switch_via_opam_switch(switch)

    # - pins opam proj ref: https://discuss.ocaml.org/t/what-is-the-difference-between-opam-pin-and-opam-install-when-to-use-one-vs-the-other/10942/3
    pin_coq_project(switch, coq_project_name, coq_project_path)

    # - get coqc executable='/dfs/scratch0/brando9/.opam/ocaml-variants.4.07.1+flambda_coq-serapi.8.11.0+0.11.1/bin/coqc'
    executable: str = check_switch_has_coqc_and_return_path_2_coqc_excutable(switch)

    # - execute opam reinstall and strace it to get pycoq context filenames
    # command: str = f'opam reinstall {root_option()} --yes --switch {switch} --keep-build-dir {coq_project_name}'
    # command: str = f'opam reinstall {root_option()} --yes --switch {switch} --keep-build-dir {coq_project_name}'
    command = ''  # todo change above to list
    # need to change the above to list
    strace_logdir = pycoq.config.get_strace_logdir()
    logging.info(f"{executable}, {regex}, {workdir}, {command} {strace_logdir}")
    filenames: list[str] = pycoq.trace.strace_build(executable, regex, workdir, command.split(), strace_logdir)
    return filenames


def strace_build_with_make_clean(switch: str,
                                 coq_project_name: str,
                                 coq_project_path: str,
                                 regex: str,
                                 workdir: Optional = None,
                                 ) -> list[str]:
    """
    Builds the give coq-project & returns a list of pycoq context filenames after opam build of a package;
    monitoring calls with (linux's) strace (to get the pycoq context filenames).

    note:
        - for additional details see: strace_build_with_opam_reinstall(...) function

    coq_package='lf'
    coq_package_pin='/dfs/scratch0/brando9/pycoq/pycoq/test/lf'

        (iit_synthesis) brando9/afs/cs.stanford.edu/u/brando9/proverbot9001/coq-projects/CompCert $ source make.sh
        make clean -C ~/proverbot9001/coq-projects/CompCert

    todo: to deal with .remake, just use the given build without .configure and put the path to remake at the end,
    todo: might need to "parse" the build command for this to work, check other todo for build command
    """
    logging.info(f'{strace_build_with_make_clean=}')
    # - activate switch
    # activate_opam_switch_via_eval(switch)
    opam_set_switch_via_opam_switch(switch)

    # - pins opam proj ref: https://discuss.ocaml.org/t/what-is-the-difference-between-opam-pin-and-opam-install-when-to-use-one-vs-the-other/10942/3
    # pin_coq_project(switch, coq_project_name, coq_project_path)

    # - get coqc executable='/dfs/scratch0/brando9/.opam/ocaml-variants.4.07.1+flambda_coq-serapi.8.11.0+0.11.1/bin/coqc'
    executable: str = check_switch_has_coqc_and_return_path_2_coqc_excutable(switch)

    # - build with make clean -C and strace it
    # command: str = f'make clean -C {coq_project_path}'
    logging.info(f'{os.getcwd()=}')
    logging.info(f'{coq_project_path=}')
    os.chdir(coq_project_path)
    logging.info(f'{os.getcwd()=}')
    workdir = coq_project_path
    logging.info(f'{workdir=}')

    command: str = f'make clean'
    logging.info(f'{command=}')
    strace_logdir = pycoq.config.get_strace_logdir()
    logging.info(f"{executable}, {regex}, {workdir}, {command} {strace_logdir}")
    filenames: list[str] = pycoq.trace.strace_build(executable, regex, workdir, command.split(), strace_logdir)
    return filenames


def strace_build_with_make_sh(switch: str,
                              coq_project_name: str,
                              coq_project_path: str,
                              build_command: str,
                              regex: str,
                              workdir: Optional = None,
                              ) -> list[str]:
    """
cd /lfs/ampere4/0/brando9/proverbot9001/coq-projects/CompCert/
source make.sh

    note:
        - in coq_proj obj doesn't have build command proverbot9001's build sh script writes a simple make.

    ref:
        - https://stackoverflow.com/questions/28054448/specifying-path-to-makefile-using-make-command#:~:text=You%20can%20use%20the%20%2DC,a%20name%20other%20than%20makefile%20.
    """
    logging.info(f'{strace_build_with_make_sh=}')
    # logging.info(f'{coq_project_path=}')
    # coq_project_path: str = os.path.realpath(coq_project_path)
    logging.info(f'{coq_project_path=}')
    logging.info(f'{build_command=} (ran inside path2coqproj/main.sh')
    # - activate switch
    # activate_opam_switch_via_eval(switch)
    opam_set_switch_via_opam_switch(switch)

    # - pins opam proj ref: https://discuss.ocaml.org/t/what-is-the-difference-between-opam-pin-and-opam-install-when-to-use-one-vs-the-other/10942/3
    # pin_coq_project(switch, coq_project_name, coq_project_path)  # not needed

    # - get coqc executable='/dfs/scratch0/brando9/.opam/ocaml-variants.4.07.1+flambda_coq-serapi.8.11.0+0.11.1/bin/coqc'
    executable: str = check_switch_has_coqc_and_return_path_2_coqc_excutable(switch)

    # - build with make clean -C and strace it
    logging.info(f'{os.getcwd()=}')
    logging.info(f'{coq_project_path=}')
    os.chdir(coq_project_path)
    logging.info(f'{os.getcwd()=}')
    workdir = coq_project_path
    logging.info(f'{workdir=}')
    # command: str = f'source {coq_project_path}/main.sh {coq_project_path}'
    command: str = 'sh make.sh'
    logging.info(f'{command=}')
    strace_logdir = pycoq.config.get_strace_logdir()
    logging.info(f"{executable}, {regex}, {workdir}, {command} {strace_logdir}")
    filenames: list[str] = pycoq.trace.strace_build(executable, regex, workdir, command.split(), strace_logdir)
    logging.info(f'{filenames=}')
    return filenames


def check_switch_has_coqc_and_return_path_2_coqc_excutable(switch: str) -> str:
    """
    executable='/dfs/scratch0/brando9/.opam/ocaml-variants.4.07.1+flambda_coq-serapi.8.11.0+0.11.1/bin/coqc'
    """
    executable: str = opam_executable('coqc', switch)
    if executable is None:
        logging.critical(f"coqc executable is not found in {switch}")
        raise Exception(f'Coqc was not installed in {switch=}, trying installing coq?')
    else:
        logging.info(f'-> coqc was found! :) {executable=}')
    return executable


def pin_coq_project(switch: str,
                    coq_proj: str,
                    coq_proj_path: str,
                    ):
    """
    Opam pins a coq project to a coq project path in the given path.

    Note:
        1. this was inspired from PyCoq's original opam_pin_package.
        2. Since we are managing our own opam coq proj by getting the source instead of the original (for now, likely
        needed to make our code/data gen reproducible) -- we are using opam pin etc.
        "opam pin “allows local customisation of the packages in a given switch” (or “divert any package definition”)."

    ref:
        - for details on opam pin (and iff with opam install): https://discuss.ocaml.org/t/what-is-the-difference-between-opam-pin-and-opam-install-when-to-use-one-vs-the-other/10942/3
    """
    logging.info(f'{pin_coq_project=}')
    # command: str = f'opam pin -y {root_option()} --switch {switch} {coq_proj} {coq_proj_path}'
    command: list = ['opam'] + ['pin'] + ['-y'] + root_option() + ['--switch'] + [switch] + [coq_proj] + [coq_proj_path]
    logging.info(f"-> {command=}")
    logging.info(f"-> command={' '.join(command)=}")
    try:
        # result = subprocess.run(command.split(), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info(f'{result.stdout.decode()=}')
        logging.info(f'{result.stderr.decode()=}')
    except Exception as e:
        logging.critical(f'Error: {e=}')
        raise e


def activate_opam_switch_via_eval(switch: str):
    """
    Runs eval $(opam env --switch=switch --set-switch). In PyCoq usually the switch name
    indicates the coq version.
        e.g. runs `eval $(opam env --switch=coq-8.10 --set-switch)` within python.

    Note: not sure how previous PyCoq made sure the right switch was activated.

    ref:
        - for what `eval $(opam env)` does: https://stackoverflow.com/questions/30155960/what-is-the-use-of-eval-opam-config-env-or-eval-opam-env-and-their-differen
    """
    # raise NotImplementedError  # see: https://discuss.ocaml.org/t/is-eval-opam-env-switch-switch-set-switch-equivalent-to-opam-switch-set-switch/10957
    # for now use: opam_set_switch_via_opam_switch
    command: str = f"eval $(opam env --switch={switch} --set-switch)"
    # result = subprocess.run(command.split(), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # command: str = ["eval", f"$(opam env --switch={switch} --set-switch)"]
    # command: str = 'eval $(opam env)'
    logging.info(f"-> {command=}")
    try:
        result = subprocess.run(command.split(), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info(f'{result.stdout.decode()=}')
        logging.info(f'{result.stderr.decode()=}')
    except Exception as e:
        logging.critical(f'Error: {e=}')
        raise e


def opam_set_switch_via_opam_switch(switch: str):
    """
    Sets the current opam switch.

    (I think it's the same as eval $(opam env --switch={switch} --set-switch) ).

        SYNOPSIS
               opam switch [OPTION]... [COMMAND] [ARG]...

        set SWITCH
           Set the currently active switch, among the installed switches.

    ref:
        - https://discuss.ocaml.org/t/is-eval-opam-env-switch-switch-set-switch-equivalent-to-opam-switch-set-switch/10957
    """
    logging.info(f'{opam_set_switch_via_opam_switch=}')
    logging.info(f'{switch=}')
    # - change opam switch
    # command: str = f'opam switch set {switch}'
    # logging.info(f"-> {command=}")
    try:
        result = subprocess.run(f'opam switch set {switch}'.split(), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info(f'{result.stdout.decode()=}')
        logging.info(f'{result.stderr.decode()=}')
    except Exception as e:
        logging.critical(f'Error: {e=}')
        raise e


def run_eval_opam_env(switch: str,
                      ):
    """
Tries to run through opam exec command arg https://opam.ocaml.org/doc/man/opam-exec.html.

     eval $(opam env --switch=switch --set-switch)

    note:
        - command substituion: replace the command ran here $(cmd) with its output (string).
        It turns out, $() is called a command substitution. The command in between $() or backticks (“) is run and the
        output replaces $().
    ref:
        - https://discuss.ocaml.org/t/is-eval-opam-env-switch-switch-set-switch-equivalent-to-opam-switch-set-switch/10957/20
        - command sub: https://blog.wplauncher.com/what-is-in-linux/#:~:text=Example%20of%20command%20substitution%20using%20%24()%20in%20Linux%3A&text=Again%2C%20%24()%20is%20a%20command,another%20context%E2%80%9D%20(Source).
        - eval $(opam env): https://stackoverflow.com/questions/30155960/what-is-the-use-of-eval-opam-config-env-or-eval-opam-env-and-their-differen?noredirect=1&lq=1
        - there is a way with opam exec: https://discuss.ocaml.org/t/is-eval-opam-env-switch-switch-set-switch-equivalent-to-opam-switch-set-switch/10957/4
    """
    logging.info(f'{run_eval_opam_env=}')
    # - get cmd sub output
    try:
        cmd_sub_output: str = subprocess.check_output(f'opam env --switch={switch} --set-switch'.split())
    except Exception as e:
        logging.critical(f'Error: {e=}')
        raise e
    # - run command to eval
    # command: str = f'eval {cmd_sub_output}'  # doesn't seem possible https://stackoverflow.com/questions/53950225/python-check-output-call-to-eval-with-arguments-fails
    command: list[str] = f'opam exec --switch {switch}'.split()
    # command: list[str] = command + cmd_sub_output.split()
    command: list[str] = command + ['sh'] + [cmd_sub_output]
    logging.info(f"-> {command=}")
    try:
        # result = subprocess.run(command.split(), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info(f'{result.stdout.decode()=}')
        logging.info(f'{result.stderr.decode()=}')
    except Exception as e:
        logging.critical(f'Error: {e=}')
        raise e


def install_deps_opam_proj_pkg():
    """ might be nice to implement so that each coq proj can be easily installed with it's dependencies.
    But note, we might still have to download the coq-project source/code anyway, to mine it for data.
    Above check if it's true some day.
    """
    raise NotImplementedError


def get_active_opam_switch_according_to_bash_opam_switch_cmd(py_prints_on: bool = False) -> str:
    """ Prints the active switch according to the opam switch command & returns it as a string.
    """
    # - get output of opam switch
    try:
        # - run opam switch & get output as a single string
        result = subprocess.run('opam switch'.split(), capture_output=True, text=True)
        opam_switch_cmd_output_str: str = result.stdout
        print(f'\n{opam_switch_cmd_output_str}') if py_prints_on else None
        logging.info(f'{opam_switch_cmd_output_str=}')

        # - get actual opam switch
        opam_switch_lines: list[str] = opam_switch_cmd_output_str.split('\n')
        target_opam_switch_line: str = ''  # line with active opam switch
        for opam_switch_line in opam_switch_lines:
            if '->' in opam_switch_line or '→' in opam_switch_line:
                target_opam_switch_line = opam_switch_line
                break
        # print(f'{target_opam_switch_line=}') if py_prints_on else None
        logging.info(f'{target_opam_switch_line=}')
        if target_opam_switch_line == '':
            raise Exception(f'No active opam switch found: {target_opam_switch_line=}')
        split_target_line: list[str] = target_opam_switch_line.split()
        # format should be "->  switch_name compiler description" so we want the second element
        opam_switch: str = split_target_line[1]

        # - done getting active switch
        print(f'{opam_switch=}\n') if py_prints_on else None
        logging.info(f'{opam_switch=}')
        return opam_switch
    except Exception as e:
        logging.critical(f'Error: {e=}')
        raise e


def check_full_opam_env_switch_within_python(py_prints_on: bool = False):
    """

    Check:
        - "opam env" displays the right env variables being set
        - check "opam env" and "os.env" match (set?)
        - check if outpout of "opam switch" is consistent with all the above

    Effortless:
        - just check os.env has the right variables set according to "opam env"
        1. get the variable values form "opam env"
        2. check they are in os.env
    """
    # -
    import uutils
    opam_set_switch_via_opam_switch('coq-8.10')
    # - get output of opam env
    opam_env_dict: dict = get_variables_from_opam_env_output(py_prints_on=py_prints_on)
    print(f'opam_env_dict=')
    uutils.pprint_dict(opam_env_dict)
    # - get output of os.env
    # print(f'\n{os.environ=}\n')
    # - verify that subprocess indeed calls it's own process indepdent of python main
    assert not uutils.check_dict1_is_in_dict2(opam_env_dict, os.environ, verbose=True)
    # - get output of opam switch
    get_active_opam_switch_according_to_bash_opam_switch_cmd(py_prints_on=py_prints_on)
    return


def run_opam_env_from_within_python(py_prints_on: bool = False) -> str:
    """ Get the output of "opam env" from within python."""
    try:
        result = subprocess.run('opam env'.split(), capture_output=True, text=True)
        opam_env_output: str = result.stdout
        print(f'\n{opam_env_output=}\n') if py_prints_on else None
        logging.info(f'{opam_env_output=}')
        return opam_env_output
    except Exception as e:
        logging.critical(f'Error: {e=}')
        raise e


def get_variables_from_opam_env_output(py_prints_on: bool = False) -> dict[str, str]:
    """
    Get the opam env variables from the output of "opam env" from within python as a dict.
    This only tells us what the env variables needed to go into the opam switch that the subprocess that was ran was in.
    """
    opam_env_output: str = run_opam_env_from_within_python(py_prints_on=py_prints_on)
    opam_env_output_lines: list[str] = opam_env_output.split('\n')
    opam_env_dict: dict = {}
    for line in opam_env_output_lines:
        if line != '':
            str_with_var_and_value: str = line.split(';')[0]
            env_var_name, env_value = str_with_var_and_value.split('=')
            env_value: str = env_value.strip("'")
            # "OPAM_SWITCH_PREFIX='/Users/brandomiranda/.opam/test'; export OPAM_SWITCH_PREFIX;".split(';')[0].split('=').strip("'")
            print(f'{env_var_name=}, {env_value=}')
            opam_env_dict[env_var_name] = env_value
    return opam_env_dict


# - tests

def do_test_opam_did_switch_from_python_later_if_pycoqs_state_did_too():
    """ Test that opam did switch from pyton. """
    # -- before tests runs what is opam switch
    opam_switch: str = get_active_opam_switch_according_to_bash_opam_switch_cmd(py_prints_on=False)
    print(f'{opam_switch=}')
    assert opam_switch == 'test', f'{opam_switch=} != test'

    # -- test
    print('---- first switch ----')
    switch: str = 'coq-8.10'
    opam_set_switch_via_opam_switch(switch)
    opam_switch: str = get_active_opam_switch_according_to_bash_opam_switch_cmd(py_prints_on=True)
    print(f'new switch should be {switch=}')
    assert opam_switch == switch, f'{opam_switch=} != {switch=}'

    print('---- second switch ----')
    switch: str = 'coq-8.12'
    opam_set_switch_via_opam_switch(switch)
    opam_switch: str = get_active_opam_switch_according_to_bash_opam_switch_cmd(py_prints_on=True)
    print(f'new switch should be {switch=}')
    assert opam_switch == switch, f'{opam_switch=} != {switch=}'

    # -- opam switch through python via eval: so question: https://stackoverflow.com/questions/74803306/what-is-the-difference-between-eval-opam-env-switch-switch-set-switch-a
    print('-------- Check opam env is the expected one--------')
    check_full_opam_env_switch_within_python()


def check_os_env_has_the_vars_set_by_opam_env():
    # -- before tests runs what is opam switch
    # opam_switch: str = get_active_opam_switch_according_to_bash_opam_switch_cmd(py_prints_on=False)
    # print(f'{opam_switch=}')
    # assert opam_switch == 'test', f'{opam_switch=} != test'

    # -
    # run_opam_env_from_within_python(py_prints_on=True)
    # get_variables_from_opam_env_output()
    check_full_opam_env_switch_within_python()


# - run main
"""
python ~/pycoq/pycoq/opam.py
"""

if __name__ == '__main__':
    import time

    start = time.time()
    print(f'{start=}')
    # do_test_opam_did_switch_from_python_later_if_pycoqs_state_did_too()
    check_os_env_has_the_vars_set_by_opam_env()
    print(f'Done! {time.time() - start=}')
