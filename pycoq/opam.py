'''
functions to work with opam

Opam terms:
opam pin/pinning = ... why do we need this? difference with opam install?
'''
import sys
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
from pycoq.project_splits_meta_data import CoqProj

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
        res = subprocess.run(command, check=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        return res.stdout.decode().strip()
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
        res = subprocess.run(command, check=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        logging.info(f"{command}: {res.stdout.decode()} {res.stderr.decode()}")
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
        res = subprocess.run(command, check=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        logging.info(f"{command}: {res.stdout.decode()} {res.stderr.decode()}")
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
        res = subprocess.run(command, check=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        logging.info(f"{command}: {res.stdout.decode()} {res.stderr.decode()}")
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
        res = subprocess.run(command, check=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        logging.info(f"{command}: {res.stdout.decode()} {res.stderr.decode()}")
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
        res = subprocess.run(command, check=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        logging.info(f"{command}: {res.stdout.decode()} {res.stderr.decode()}")
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
        res = subprocess.run(command, check=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        logging.info(f"{command}: {res.stdout.decode()} {res.stderr.decode()}")
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

        res = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        logging.info(f'{res.stdout.decode=}')
        logging.info(f'{res.stderr.decode=}')
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
    #     res = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #
    #     logging.info(f"-> command=[{' '.join(command)}]")
    #     logging.info(f'{res.stdout.decode=}')
    #     logging.info(f'{res.stderr.decode=}')
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
        res = subprocess.run(command, check=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        logging.info(res.stdout.decode(), res.stderr.decode())
        root = res.stdout.decode().strip()
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
        res = subprocess.run(command, check=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        logging.info(f"{command}: {res.stdout.decode()} {res.stderr.decode()}")
        ans = res.stdout.decode().strip()
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
        res = subprocess.run(command,
                             cwd=coq_ctxt.pwd,
                             check=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        logging.info(f"{command}: {res.stdout.decode()} {res.stderr.decode()}")
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
        res = subprocess.run(command,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        # print(f'{res.stdout.decode()}')
        logging.info(f"{command}: {res.stdout.decode()} {res.stderr.decode()}")
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
    # assert switch == coq_proj.switch, f'Err: switches don\'t match {switch=} {coq_proj.switch=}'
    logging.info(f'{strace_build_coq_project_and_get_filenames=}')
    logging.info(f'{root_option()=}')

    # - use switch corresponding to the coq proj
    logging.info(f'{coq_proj=}')
    switch: str = coq_proj.switch  # e.g. coq-8.10
    coq_project_name: str = coq_proj.project_name  # e.g. CompCert
    coq_project_path: str = coq_proj.get_coq_proj_path()  # e.g. ~/proverbot9001/coq-projects/
    build_command: str = coq_proj.build_command  # e.g. proverbot9001 had: configure x86_64-linux && make todo solve
    logging.info(f'{switch=}')
    logging.info(f'{coq_project_name=}')
    logging.info(f'{coq_project_path=}')
    logging.info(f'{build_command=}')

    # - activate opam switch for coq project
    # activate_opam_switch(switch)
    opam_set_switch(switch)

    # -- get list of coq files from coq project
    # - since we are in the code that build the coq proj & gets list of filename pycoq contexts, we need to opam pin https://stackoverflow.com/questions/74777579/is-opam-pin-project-needed-when-one-wants-to-install-a-opam-project-with-opam-re
    # pin_coq_project(switch, coq_project_name, coq_project_path)  # todo double check

    # - keep building & stracing until success i.e. filenames is none empty.
    regex: str = pycoq.pycoq_trace_config.REGEX if regex_to_get_filenames is None else regex_to_get_filenames
    logging.info(f'{regex=}')
    filenames: list[str] = []
    # if len(filenames) == 0:
    #     # else build with the coq-projs make file
    #     filenames: list[str] = strace_build_with_make_clean(switch, coq_project_name, coq_project_path, regex)
    # if len(filenames) == 0:
    #     # try to build it with VPs opam reinstall
    #     # filenames: list[str] = strace_build_opam_reinstall_opam_pin(switch, coq_project_name, coq_project_path, regex)
    #     filenames: list[str] = strace_build_opam_reinstall(switch, coq_project_path, regex)
    if len(filenames) == 0:
        # else use build command
        filenames: list[str] = strace_build_with_build_command(switch, coq_project_name, coq_project_path,
                                                               build_command, regex)
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
    # activate_opam_switch(switch)
    opam_set_switch(switch)

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
    raise NotImplementedError
    logging.info(f'{strace_build_with_make_clean=}')
    # - activate switch
    # activate_opam_switch(switch)
    opam_set_switch(switch)

    # - pins opam proj ref: https://discuss.ocaml.org/t/what-is-the-difference-between-opam-pin-and-opam-install-when-to-use-one-vs-the-other/10942/3
    # pin_coq_project(switch, coq_project_name, coq_project_path)

    # - get coqc executable='/dfs/scratch0/brando9/.opam/ocaml-variants.4.07.1+flambda_coq-serapi.8.11.0+0.11.1/bin/coqc'
    executable: str = check_switch_has_coqc_and_return_path_2_coqc_excutable(switch)

    # - build with make clean -C and strace it
    command: str = f'make clean -C {coq_project_path}'
    logging.info(f'{command=}')
    st()
    strace_logdir = pycoq.config.get_strace_logdir()
    logging.info(f"{executable}, {regex}, {workdir}, {command} {strace_logdir}")
    filenames: list[str] = pycoq.trace.strace_build(executable, regex, workdir, command.split(), strace_logdir)
    return filenames


def strace_build_with_build_command(switch: str,
                                    coq_project_name: str,
                                    coq_project_path: str,
                                    build_command: str,
                                    regex: str,
                                    workdir: Optional = None,
                                    ) -> list[str]:
    """
cd /lfs/ampere4/0/brando9/proverbot9001/coq-projects/CompCert/
source make.sh

    ref:
        - https://stackoverflow.com/questions/28054448/specifying-path-to-makefile-using-make-command#:~:text=You%20can%20use%20the%20%2DC,a%20name%20other%20than%20makefile%20.
    """
    logging.info(f'{strace_build_with_build_command=}')
    # logging.info(f'{coq_project_path=}')
    # coq_project_path: str = os.path.realpath(coq_project_path)
    logging.info(f'{coq_project_path=}')
    logging.info(f'{build_command=} (ran inside path2coqproj/main.sh')
    # - activate switch
    # activate_opam_switch(switch)
    opam_set_switch(switch)

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


def strace_build_opam_reinstall(switch: str,
                                # coq_project_name: str,
                                coq_project_path: str,
                                regex: str,
                                workdir: Optional = None,
                                ):
    """

NAME
       opam-reinstall - Reinstall a list of packages.

SYNOPSIS
       opam reinstall [OPTION]... [PACKAGES]...

ARGUMENTS
       PACKAGES
           List of package names, with an optional version or constraint, e.g
           `pkg', `pkg.1.0' or `pkg>=0.5' ; or directory names containing
           package description, with explicit directory (e.g. `./srcdir' or
           `.')

    note:
        ref: https://discuss.ocaml.org/t/how-does-one-reinstall-an-opam-package-proj-using-the-absolute-path-to-the-project/10944

    """
    logging.info(f'{strace_build_opam_reinstall_opam_pin=}')
    # - activate switch
    # activate_opam_switch(switch)
    opam_set_switch(switch)

    # - pins opam proj ref: https://discuss.ocaml.org/t/what-is-the-difference-between-opam-pin-and-opam-install-when-to-use-one-vs-the-other/10942/3
    # pin_coq_project(switch, coq_project_name, coq_project_path)  # todo: don't think we need this, I really hope

    # - get coqc executable='/dfs/scratch0/brando9/.opam/ocaml-variants.4.07.1+flambda_coq-serapi.8.11.0+0.11.1/bin/coqc'
    executable: str = check_switch_has_coqc_and_return_path_2_coqc_excutable(switch)

    # - execute opam reinstall and strace it to get pycoq context filenames
    # command: str = f'opam reinstall {root_option()} --yes --switch {switch} --keep-build-dir {coq_project_name}'
    # command: str = f'opam reinstall {root_option()} --yes --switch {switch} --keep-build-dir {coq_project_name}'
    command: list = ['opam'] + ['reinstall'] + root_option() + ['--yes'] + ['--switch', switch] + \
                    ['--keep-build-dir', coq_project_path] + \
                    [coq_project_path]
    strace_logdir = pycoq.config.get_strace_logdir()
    logging.info(f"{executable}, {regex}, {workdir}, {command} {strace_logdir}")
    # filenames: list[str] = pycoq.trace.strace_build(executable, regex, workdir, command.split(), strace_logdir)
    filenames: list[str] = pycoq.trace.strace_build(executable, regex, workdir, command, strace_logdir)
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
    # command: str = f'opam pin -y {root_option()} --switch {switch} {coq_proj} {coq_proj_path}'
    command: list = ['opam'] + ['pin'] + ['-y'] + root_option() + ['--switch'] + [switch] + [coq_proj] + [coq_proj_path]
    logging.info(f"-> {command=}")
    logging.info(f"-> command={' '.join(command)=}")
    try:
        # res = subprocess.run(command.split(), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        res = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info(f'{res.stdout.decode=}')
        logging.info(f'{res.stderr.decode=}')
    except Exception as e:
        logging.critical(f'Error: {e=}')
        raise e


def activate_opam_switch(switch: str):
    """
    Runs eval $(opam env --switch=switch --set-switch). In PyCoq usually the switch name
    indicates the coq version.
        e.g. runs `eval $(opam env --switch=coq-8.10 --set-switch)` within python.

    Note: not sure how previous PyCoq made sure the right switch was activated.

    ref:
        - for what `eval $(opam env)` does: https://stackoverflow.com/questions/30155960/what-is-the-use-of-eval-opam-config-env-or-eval-opam-env-and-their-differen
    """
    raise NotImplementedError  # see: https://discuss.ocaml.org/t/is-eval-opam-env-switch-switch-set-switch-equivalent-to-opam-switch-set-switch/10957
    # for now use: opam_set_switch
    command: str = f"eval $(opam env --switch={switch} --set-switch)"
    res = subprocess.run(command.split(), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    command: str = ["eval", f"$(opam env --switch={switch} --set-switch)"]
    command: str = 'eval $(opam env)'
    logging.info(f"-> {command=}")
    try:
        res = subprocess.run(command.split(), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # res = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info(f'{res.stdout.decode=}')
        logging.info(f'{res.stderr.decode=}')
    except Exception as e:
        logging.critical(f'Error: {e=}')
        raise e


def opam_set_switch(switch: str):
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
    command: str = f'opam switch set {switch}'
    logging.info(f"-> {command=}")
    try:
        res = subprocess.run(command.split(), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # res = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info(f'{res.stdout.decode=}')
        logging.info(f'{res.stderr.decode=}')
    except Exception as e:
        logging.critical(f'Error: {e=}')
        raise e


def install_denpds_opam_proj():
    """ might be nice to implement so that each coq proj can be easily installed with it's dependencies.
    But note, we might still have to download the coq-project source/code anyway, to mine it for data.
    Above check if it's true some day.
    """
    raise NotImplementedError


# - tests

def bash_cmd_to_str(cmd: list[str]) -> str:
    cmd: str = ' '.join(cmd)
    return cmd


def get_cmd_pin_lf():
    cmd = ['opam', 'pin', '-y',
           '--switch', 'ocaml-variants.4.07.1+flambda_coq-serapi.8.11.0+0.11.1',
           'lf', '/home/bot/pycoq/pycoq/test/lf']
    cmd: str = bash_cmd_to_str(cmd)
    return cmd


def get_cmd_pin_debug_proj():
    cmd = ['opam', 'pin', '-y',
           '--switch', 'ocaml-variants.4.07.1+flambda_coq-serapi.8.11.0+0.11.1',
           'debug_proj', '/home/bot/iit-term-synthesis/coq_projects/debug_proj']
    cmd: str = bash_cmd_to_str(cmd)
    return cmd


def get_make_cmd():
    cmd: str = ['make', '-C', '/home/bot/iit-term-synthesis/coq_projects/debug_proj']
    cmd: str = ['make', 'clean', '-C', '/home/bot/iit-term-synthesis/coq_projects/debug_proj']
    cmd: str = bash_cmd_to_str(cmd)
    return cmd


if __name__ == '__main__':
    print('')
    # cmd: list[str] = ['opam', 'pin', '-y', '--switch', 'ocaml-variants.4.07.1+flambda_coq-serapi.8.11.0+0.11.1', 'debug_proj', '/home/bot/iit-term-synthesis/coq_projects/debug_proj']
    # cmd: str = bash_cmd_to_str(cmd)
    # cmd: str = get_cmd_pin_debug_proj()
    # cmd: str = get_cmd_pin_lf()
    # cmd: str = get_make_cmd()
    print(cmd)
    print('Done!\a')
