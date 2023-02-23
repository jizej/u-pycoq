import os
import argparse
import re

from dataclasses_json import dataclass_json
from dataclasses import dataclass, field
from typing import List, Dict
from pycoq.pycoq_trace_config import CONTEXT_EXT

# import pycoq.log
import logging

TIMEOUT_TERMINATE = 5

_DEFAULT_SERAPI_LOGEXT = "._pycoq_serapi"


def serapi_log_fname(source):
    return source + _DEFAULT_SERAPI_LOGEXT


@dataclass
class IQR():
    I = List[str]
    Q = List[List[str]]  # List of pairs of str
    R = List[List[str]]  # List of pairs of str


@dataclass_json
@dataclass
class CoqContext:
    pwd: str
    executable: str
    target: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)

    def IQR(self) -> IQR:
        parser = argparse.ArgumentParser()
        parser.add_argument('-I', metavar=('dir'),
                            nargs=1,
                            action='append',
                            default=[],
                            help='append filesystem to ML load path')

        parser.add_argument('-Q', metavar=('dir', 'coqdir'),
                            nargs=2, action='append',
                            default=[],
                            help='append filesystem dir mapped to coqdir to coq load path')

        parser.add_argument('-R', metavar=('dir', 'coqdir'),
                            nargs=2, action='append',
                            default=[],
                            help='recursively append filesystem dir mapped '
                                 'to coqdir to coq load path')
        args, _ = parser.parse_known_args(self.args)

        return args

    def get_switch_name(self) -> str:
        """
        Get switch name from the env var OPAMSWITCH. Likely uses some trick that strace is doing to create this
        CoqContext in the first place.

        Note:
            - I noticed the env var OPAMSWITCH is only set when using (but perhaps opam exec --switch -- cmd does it too)
                "opam env --switch {switch} --set-switch"
            e.g.
                opam env --switch 'coq-8.10' --set-switch

                OPAMSWITCH='coq-8.10'; export OPAMSWITCH;
                OPAM_SWITCH_PREFIX='/lfs/ampere4/0/brando9/.opam/coq-8.10'; export OPAM_SWITCH_PREFIX;
                CAML_LD_LIBRARY_PATH='/lfs/ampere4/0/brando9/.opam/coq-8.10/lib/stublibs:/lfs/ampere4/0/brando9/.opam/coq-8.10/lib/ocaml/stublibs:/lfs/ampere4/0/brando9/.opam/coq-8.10/lib/ocaml'; export CAML_LD_LIBRARY_PATH;
                OCAML_TOPLEVEL_PATH='/lfs/ampere4/0/brando9/.opam/coq-8.10/lib/toplevel'; export OCAML_TOPLEVEL_PATH;
                MANPATH=':/usr/kerberos/man:/usr/share/man:/usr/local/man:/usr/man:/opt/puppetlabs/puppet/share/man:/lfs/ampere4/0/brando9/.opam/coq-8.10/man'; export MANPATH;
                PATH='/lfs/ampere4/0/brando9/.opam/coq-8.10/bin:/lfs/ampere4/0/brando9/miniconda/envs/metalearning_gpu/bin:/lfs/ampere4/0/brando9/miniconda/condabin:/lfs/ampere4/0/brando9/miniconda/bin:/lfs/ampere4/0/brando9/.local/bin:/lfs/ampere4/0/brando9/.ruby-build/bin:/lfs/ampere4/0/brando9/.rbenv/shims:/lfs/ampere4/0/brando9/.rbenv/bin:/usr/local/cuda-11.7/bin:/usr/kerberos/sbin:/usr/kerberos/bin:/afs/cs/software/sbin:/afs/cs/software/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin:/opt/puppetlabs/bin'; export PATH;
        """
        return str(self.env['OPAMSWITCH'])


@dataclass
class LocalKernelConfig():
    command: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    pwd: str = os.getcwd()


@dataclass
class RemoteKernelConfig():
    hostname: str
    port: int


def context_fname(target_fname):
    return target_fname + CONTEXT_EXT


def dump_context(fname: str, coq_context: CoqContext) -> str:
    '''
    returns fname of dumped coq_context
    '''
    with open(fname, 'w') as fout:
        logging.info(f'dump_context: recording context to {fname}')
        fout.write(coq_context.to_json())
        return (fname)


def load_context(fname: str) -> CoqContext:
    """
    loads CoqContext from pycoq_strace log file 
    """
    with open(fname, 'r') as f:
        return CoqContext.from_json(f.read())


def serapi_args(args: IQR) -> List[str]:
    res = []
    for x in args.I:
        res += ['-I', ','.join(x)]

    for x in args.Q:
        res += ['-Q', ','.join(x)]

    for x in args.R:
        res += ['-R', ','.join(x)]

    return res


def coqc_args(args: IQR) -> List[str]:
    res = []

    for x in args.I:
        res += ['-I'] + x

    for x in args.Q:
        res += ['-Q'] + x

    for x in args.R:
        res += ['-R'] + x

    return res


def serapi_kernel_config(kernel='sertop', opam_switch=None, opam_root=None, args=None,
                         pwd=os.getcwd(), remote=False):
    assert remote == False  # support for remote kernel not yet implemented

    if opam_switch is None:
        env = os.environ
        if args == None:
            args = []
        return LocalKernelConfig(command=[kernel] + args, env=os.environ, pwd=pwd)

    executable = 'opam'
    root_prefix = [] if opam_root is None else ['--root', opam_root]
    switch_prefix = [] if opam_switch is None else ['--switch', opam_switch]
    args_suffix = [] if args is None else args

    args = (['exec']
            + root_prefix
            + switch_prefix
            + ['--', kernel]
            + args_suffix)

    env = {'HOME': os.environ['HOME']}
    return LocalKernelConfig(command=[executable] + args, env=env, pwd=pwd)


def find_files(rootdir, pattern):
    regex = re.compile(pattern)
    for root, dirs, files in os.walk(rootdir):
        for name in files:
            if regex.match(name):
                yield (os.path.abspath(os.path.join(root, name)))
