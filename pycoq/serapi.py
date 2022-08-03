'''
functions to work with coq-serapi
'''

# TODO: replace print with logging

# TODO: in wait for answer completed if received 
# (Of_sexp_error"sertop/sertop_ser.ml.cmd_of_sexp: sum tag \"Query\" has incorrect number of arguments"(invalid_sexp(Query((pp((pp_format PpCoq))))Definition th13)))
# then stop waiting and return error 

import re
import json
import time

from typing import List, Union, Tuple

import serlib.parser

import pycoq.kernel

from dataclasses import dataclass
from collections.abc import Iterable

from pdb import set_trace as st

COMPLETED_PATTERN = re.compile(r"\(Answer\s\d+\sCompleted\)")
ANSWER_PATTERN = re.compile(r"\(Answer\s(\d+)(.*)\)")
ANSWER_PATTERN_OBJLIST = re.compile(r"\(Answer\s(\d+)(\(ObjList.*\))\)")
ADDED_PATTERN = re.compile(r"\(Added\s(\d+)(.*)\)")
COQEXN_PATTERN = re.compile(r"\((CoqExn\(.*\))\)")

from pycoq.query_goals import SerapiGoals


def ocaml_string_quote(s: str):
    """
    OCaml-quote string 
    """
    return s.replace('\\', '\\\\').replace('\"', '\\\"')


def sexp(x) -> str:
    """
    make s-expression of python object
    """
    if isinstance(x, int):
        return str(x)
    elif isinstance(x, str):
        return '"' + ocaml_string_quote(x) + '"'
    elif isinstance(x, Iterable):
        return '(' + " ".join(sexp(e) for e in x) + ')'
    else:
        raise TypeError(f'pycoq.serapi.sexp for type {type(x)} is not yet implemented')


def matches_answer_completed(line: str, ind: int):
    """
    checks if coq-serapi responses matches "Answer Completed"
    """
    return line.strip() == f'(Answer {ind} Completed)'


def matches_answer(line: str, sent_index):
    """ 
    if line matches Answer
    return (index, answer)
    """

    match = ANSWER_PATTERN.match(line)
    if match and int(match.group(1)) == sent_index:
        return match.group(2).strip()


def parse_added_sid(line: str):
    """
    find sentence id (sid) in coq-serapi response
    """

    match = ADDED_PATTERN.match(line)
    if match:
        return int(match.group(1))
    else:
        return None


@dataclass
class CoqExn():
    message: str


def parse_coqexn(line: str):
    """
    parse CoqExn in coq-serapi response
    """
    match = COQEXN_PATTERN.match(line)
    if match:
        return CoqExn(message=match.group(0))
    else:
        return None


class CoqSerapi():
    """ 
    object of CoqSerapi provides communication with coq through coq-serapi interface

    initialise by passing either a kernel object that has interface

        kernel.readline()
        kernel.readlines()
        kernel.writeline()
        
    of config defined by the protocol pycoq.kernel.LocalKernel

    """

    def __init__(self, kernel_or_cfg: Union[pycoq.kernel.LocalKernel, pycoq.common.LocalKernelConfig], logfname=None):
        """ 
        wraps coq-serapi interface on the running kernel object
        """
        self._logfname = logfname
        if isinstance(kernel_or_cfg, pycoq.kernel.LocalKernel):
            self._kernel = kernel_or_cfg
            self._cfg = None
        elif isinstance(kernel_or_cfg, pycoq.common.LocalKernelConfig):
            self._kernel = None
            self._cfg = kernel_or_cfg
        else:
            raise TypeError("CoqSerapi class must be initialized either with an existing kernel "
                            "object of type pycoq.kernel.LocalKernel or config object of type "
                            " pycoq.common.LocalKernelConfig "
                            f"but the supplied argument has type {type(kernel_or_cfg)}")

        self._sent_history = []
        self._serapi_response_history = []
        self._added_sids = []
        self._executed_sids = []
        self.parser = serlib.parser.SExpParser()

    async def start(self):
        """ starts new kernel if not already connected
        """
        if (self._kernel is None):
            self._kernel = pycoq.kernel.LocalKernel(self._cfg)
            await self._kernel.start()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exception_type, exception_value, traceback):
        await self._kernel.__aexit__(exception_type, exception_value, traceback)
        async for line in self._kernel.readlines():
            self._serapi_response_history.append(line)

        if not self._logfname is None:
            await self.save_serapi_log()

    async def add(self, coq_stmt: str):
        """ sends serapi command
        (Add () "coq_stmt")
        """

        cmd_tag = len(self._sent_history)

        quoted = ocaml_string_quote(coq_stmt)
        cmd = f'(Add () "{quoted}")'
        await self._kernel.writeline(cmd)
        self._sent_history.append(cmd)

        return cmd_tag

    async def query_goals(self, opts: str = '') -> str:
        """ sends serapi command 
        (Query () Goals)
        """
        cmd_tag = len(self._sent_history)
        cmd = f'(Query ({opts}) Goals)'
        await self._kernel.writeline(cmd)
        self._sent_history.append(cmd)
        return cmd_tag

    async def query_definition(self, name) -> str:
        """ 
        sends serapi command
        (Query () Definition name)
        """
        cmd_tag = len(self._sent_history)
        cmd = f'(Query () (Definition {name}))'
        await self._kernel.writeline(cmd)
        self._sent_history.append(cmd)
        return cmd_tag

    async def exec(self, sid: int):
        """ sends serapi command to execute coq statement sid
        (Exec sid)
        """
        cmd_tag = len(self._sent_history)

        cmd = f'(Exec {sid})'
        await self._kernel.writeline(cmd)
        self._sent_history.append(cmd)

        return cmd_tag

    async def cancel(self, sids: List[int]) -> bool:
        """ cancels given list of sids
        """
        cmd_tag = len(self._sent_history)
        cmd = f'(Cancel {sexp(sids)})'

        await self._kernel.writeline(cmd)
        self._sent_history.append(cmd)
        return cmd_tag

    async def wait_for_answer_completed(self, cmd_tag: int):
        """ read and save responses from serapi to _serapi_response_history
        stop when (Answer cmd_tag Completed) is received
        """
        while True:
            line = await self._kernel.readline()
            if line == '':
                print("empty readline: ", end='')
                time.sleep(0.1)
                print("process terminated with proc code", self._kernel._proc.returncode)
                raise EOFError

            self._serapi_response_history.append(line)
            if matches_answer_completed(line, cmd_tag):
                return len(self._serapi_response_history)

    async def add_completed(self, coq_stmt: str) -> Tuple[int, int, Union[int, str]]:
        """ sends serapi command Add CoqSerapi.add()
        awaits completed response; returns list of sids / CoqExns
        """

        cmd_tag = await self.add(coq_stmt)
        resp_ind = await self.wait_for_answer_completed(cmd_tag)

        sids = await self.added_sids(cmd_tag)  # separate added sids vs CoqExns
        self._added_sids.append(sids)
        coqexns = await self.coqexns(cmd_tag)

        return (cmd_tag, resp_ind, sids, coqexns)

    async def exec_completed(self, sid: int) -> List[str]:  # returns list of coqexn
        """ sends serapi command Exec
        awaits completed response
        returns ind of completed message
        and CoqExns
        """
        cmd_tag = await self.exec(sid)
        resp_ind = await self.wait_for_answer_completed(cmd_tag)
        coqexns = await self.coqexns(cmd_tag)

        return (cmd_tag, resp_ind, coqexns)

    async def cancel_completed(self, sids: List[int]) -> List[str]:  # List[CoqExn]
        cmd_tag = await self.cancel(sids)
        resp_ind = await self.wait_for_answer_completed(cmd_tag)
        coqexns = await self.coqexns(cmd_tag)
        if coqexns != []:
            raise RuntimeError(f'Unexpected error during coq-serapi command Cancel'
                               f'with CoqExns {coqexns}')
        return (cmd_tag, resp_ind)

    async def _query_goals_completed(self, opts: str = '') -> List[str]:
        """ returns literal serapi response (Query () Goals)
        """
        cmd_tag = await self.query_goals(opts)
        resp_ind = await self.wait_for_answer_completed(cmd_tag)
        coqexns = await self.coqexns(cmd_tag)
        if coqexns != []:
            raise RuntimeError(f'Unexpected error during coq-serapi command Query () Goals '
                               f'with CoqExns {coqexns}')
        goals = await self._answer(cmd_tag)
        return goals

    async def _query_definition_completed(self, name) -> List[str]:
        """
        returns literal serapi response (Query () Definition name)
        """
        cmd_tag = await self.query_definition(name)
        resp_ind = await self.wait_for_answer_completed(cmd_tag)
        coqexns = await self.coqexns(cmd_tag)
        if coqexns != []:
            raise RuntimeError(f'Unexpected error during coq-serapi command Query () Definition {name}'
                               f'with CoqExns {coqexns}')
        definition = await self._answer(cmd_tag)
        return definition

    async def query_goals_completed(self, opts: str = '') -> str:
        """
        returns a single serapi response on (Query () Goals)
        """

        serapi_goals: List[str] = await self._query_goals_completed(opts)

        if len(serapi_goals) != 1:
            print("pycoq received list of goals", serapi_goals)
            raise RuntimeError("unexpected behaviour of pycoq - serapi - coq API: "
                               "query goals returned a list of len != 1 in serapi response")
        else:
            return serapi_goals[0]

    async def serapi_goals(self) -> SerapiGoals:
        """
        returns parsed SerapiGoals object
        """
        _serapi_goals: str = await self.query_goals_completed()
        post_fix = self.parser.postfix_of_sexp(_serapi_goals)
        ann = serlib.cparser.annotate(post_fix)
        return pycoq.query_goals.parse_serapi_goals(self.parser, post_fix, ann, pycoq.query_goals.SExpr)

    async def query_local_ctx_and_goals(self) -> Union[str, list]:
        """
        Returns the proof state as the local context + goals as a single string.
        In particular, sends serapi command
            (Query ((pp ((pp_format PpStr)))) Goals)
        If it's not in proving mode (e.g. not in a thoerem) then it returns the empty string ''.

        Details:
            Want to get the entire context from SerAPI from some Py-SerAPI interface.
            (Add () "Lemma addn0 n : n + 0 = n.")
            (Add () "Proof.")
            (Exec 3)
            (Query ((pp ((pp_format PpStr)))) Goals)

            Then extract the CoqString from answer:
            (Answer 2 Completed)
            (Query ((pp ((pp_format PpStr)))) Goals)
            (Answer 3 Ack)
            (Answer 3
             (ObjList
              ((CoqString  "\
                          \n  n : nat\
                          \n============================\
                          \nn + 0 = n"))))
            (Answer 3 Completed)
        """
        from sexpdata import loads

        _local_ctx_and_goals: str = await self.query_goals_completed(opts='(pp ((pp_format PpStr)))')
        _local_ctx_and_goals: list = loads(_local_ctx_and_goals)
        print(f'{_local_ctx_and_goals=}')
        assert _local_ctx_and_goals[0].value() == 'ObjList'
        if _local_ctx_and_goals[1] == []:
            return []  # if not in proof mode there is no coq-str obj so return empty list
        else:
            # example smallest valid goals: (ObjList ((CoqString "")))
            obj_list: list = _local_ctx_and_goals[1]
            coq_str_sexp: list = obj_list[0]  # e.g. (CoqString "")
            assert len(coq_str_sexp) == 2
            assert coq_str_sexp[0].value() == 'CoqString'
            # local_ctx_and_goals: str = _local_ctx_and_goals[1][0][1]
            local_ctx_and_goals: str = coq_str_sexp[1]
            return local_ctx_and_goals

    async def in_proof_mode(self) -> bool:
        """
        Detects if we are in proof mode.

        This is done by making sure the serapi goals query returns some CoqString -- even the empty string means your
        in proof mode still.
        We are only not in proof mode if when we query the goals it returns nothing -- the empty list [].
        e.g.
        in proof mode, query goals returns string:
            case 2: in the middle of some step.
            ```
            rlwrap sertop --printer=human

            (Add () "
            Theorem easy: nat -> nat. intros.
            ")

            (Exec 3)

            (Query ((pp ((pp_format PpStr)))) Goals)
            ```
            (Query ((pp ((pp_format PpStr)))) Goals)
            (Answer 2 Ack)
            (Answer 2
             (ObjList ((CoqString  "\
                                  \n  H : nat\
                                  \n============================\
                                  \nnat"))))
            (Answer 2 Completed)
            -> Conclusion: proof state with (lots) of string content, so your in proof mode


            case 3: proof is done (but without a Qed.)
            ```
            rlwrap sertop --printer=human

            (Add () "
            Theorem easy: nat -> nat. intros. apply O.
            ")
            (Exec 4)

            (Query ((pp ((pp_format PpStr)))) Goals)
            ```
            (Query ((pp ((pp_format PpStr)))) Goals)
            (Answer 2 Ack)
            (Answer 2 (ObjList ((CoqString ""))))
            (Answer 2 Completed)
            -> Conclusion: when proof is done then we have goals being the empty string (note proof term is completed).


        if proof is officially closed by a Qed. then the goals query doesn't even return a coq string object:
            ```
            rlwrap sertop --printer=human

            (Add () "
            Theorem easy: nat -> nat. intros. apply O. Qed.
            ")

            (Exec 5)

            (Query ((pp ((pp_format PpStr)))) Goals)
            ```
            (Query ((pp ((pp_format PpStr)))) Goals)
            (Answer 2 Ack)
            (Answer 2 (ObjList ()))
            (Answer 2 Completed)
            -> Conclusion: when proof is closed, then the goals is literally empty, no coq string object.
        """
        goals = await self.query_local_ctx_and_goals()
        not_in_proof_mode: bool = goals == []
        in_proof_mode: bool = isinstance(goals, str)
        in_proof_mode = not not_in_proof_mode and in_proof_mode
        return in_proof_mode

    async def empty_but_existent_goals(self) -> bool:
        """
        Returns true if your current set of goals is empty -- in fact the empty string.
        Useful to detect if your current coq-stmt (tactic) completed all goals.

        Note: if you executed a Qed. then it will return False, since there exists no goals.

        Details: works by checking the goals is the empty string.
        e.g. your last tactic closed the proof:
            rlwrap sertop --printer=human

            (Add () "
            Theorem easy: nat -> nat. intros. apply O.
            ")
            (Exec 4)

            (Query ((pp ((pp_format PpStr)))) Goals)
            ```
            (Query ((pp ((pp_format PpStr)))) Goals)
            (Answer 2 Ack)
            (Answer 2 (ObjList ((CoqString ""))))
            (Answer 2 Completed)
        """
        goals = await self.query_local_ctx_and_goals()
        proof_closed_done: bool = goals == ""
        return proof_closed_done

    async def query_coq_proof(self):
        """
        (Query ((pp ((pp_format PpStr)))) CoqProof)
        """
        _local_ctx_and_goals: str = await self.query_goals_completed(opts='(pp ((pp_format PpStr)))')
        raise NotImplemented

    async def get_current_proof_term_via_add(self) -> Union[str, list[CoqExn]]:
        """
        Returns the proof term (proof object, lambda term etc.) representation of the proof.

        (Add () "Show Proof.")
        """
        coq_stmt: str = 'Show Proof.'
        cmd_tag, resp_ind, coq_exns, sids = await self.execute(coq_stmt)
        if coq_exns:
            print(f'{await self.query_local_ctx_and_goals()=}')
            print(f'{await self.in_proof_mode()=}')
            st()
            raise ValueError(f'Got an error, are you sure you can get the proof term right now? err: {coq_exns=}'
                             f', {self._sent_history=}')
            # return coq_exns
        # todo: another place where perhaps we should move to VP's serlib? unsure if worth it.
        # - extract_proof_term, following the Feedback constructor from type answer serapir response: http://ejgallego.github.io/coq-serapi/coq-serapi/Serapi/Serapi_protocol/#type-answer.Feedback
        from sexpdata import loads
        serapi_response: str = self._serapi_response_history[-3]
        res: str = serapi_response
        _res: list = loads(res)
        feedback: list = _res[-1]
        assert len(feedback) == 4
        contents: list = feedback[-1]
        assert len(contents) == 2
        message: list = contents[-1]
        assert len(message) == 5
        string: list = message[-1]
        assert string[0].value() == 'str'
        # - edge case if the sexpdata sees an atom that is a string it didn't wrap it in a Symbol for some reason
        if isinstance(string[-1], str):
            ppt: str = string[-1]
        else:
            ppt: str = string[-1].value()
        return ppt

    async def query_definition_completed(self, name) -> str:
        """
        returns a single serapi response on (Query () Definition name))
        """
        definition = await self._query_definition_completed(name)

        if len(definition) != 1:
            print("pycoq received definition", definition)
            raise RuntimeError("unexpected behaviour of pycoq - serapi - coq API: "
                               "definition returned a list of len != 1 in serapi response")
        else:
            return definition[0]

    async def show_name_of_theorem(self) -> str:
        """
        Returns name/identifier of theorem/conjecture currently being proved (as a string).
        see: https://coq.github.io/doc/v8.10/refman/proof-engine/proof-handling.html#coq:cmdv.show-conjectures

        e.g.
Theorem zero_plus_n_eq_n:
  forall n: nat, 0 + n = n.
Show Conjectures.

zero_plus_n_eq_n
---
(Add () "
Theorem add_easy_0'':
forall n:nat,
  0 + n = n.
Proof.
    intros.
    simpl.
")
(Exec 5)

(Add () "Show Conjectures.")
(Exec 6)

(Answer 3 Ack)
(Answer 3
 (Added 6
  ((fname ToplevelInput) (line_nb 1) (bol_pos 0) (line_nb_last 1)
   (bol_pos_last 0) (bp 0) (ep 17))
  NewTip))
(Answer 3 Completed)

(Exec 6)
(Answer 4 Ack)
(Feedback
 ((doc_id 0) (span_id 6) (route 0) (contents (ProcessingIn master))))
(Feedback ((doc_id 0) (span_id 5) (route 0) (contents Processed)))
(Feedback
 ((doc_id 0) (span_id 6) (route 0)
  (contents
   (Message (level Notice) (loc ()) (pp (Pp_string add_easy_0''))
    (str add_easy_0'')))))
(Feedback ((doc_id 0) (span_id 6) (route 0) (contents Processed)))
(Answer 4 Completed)
        """
        cmd_tag, resp_ind, coq_exns, sids = await self.execute(coq_stmt="Show Conjectures.")
        if coq_exns:
            raise ValueError(f'Error: {coq_exns=}')
        # parse response see self.get_current_proof_term_via_add as an example
        raise NotImplemented

    async def show_open_all_goals_and_existential_variables(self):
        """
        Displays all open goals / existential variables in the current proof along with the type and the context of each variable.
        Execute" "Show Existentials."

Displays all open goals / existential variables in the current proof along with the type and the context of each variable.

https://coq.github.io/doc/v8.10/refman/proof-engine/proof-handling.html#coq:cmdv.show-conjectures
3:14
Show Existentials. is interesting too.  It shows the proof state for each goal/e-variable, and also makes clear what the e-variables names are in the proof.
3:15
https://coq.github.io/doc/v8.10/refman/proof-engine/proof-handling.html#coq:cmdv.show-existentials
```

```
Theorem zero_plus_n_eq_n:
  forall n: nat, 0 + n = n.
  Show.
 Proof.
  intros.
  simpl.
  Show Existentials.

Existential 1 =
?Goal : [n : nat |- n = n]

Displays all open goals / existential variables in the current proof along with the type and the context of each variable.
        """
        cmd_tag, resp_ind, coq_exns, sids = await self.execute(coq_stmt="Show Existentials.")
        if coq_exns:
            raise ValueError(f'Error: {coq_exns=}')
        # parse response see self.get_current_proof_term_via_add as an example
        raise NotImplemented

    async def execute(self, coq_stmt: str) -> List[CoqExn]:
        """ tries to execute coq_stmt
        if CoqExn then cancel coq_stmt
        returns (cmd_tag, resp_ind, List[CoqExn], List[executed sids])
        """

        cmd_tag, resp_ind, sids, coqexns = await self.add_completed(coq_stmt)

        assert all(isinstance(sid, int) for sid in sids)
        if len(sids) == 0:
            print(f"notice: {len(sids)} sids in coq_stmt: {coq_stmt}")

        if coqexns:
            (cmd_tag, resp_ind) = await self.cancel_completed(sids)
            return (cmd_tag, resp_ind, coqexns, [])

        for sid in sids:
            cmd_tag, resp_ind, coqexns = await self.exec_completed(sid)
            if coqexns:
                (cmd_tag, resp_ind) = await self.cancel_completed(sids)
                return (cmd_tag, resp_ind, coqexns, None)
            self._executed_sids.append(sid)

        return (cmd_tag, resp_ind, [], sids)

    async def added_sids(self, cmd_tag) -> List[Union[int, str]]:
        """ 
        returns the list of sid (sentence id) from history of serapi responses

        """
        cur = len(self._serapi_response_history) - 1
        res = []
        while cur >= 0:
            line = self._serapi_response_history[cur].strip()
            line_answer = matches_answer(line, cmd_tag)
            if line_answer is None or line_answer == 'Completed':
                cur -= 1
                continue
            if line_answer == 'Ack':
                break
            sid = parse_added_sid(line_answer)
            if not sid is None:
                res.append(sid)
            cur -= 1

        return list(reversed(res))

    async def coqexns(self, cmd_tag):
        '''
        retrieves List of coqexns that serapi transmited on a given serapi command with cmd_tag
        '''
        cur = len(self._serapi_response_history) - 1
        res = []
        while cur >= 0:
            line = self._serapi_response_history[cur].strip()
            line_answer = matches_answer(line, cmd_tag)
            if line_answer is None or line_answer == 'Completed':
                cur -= 1
                continue
            if line_answer == 'Ack':
                break

            coqexn = parse_coqexn(line_answer)
            if not coqexn is None:
                res.append(coqexn)
            cur -= 1

        return res

    async def _answer(self, cmd_tag) -> List[str]:
        """ return the list of str matching answer cmd_tag
        """
        cur = len(self._serapi_response_history) - 1
        res = []
        while cur >= 0:
            line = self._serapi_response_history[cur].strip()
            line_answer = matches_answer(line, cmd_tag)
            if line_answer is None or line_answer == 'Completed':
                cur -= 1
                continue
            if line_answer == 'Ack':
                break
            res.append(line_answer)
            cur -= 1

        return res

    async def save_serapi_log(self):
        """
        dumps json log of sent and received serapi lines
        """
        with open(self._logfname, 'w') as f:
            stderr = []
            async for line in self._kernel.readlines_err(quiet=False):
                stderr.append(line)

            json.dump({'response': self._serapi_response_history,
                       'sent': self._sent_history,
                       'stderr': stderr}, fp=f)

    async def echo(self, quiet=False, timeout=None):
        async for line in self._kernel.readlines(timeout=timeout, quiet=quiet):
            print(line, end='')

    async def echo_err(self, quiet=False, timeout=None):
        async for line in self._kernel.readlines_err(timeout=timeout, quiet=quiet):
            print(line, end='')

    def finished(self):
        return not self._kernel._proc.returncode is None
