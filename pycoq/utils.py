import asyncio
from contextlib import asynccontextmanager

from pycoq.common import CoqContext, LocalKernelConfig
from pycoq.serapi import CoqSerapi

from pdb import set_trace as st


@asynccontextmanager
async def get_coq_serapi(coq_ctxt: CoqContext) -> CoqSerapi:
    """
    Returns CoqSerapi instance that is closed with a with statement.
    CoqContext for the file is also return since it can be used to manipulate the coq file e.g. return
    the coq statements as in for `stmt in pycoq.split.coq_stmts_of_context(coq_ctxt):`.

    example use:
    ```
    filenames = pycoq.opam.opam_strace_build(coq_package, coq_package_pin)
        filename: str
        for filename in filenames:
            with get_coq_serapi(filename) as coq, coq_ctxt:
                for stmt in pycoq.split.coq_stmts_of_context(coq_ctxt):
    ```

    ref:
    - https://stackoverflow.com/questions/37433157/asynchronous-context-manager
    - https://stackoverflow.com/questions/3693771/understanding-the-python-with-statement-and-context-managers

    Details:

    Meant to replace (see Brando's pycoq tutorial):
    ```
            async with aiofile.AIOFile(filename, 'rb') as fin:
                coq_ctxt = pycoq.common.load_context(filename)
                cfg = opam.opam_serapi_cfg(coq_ctxt)
                logfname = pycoq.common.serapi_log_fname(os.path.join(coq_ctxt.pwd, coq_ctxt.target))
                async with pycoq.serapi.CoqSerapi(cfg, logfname=logfname) as coq:
    ```
    usually then you loop through the coq stmts e.g.
    ```
                    for stmt in pycoq.split.coq_stmts_of_context(coq_ctxt):
    ```
    """
    try:
        import pycoq
        from pycoq import opam
        from pycoq.common import LocalKernelConfig
        import os

        # - note you can't return the coq_ctxt here so don't create it due to how context managers work, even if it's needed layer for e.g. stmt in pycoq.split.coq_stmts_of_context(coq_ctxt):
        # _coq_ctxt: CoqContext = pycoq.common.load_context(coq_filepath)
        # - not returned since it seems its only needed to start the coq-serapi interface
        cfg: LocalKernelConfig = opam.opam_serapi_cfg(coq_ctxt)
        logfname = pycoq.common.serapi_log_fname(os.path.join(coq_ctxt.pwd, coq_ctxt.target))
        # - needed to be returned to talk to coq
        coq: CoqSerapi = pycoq.serapi.CoqSerapi(cfg, logfname=logfname)
        # - crucial, or coq._kernel is None and .execute won't work
        await coq.__aenter__()  # calls self.start(), this  must be called by itself in the with stmt beyond yield
        yield coq
    except Exception as e:
        import traceback
        await coq.__aexit__(Exception, e, traceback.format_exc())
        # coq_ctxt is just a data class serapio no need to close it, see: https://github.com/brando90/pycoq/blob/main/pycoq/common.py#L32
    finally:
        import traceback
        err_msg: str = 'Finally exception clause'
        exception_type, exception_value = Exception('Finally exception clause'), ValueError(err_msg)
        print(f'{traceback.format_exc()=}')
        await coq.__aexit__(exception_type, exception_value, traceback.format_exc())
        # coq_ctxt is just a data class so no need to close it, see: https://github.com/brando90/pycoq/blob/main/pycoq/common.py#L32


# -

async def loop_through_files_original():
    ''' '''
    import os

    import aiofile

    import pycoq
    from pycoq import opam

    coq_package = 'lf'
    from pycoq.test.test_autoagent import with_prefix
    coq_package_pin = f"file://{with_prefix('lf')}"

    print(f'{coq_package=}')
    print(f'{coq_package_pin=}')
    print(f'{coq_package_pin=}')

    filenames: list[str] = pycoq.opam.opam_strace_build(coq_package, coq_package_pin)
    filename: str
    for filename in filenames:
        print(f'-> {filename=}')
        async with aiofile.AIOFile(filename, 'rb') as fin:
            coq_ctxt: CoqContext = pycoq.common.load_context(filename)
            cfg: LocalKernelConfig = opam.opam_serapi_cfg(coq_ctxt)
            logfname = pycoq.common.serapi_log_fname(os.path.join(coq_ctxt.pwd, coq_ctxt.target))
            async with pycoq.serapi.CoqSerapi(cfg, logfname=logfname) as coq:
                print(f'{coq._kernel=}')
                for stmt in pycoq.split.coq_stmts_of_context(coq_ctxt):
                    print(f'--> {stmt=}')
                    _, _, coq_exc, _ = await coq.execute(stmt)
                    if coq_exc:
                        raise Exception(coq_exc)


async def loop_through_files():
    """
    to test run in linux:
    ```
        python ~pycoq/pycoq/utils.py
        python -m pdb -c continue ~/pycoq/pycoq/utils.py
    ```
    """
    import pycoq

    coq_package = 'lf'
    from pycoq.test.test_autoagent import with_prefix
    coq_package_pin = f"file://{with_prefix('lf')}"

    print(f'{coq_package=}')
    print(f'{coq_package_pin=}')
    print(f'{coq_package_pin=}')

    filenames: list[str] = pycoq.opam.opam_strace_build(coq_package, coq_package_pin)
    filename: str
    for filename in filenames:
        print(f'-> {filename=}')
        coq_ctxt: CoqContext = pycoq.common.load_context(filename)
        async with get_coq_serapi(coq_ctxt) as coq:
            print(f'{coq=}')
            print(f'{coq._kernel=}')
            stmt: str
            for stmt in pycoq.split.coq_stmts_of_context(coq_ctxt):
                print(f'--> {stmt=}')
                _, _, coq_exc, _ = await coq.execute(stmt)
                if coq_exc:
                    raise Exception(coq_exc)


if __name__ == '__main__':
    asyncio.run(loop_through_files_original())
    asyncio.run(loop_through_files())
    print('Done!\a\n')
