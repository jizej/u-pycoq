"""

A data set is made from a collection (list) of coq projs/pkgs.
Each of these coq projs/pkgs has split for their coq .v files.
An example split (see: ~proverbot9001/coqgym_projs_splits.json or ~/iit-term-synthesis/lf_projs_splits.json):
    split: list[dict] =
    [
        {
            "project_name": "constructive-geometry",
            "train_files": [
                "problems.v",
                "affinity.v",
                "basis.v",
                "orthogonality.v",
                "part1.v",
                "part3.v",
                "part2.v"
            ],
            "test_files": [],
            "switch": "coq-8.10"
        },
        ...
        ]
"""
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Union, Optional

from pycoq.utils import clean_up_filename
from uutils import load_json, merge_two_dicts


@dataclass()
class CoqProj:
    """ Models a single dict element in the X_projs.json file for a single coq project. """
    project_name: str
    train_files: list[str]
    test_files: list[str]
    switch: str
    #  root path to where this coq proj lives & *all& the rest of them live e.g. ~/proverbot9001/coq-projects/
    path_2_coq_projs: str

    # - other names based on coq-gym
    build_command: str = ''  # e.g. "build_command": "./configure.sh && make"
    original_build_command: str = ''  # "build_command": "./configure.sh && make"
    build_partition: str = ''  # e.g.         "build_partition": "long"

    # coq_proj_version ... shoould work for the selected coq ver in (opam) switch

    def get_split(self, split: str) -> list[str]:
        if split == 'train':
            return self.train_files
        else:
            return self.test_files

    def is_filename_in_split(self, filename: str, split: str) -> bool:
        split_files: list[str] = self.get_split(split)
        filename = clean_up_filename(filename)
        in_split: bool = any([split_filename in filename for split_filename in split_files])
        return in_split

    def get_coq_proj_path(self) -> str:
        """
        e.g.
            get_coq_proj_path='/dfs/scratch0/brando9/pycoq/pycoq/test/lf'
        """
        return f"{self.path_2_coq_projs}/{self.project_name}"


# basically entire benchmark
@dataclass
class CoqProjs:
    """Represents the info & coq projs in a X_projects_splits.json in a dataclass. """
    # the actual split info for each coq project/package -- since for each project we need to specify which files are for train & which are for test
    coq_projs: list[CoqProj]
    # root path to where original/raw all coq projects live e.g. proverbot's coq-projects folder
    path_2_coq_projs: Path
    # path to the splits for each coq project
    path_2_coq_projs_json_splits: Path
    # home root used when generating data set
    home_root: Path = str(Path.home())


def list_dict_splits_2_list_splits(coq_projs: list[dict], path_2_coq_projs: Path) -> list[CoqProj]:
    """
    e.g. use
        coq_projs_splits: list[CoqProj] = list_coq_projs_2_list_coq_projs(coq_projs_splits)
    more advanced: https://stackoverflow.com/questions/53376099/python-dataclass-from-a-nested-dict
    """
    path_2_coq_projs: Path = path_2_coq_projs.expanduser()
    path_2_coq_projs: str = str(path_2_coq_projs)

    # - loop
    kwargs: dict = dict(path_2_coq_projs=path_2_coq_projs)
    coq_proj_splits_: list[CoqProj] = []
    coq_proj_dict: dict
    for coq_proj_dict in coq_projs:
        kwargs: dict = merge_two_dicts(kwargs, coq_proj_dict)  # merges by replacing according to 2nd arg
        coq_proj_split: CoqProj = CoqProj(**kwargs)
        coq_proj_splits_.append(coq_proj_split)
    return coq_proj_splits_


def get_debug_projprojs_meta_data() -> CoqProjs:
    pass


def get_lf_coq_projs() -> CoqProjs:
    path_2_coq_projs: Path = Path('~/pycoq/debug_proj_pycoq_lf/').expanduser()
    path_2_coq_projs_json_splits: Path = Path('~/pycoq/lf_projs_splits.json').expanduser()
    coq_projs: list[dict] = load_json(path_2_coq_projs_json_splits)
    logging.info(f'{coq_projs[0].keys()=}')
    coq_projs: list[CoqProj] = list_dict_splits_2_list_splits(coq_projs, path_2_coq_projs)
    assert len(coq_projs) == 1
    coq_projs: CoqProjs = CoqProjs(path_2_coq_projs=path_2_coq_projs,
                                   path_2_coq_projs_json_splits=path_2_coq_projs_json_splits,
                                   coq_projs=coq_projs)
    return coq_projs


def get_debug_two_coq_projects_train_test() -> CoqProjs:
    """
    Note:
        for this to work you need the make.sh scripts. So you'd need to run
        1. the dependecies files (to instal deps).
        2. the build to install the make.
        it's not really needed if you can install deps in python and then the second is just an opam switch set followed by
        a make.
    """
    # note: the CompCert path sym links to the CompCert in coq_projects
    path_2_coq_projs: Path = Path('~/pycoq/debug_two_coq_projects_train_test/').expanduser()
    path_2_coq_projs_json_splits: Path = Path('~/pycoq/debug_two_coq_projects_train_test_splits.json').expanduser()
    coq_projs: list[dict] = load_json(path_2_coq_projs_json_splits)
    logging.info(f'{coq_projs[0].keys()=}')
    coq_projs: list[CoqProj] = list_dict_splits_2_list_splits(coq_projs, path_2_coq_projs)
    coq_projs: CoqProjs = CoqProjs(path_2_coq_projs=path_2_coq_projs,
                                   path_2_coq_projs_json_splits=path_2_coq_projs_json_splits,
                                   coq_projs=coq_projs)
    return coq_projs


def get_compcert_coq_projs() -> CoqProjs:
    """
    Get data set coq projs info (i.e. meta data) e.g. path2 coq-proj
    """
    # note: the CompCert path sym links to the CompCert in coq_projects
    path_2_coq_projs: Path = Path('~/proverbot9001/coq-projects/').expanduser()  # todo: move to pycoq location
    path_2_coq_projs_json_splits: Path = Path(
        '~/proverbot9001/compcert_projs_splits.json').expanduser()  # todo: move to pycoq & have it work when you build from pycoq
    coq_projs: list[dict] = load_json(path_2_coq_projs_json_splits)
    logging.info(f'{coq_projs[0].keys()=}')
    coq_projs: list[CoqProj] = list_dict_splits_2_list_splits(coq_projs, path_2_coq_projs)
    assert len(coq_projs) == 1
    coq_projs: CoqProjs = CoqProjs(path_2_coq_projs=path_2_coq_projs,
                                   path_2_coq_projs_json_splits=path_2_coq_projs_json_splits,
                                   coq_projs=coq_projs)
    return coq_projs


def get_coqgym_coq_projs() -> CoqProjs:
    pass


# - coq proj splits generation

def create_official_makefiles_for_coq_proj_from_path_2_original_coq_repo(
        path2MakeFile: str = '~/pycoq/debug_proj/MakeFile',
        switch_2_set_from_premade: Optional[str] = None
):
    """
    todo: plan https://github.com/brando90/pycoq/issues/11
    Create a coq

    - copy the default MakeFile from debug_proj, all coq projs use that version
    - now loop through the opam src proj path give & append the file names to _CoqProject. This is needed for the
    MakeFile form the previous step to work.
    - then the project should be ready to be make with make clean. Make sure to cd to that repo within python
    (this is optional since it can take time but useful to do to double check your setup works)

    note:
        - this assumes you've already set up your opam switch & coq install already outside
        - if note you optionally specify the switch, compiler & coq version you proj needs
    todo: should be split by project or by train, test files? project doesn't need us to worry about topolical sort.
        Tests a harder gen. Let's do this + it's simpler.
    """
    from pycoq.opam import opam_set_switch
    # -- optionally set switch or create entire switch from scratch
    if switch_2_set_from_premade:
        # move to a switch you already made
        opam_set_switch(switch_2_set_from_premade)
    else:
        raise ValueError('Not implemented but idea is to create entire switch using'
                         'in pycoqs opam function create_entire_pycoq_switch_from_scratch')

    # -- copy debug proj MakeFile to new project
    pass

    # -- make _CoqProject if not there, loop through foles * add *.v$ files and the coqc args
    # flags for coqc, path where folder is and stuff is ran from and name of project/Module
    # -Q.Debug_Proj
    # -arg
    # "-w all"
    # pycoq's lf uses
    # -Q.LF
    pass

    # - test if install worked by make clean project, cd into it
    pass


def create_splits_for_json_files_from_coq_proj(path2coq_proj: str,
                                               path2save: Path,
                                               splits_json_filename: str,
                                               switch: str,
                                               split_ratio: tuple = (0.9, 0.1),
                                               ):
    """


    note:
        - based on first result in google search: In general, putting 80% of the data in the training set, 10% in the validation set, and 10% in the test set is a good split to start with.
        - you have to process the train files if you want a val set. Usually 0.8:0.1:0.1 is done
            - have some code that give 0.9:0.1 does that split for you somewhere in uutils
        - splits created randomly, no dag awareness, that's how coq gym did it anyway: https://github.com/princeton-vl/CoqGym/discussions/79
        - actually inspecting more carefully, proverbot9001 splits seem that entire coq repos are either at train
        or at test. Except for only compcert on it's own not in coq-gym.

    """
    pass
    # -- loop through all *.v% recursively (nothing in end in filename) then put that in some split
    # - collect all in their own train test lists
    # - split (approx) according to ratio
    # - save new json proj


def pycoq_build_coq_project():
    """
```bash
for project in $(jq -r '.[].project_name' compcert_projs_splits.json); do
    echo $project

    echo "#!/usr/bin/env bash" > coq-projects/$project/make.sh
    echo ${INIT_CMD} >> coq-projects/$project/make.sh
    if $(jq -e ".[] | select(.project_name == \"$project\") | has(\"build_command\")" \
         coqgym_projs_splits.json); then
        BUILD=$(jq -r ".[] | select(.project_name == \"$project\") | .build_command" \
                   coqgym_projs_splits.json)
    else
        BUILD="make"
    fi

    SWITCH=$(jq -r ".[] | select(.project_name == \"$project\") | .switch" coqgym_projs_splits.json)

    # why not just call opam switch? or `opam switch set {$SWITCH}`
    echo "eval \"$(opam env --set-switch --switch=$SWITCH)\"" >> coq-projects/$project/make.sh

    echo "$BUILD $@" >> coq-projects/$project/make.sh
```

    main idea:
        - it makes a make.sh file that builds the project according to the stored build command in the json file
        - seems you can't infer it from the coq-project path, it's hardcoded in the json splits manually todo improve
        - but if the build_command isn't there then they use just use make. Though note that
            `./configure x86_64-linux && make` seems common too.
    """
    pass


def create_new_splits_for_json_files_from_premake_coq_project_splits(coq_proj_2_target: str,
                                                                     path2save: str,
                                                                     splits_prefix: str,  # prefix for splits.json file
                                                                     splits_json_filename: Optional[str] = None,
                                                                     split_ratio: tuple = (0.9, 0.1),
                                                                     ):
    """
    note:
        - recommended:
            splits_json_filename: str = f'{splits_prefix}_projs_splits.json'
    """
    pass
    splits_json_filename: str = f'{splits_prefix}_projs_splits.json' if splits_json_filename is None else splits_json_filename
    # - loop through all *.v%  (first merge train, test though usually proverbot's train or test is empty)
    # - seperate all in their own train test lists
    # - split (approx) according to ratio
    # - save new json proj, use the original defaults, switch, build_command (if present) etc. would be nice to say
    # which coq version coq project depends on since this has to be stored somewhere since we are using a local version
    # local version needed because we are extracting data from it using strace & coqc, idk if data can be extracted
    # from the remote version


# -


def get_proj_splits_based_on_name_of_path2data(path2data: Union[Path, str]) -> CoqProjs:
    # expanduser(path2data)
    name_path2data: str = str(path2data)
    if 'pycoq_lf_debug' in name_path2data:
        coq_projs: CoqProjs = get_lf_coq_projs()
    elif 'debug_proj' in name_path2data:
        coq_projs: CoqProjs = get_debug_projprojs_meta_data()
    elif 'debug_two_coq_projects_train_test' in name_path2data:
        coq_projs: CoqProjs = get_debug_two_coq_projects_train_test()
    elif 'compcert' in name_path2data:
        coq_projs: CoqProjs = get_compcert_coq_projs()
    elif 'coqgym' in name_path2data:
        coq_projs: CoqProjs = get_coqgym_coq_projs()
    else:
        raise ValueError(f'Invalid type of data set/benchmark, got (invalid): {name_path2data=}')
    return coq_projs


# - tests

def generate_sf_lf_from_soln_repo():
    # create_official_makefiles_for_coq_proj_from_path_2_original_coq_repo()
    pass


if __name__ == '__main__':
    import time
    from uutils import report_times

    start = time.time()
    generate_sf_lf_from_soln_repo
    print(f"\nSuccess Done!: {report_times(start)}\a")
