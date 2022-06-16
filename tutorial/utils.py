from typing import Union

from pathlib import Path


# def set_up_opam(coq_package: str,
#                 coq_package_pin=None,
#                 coq_serapi=COQ_SERAPI,
#                 coq_serapi_pin=COQ_SERAPI_PIN,
#                 compiler=DEFAULT_OCAML,
#                 ):
#     """
#     Set up opam if not activated already.
#     Maybe useful when going through a coq_proj for the first time and nothing wrt opam is setup.
#
#     Dockerfile sets it up as follows:
#         RUN opam init --disable-sandboxing
#         RUN opam switch create debug_proj_4.09.1 4.09.1
#         RUN opam switch debug_proj_4.09.1
#         # RUN eval $(opam env)
#         RUN opam repo add coq-released https://coq.inria.fr/opam/released
#         RUN opam pin add -y coq 8.11.0
#         RUN opam install -y coq-serapi
#         RUN eval $(opam env)
#     """
#     # - create swtich name from strings based on serapi. Serapi name here is not really special.
#     # compiler = ocaml-variants.4.07.1+flambda
#     # switch = 'ocaml-variants.4.07.1+flambda_coq-serapi.8.11.0+0.11.1'
#     switch: str = opam_switch_name(compiler, coq_serapi, coq_serapi_pin)
#
#     # - returns True if opam can create or recreate switch successfully
#     if not opam_create_switch(switch, compiler):
#         return False
#
#     # - pins package to source in the switch
#     # if not opam_pin_package(coq_serapi, coq_serapi_pin, coq_serapi, coq_serapi_pin, compiler):
#     if not opam_pin_package_to_switch(coq_serapi, coq_serapi_pin, switch):
#             return False
#
#     # - installs package (coq_serapi) into a selected switch or updates
#     if not opam_install_package(switch, coq_serapi):
#         return False
#
#     # - installs current coq project to current switch
#     if ((not coq_package_pin is None) and
#             not opam_pin_package_to_switch(coq_package, coq_package_pin, switch)):
#             # not opam_pin_package(coq_package, coq_package_pin, coq_serapi, coq_serapi_pin, compiler)):
#         return False

# def opam_pin_package_to_switch()

def cat_file(path2filename: Union[str, Path]):
    """prints/displays file contents. Do path / filename or the like outside of this function. ~ is alright to use. """
    if not isinstance(path2filename, Path):
        path2filename: Path = Path(path2filename).expanduser()
    path2filename.expanduser()
    with open(path2filename, 'r') as f:
        print(f.read())
