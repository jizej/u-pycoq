"""

"""
from pprint import pprint

import shutil

import json
from collections import defaultdict, namedtuple

from pathlib import Path

import serlib
from pycoq.query_goals import SerapiGoals, srepr
from pycoq.split import agen_coq_stmts
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

import aiofile

from pdb import set_trace as st
from pprint import pprint

Thm = str
RID = int  # refined id -- corresponding to where the hole was placed

Filename = str

DataPoint = namedtuple("DataPoint", "x y")
X = namedtuple("X", "tt ppt ps ptp")
Y = namedtuple("Y", "hts")  # list[HelperTerm]

DataPoints = dict[RID, DataPoint]
DataFile = dict[Thm, DataPoints]
DataSet = dict[Filename, DataFile]

ProofState = namedtuple("ProofState", 'goals l_ctx g_ctx')

def get_proof_state() -> ProofState:
    return ''


async def go_through_proofs_in_file_and_print_proof_info(coq_package: str,
                                                         coq_package_pin: str,
                                                         write=False,
                                                         ):
    data_set: DataSet = {}

    # - for coq_filename in coq_project.filenames():
    filenames = pycoq.opam.opam_strace_build(coq_package, coq_package_pin)
    pprint(f'{filenames=}')
    for filename in filenames:
        data_set[filename]: DataFile = {}
        # - for thm in get_thms(coq_filename):
        # thms = get_thms(filename)
        # --
        if "TwoGoals" in filename:
            print(f'-> {filename=}')
            async with aiofile.AIOFile(filename, 'rb') as fin:
                in_thm: bool = False
                coq_ctxt = pycoq.common.load_context(filename)
                cfg = opam.opam_serapi_cfg(coq_ctxt)
                logfname = pycoq.common.serapi_log_fname(os.path.join(coq_ctxt.pwd, coq_ctxt.target))
                res = []
                async with pycoq.serapi.CoqSerapi(cfg, logfname=logfname) as coq:
                    # --
                    for stmt in pycoq.split.coq_stmts_of_context(coq_ctxt):
                        print(f'--> {stmt=}')
                        _, _, coq_exc, _ = await coq.execute(stmt)
                        if coq_exc:
                            return res
                        _serapi_goals = await coq.query_goals_completed()
                        post_fix = coq.parser.postfix_of_sexp(_serapi_goals)
                        ann = serlib.cparser.annotate(post_fix)
                        serapi_goals: SerapiGoals = pycoq.query_goals.parse_serapi_goals(coq.parser, post_fix, ann,
                                                                                         pycoq.query_goals.SExpr)
                        # --
                        if "Theorem" in stmt or "Lemma" in stmt:
                            in_thm: bool = True
                            tt: str = stmt
                            data_set[filename][tt]: DataPoints = {}
                            rid = -1
                            refined_proof_script: str = "" + tt
                        elif in_thm:
                            # - for i, stmt in enumerate(thm.tt.proof.stmts):
                            rid += 1
                            # - get x
                            ppt = None

                            ps = None
                            st()

                            ptp = None
                            x = X(tt=tt, ppt=ppt, ps=ps, ptp=ptp)
                            y = Y(hts=[])
                            # - store x in data set D
                            data_points: DataPoints = data_set[filename][tt]
                            data_points[rid] = DataPoint(x=x, y=y)  # basically an append
                            if stmt == 'Proof.':
                                refined_proof_script += "\n{stmt}. refine (hole {rid} _)."
                            else:
                                refined_proof_script += "\n{stmt};refine (hole {rid} _)."
                        elif "Qed." in stmt or stmt in "Defined.":
                            in_thm: bool = False
                            # - get y's
                            refined_proof_script += "Show Proof."
                            _, _, coq_exc, _ = await coq.execute(refined_proof_script)
                            if coq_exc:
                                return res
                            # fill data set with helper terms
                            D_t: DataPoints = data_set[filename][tt]
                            # rept = get_ept()  # await coq.query_goals_completed()
                            rept = None  # the entire proof term with the refined decoration, now we can extract the helper terms/holes and match them to rids
                            assert rid == len(D_t), f'Unexpected error, the last rid {rid=} should be ' \
                                                    f'the number of stmts executed in the current proof for {tt=}' \
                                                    f'but was {len(D_t)=}'
                            # get_helper_terms(rid, rept, D_t, thm)
                            rid = 0
                        else:
                            pass
                    # print(f'---> {res=}')


def main():
    """
    My debug example executing the commands in a script.

    opam pin -y --switch debug_proj_4.09.1 debug_proj file:///home/bot/pycoq/debug_proj
    :return:
    """
    sys.setrecursionlimit(10000)

    write: bool = False
    coq_package = 'lf'
    coq_package_pin = f"file://{with_prefix('lf')}"
    # write: bool = False
    # coq_package = 'debug_proj'
    # # coq_package_pin = f"file://{os.path.expanduser('~/pycoq/debug_proj')}"
    # coq_package_pin = f"{os.path.expanduser('~/pycoq/debug_proj')}"

    # go_through_proofs_in_file_and_print_proof_info(coq_package, coq_package_pin, write)
    asyncio.run(go_through_proofs_in_file_and_print_proof_info(coq_package, coq_package_pin, write))


if __name__ == '__main__':
    print()
    print('------------------------ output of python to terminal --------------------------\n')
    start_time = time.time()
    Path(pycoq.config.get_var('log_filename')).expanduser().unlink(missing_ok=True)
    main()
    duration = time.time() - start_time
    logging.info(f"Duration {duration} seconds.\n\a")
    print(f"Duration {duration} seconds.\n")

    # print('------------------------ output of logfile --------------------------\n')
    # cat_file(pycoq.config.get_var('log_filename'))
    # Path(pycoq.config.get_var('log_filename')).expanduser().unlink(missing_ok=True)
