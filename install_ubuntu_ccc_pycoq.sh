# for now just putting commands I'm running in terminal. Hope to evetually organize this better for compilation/install
# of python depedent tools + coq depedent tools.
# - install python: https://askubuntu.com/a/1412558/230288
sudo apt-get update
sudo apt-get install wget

# wget https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh -O ~/miniconda.sh
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh
bash ~/miniconda.sh -b -p $HOME/miniconda

# source /Users/my_username/opt/anaconda3/bin/activate
source ~/miniconda/bin/activate
# conda init zsh
conda init
conda update -n base -c defaults conda
conda install conda-build

conda create -n pycoq python=3.9
conda activate pycoq
#conda remove --name metalearning2 --all

# - install opam
# brew install opam # for mac
conda install -c conda-forge opam
opam init
# if doing local env? https://stackoverflow.com/questions/72522412/what-does-eval-opam-env-do-does-it-activate-a-opam-environment
eval $(opam env)

# - install coq: see https://stackoverflow.com/questions/71117837/how-does-one-install-a-new-version-of-coq-when-it-cannot-find-the-repositories-i
opam switch create debug_proj_4.09.1 4.09.1
opam switch debug_proj_4.09.1
opam repo add coq-released https://coq.inria.fr/opam/released
# install the right version of coq and pins it to it so that future opam installs don't change the coq version
opam pin add coq 8.11.0

opam switch list

# - install coq-serapi
opam install coq-serapi

# - install utop
opam install utop

# - python installs
pip install -e ~/pycoq
pip install -e ~/ultimate-utils/

# - test pycoq
pytest --pyargs pycoq

