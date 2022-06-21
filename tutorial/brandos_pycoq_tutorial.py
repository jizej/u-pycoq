"""

"""
from pprint import pprint

import shutil

import json
from collections import defaultdict

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


async def go_through_proofs_in_file_and_print_proof_info(coq_package: str,
                                                         coq_package_pin: str,
                                                         write=False,
                                                         ):
    # - for coq_filename in coq_project.filenames():
    filenames = pycoq.opam.opam_strace_build(coq_package, coq_package_pin)
    pprint(f'{filenames=}')
    for filename in filenames:
        # - for thm in get_thms(coq_filename):
        # thms = get_thms(filename)
        if "TwoGoals" in filename:
            print(f'-> {filename=}')
            async with aiofile.AIOFile(filename, 'rb') as fin:
                in_thm: bool = False
                coq_ctxt = pycoq.common.load_context(filename)
                cfg = opam.opam_serapi_cfg(coq_ctxt)
                logfname = pycoq.common.serapi_log_fname(os.path.join(coq_ctxt.pwd, coq_ctxt.target))
                res = []
                async with pycoq.serapi.CoqSerapi(cfg, logfname=logfname) as coq:
                    for stmt in pycoq.split.coq_stmts_of_context(coq_ctxt):
                        print(f'--> {stmt=}')
                        _, _, coq_exc, _ = await coq.execute(stmt)
                        if coq_exc:
                            # break
                            return res
                        _serapi_goals = await coq.query_goals_completed()
                        post_fix = coq.parser.postfix_of_sexp(_serapi_goals)
                        ann = serlib.cparser.annotate(post_fix)
                        serapi_goals: SerapiGoals = pycoq.query_goals.parse_serapi_goals(coq.parser, post_fix, ann,
                                                                                         pycoq.query_goals.SExpr)
                        if "Theorem" in stmt or "Lemma" in stmt:
                            in_thm: bool = True
                            # parsed_goals: str = srepr(coq.parser, post_fix, ann, 0, int)
                            # print(f'{parsed_goals=}')
                            pprint(f'{serapi_goals=}')
                            return
                        elif "Qed." in stmt or stmt in "Defined.":
                            in_thm: bool = False
                        # print(f'{serapi_goals=}')
                        # return
                        # res.append((stmt, _serapi_goals, serapi_goals))
                        # - for i, stmt in enumerate(thm.tt.proof.stmts):
                        # if in_thm:
                        #     # - get x
                        #     # ppt = get_ppt()  # no pt has no hole refinement
                        #     _, _, coq_exc, _ = await coq.execute('Show Proof.')
                        #     if coq_exc:
                        #         # break
                        #         return res
                        #     _serapi_goals = await coq.query_goals_completed()
                        #     post_fix = coq.parser.postfix_of_sexp(_serapi_goals)
                        #     ann = serlib.cparser.annotate(post_fix)
                        #     serapi_goals = pycoq.query_goals.parse_serapi_goals(coq.parser, post_fix, ann,
                        #                                                         pycoq.query_goals.SExpr)
                        #     res.append((stmt, _serapi_goals, serapi_goals))
                        #     print(f"{serapi_goals=}")
                        #     return
                        # ps = get_ps()  # ultimately be (LC, goals, top ten envs from coqhammer)
                        # ptp += f"\n {stmt}"
                        # - label proof term with which x corresponds to which holes
                        # rid: RefinedID = i
                        # if stmt == "Proof.":  # or i == 0
                        #     refined_proof_script += "\n{stmt}. refine (hole {rid} _)."
                        # else:
                        #     refined_proof_script += "\n{stmt};refine (hole {rid} _)."

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
