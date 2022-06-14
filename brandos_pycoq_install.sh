# for now just putting commands I'm running in terminal. Hope to evetually organize this better for compilation/install
# of python depedent tools + coq depedent tools.

# - install python: https://stackoverflow.com/questions/49118277/what-is-the-best-way-to-install-conda-on-macos-apple-mac
# install brew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
#  install wget to get miniconda
#brew install wget

# - install miniconda
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh -O ~/miniconda.sh
bash ~/miniconda.sh -b -p $HOME/miniconda
# source /Users/my_username/opt/anaconda3/bin/activate
source ~/miniconda/bin/activate
conda init zsh
# conda init
conda update -n base -c defaults conda
conda install conda-build

conda create -n pycoq python=3.9
conda activate pycoq
#conda remove --name metalearning2 --all

# - install pycoq
pip install -e .
#pip install -e ~/pycoq

# - install opam
#brew install opam
# https://stackoverflow.com/questions/72522266/how-does-one-install-opam-with-conda-for-mac-apple-os-x
conda install -c conda-forge opam
opam init
# if doing local env? https://stackoverflow.com/questions/72522412/what-does-eval-opam-env-do-does-it-activate-a-opam-environment
#eval $(opam env)

# - install coq: see https://stackoverflow.com/questions/71117837/how-does-one-install-a-new-version-of-coq-when-it-cannot-find-the-repositories-i
# local install
#opam switch create . 4.12.1
#eval $(opam env)
#opam repo add coq-released https://coq.inria.fr/opam/released
#opam install coq

# If you want a single global (wrt conda) coq installation (for say your laptop):
#opam switch create 4.12.1
#opam switch 4.12.1
#opam repo add coq-released https://coq.inria.fr/opam/released
#opam install coq

opam switch create debug_proj_4.09.1 4.09.1
opam switch debug_proj_4.09.1
opam repo add coq-released https://coq.inria.fr/opam/released
# install the right version of coq and pins it to it so that future opam installs don't change the coq version
opam pin add coq 8.11.0

# Don't think this is needed since the opam switch <switch> activated env? asked here as a comment: https://stackoverflow.com/questions/30155960/what-is-the-use-of-eval-opam-config-env-or-eval-opam-env-and-their-differen
# Run eval $(opam env --switch=debug_proj_4.09.1) to update the current shell environment
#eval $(opam env)
#eval $(opam env --switch=debug_proj_4.09.1)

# to display which switch you are on
opam switch list

# - install coq-serapi
opam install coq-serapi

# - install utop
opam install utop

# install docker, https://stackoverflow.com/questions/40523307/brew-install-docker-does-not-include-docker-engine
# brew install --cask docker

# - test pycoq
pytest --pyargs pycoq

