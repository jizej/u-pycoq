#!/usr/bin/env bash

# - CAREFUL, if a job is already running it could do damage to it, rm reauth process, qian doesn't do it so skip it
# top -u brando9
#
# pkill -9 tmux -u brando9; pkill -9 krbtmux -u brando9; pkill -9 reauth -u brando9; pkill -9 python -u brando9; pkill -9 wandb-service* -u brando9;
#
# pkill -9 python -u brando9; pkill -9 wandb-service* -u brando9;
#
# krbtmux
# reauth
# nvidia-smi
# sh ~/.bashrc.user
# sh main_krbtmux.sh
#
# tmux attach -t 0

# ssh brando9@hyperturing1.stanford.edu
# ssh brando9@hyperturing2.stanford.edu
# ssh brando9@turing1.stanford.edu

# - install conda
echo $HOME
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh
bash ~/miniconda.sh -b -p $HOME/miniconda
ls -lah ~

export PATH="$HOME/miniconda/bin:$PATH"
echo $PATH
conda

source ~/miniconda/bin/activate
conda init
conda init bash
conda update -n base -c defaults conda
conda install conda-build

conda create -n metalearning_gpu python=3.9
conda activate metalearning_gpu
conda create -n iit_synthesis python=3.9
conda activate iit_synthesis
conda list

conda create -n iit_synthesis python=3.9
conda activate iit_synthesis

# - install rbenv for installing ruby
mkdir ~/.rbenv
cd ~/.rbenv
git clone https://github.com/rbenv/rbenv.git .

export PATH="$HOME/.rbenv/bin:$PATH"
eval "$(rbenv init -)"
echo 'export PATH="$HOME/.rbenv/bin:$PATH"' >> ~/.bashrc.user
echo 'eval "$(rbenv init -)"' >> ~/.bashrc.user
exec $SHELL
bash
source ~/.bashrc.user

rbenv -v

# - install ruby-build
mkdir ~/.ruby-build
cd ~/.ruby-build
git clone https://github.com/rbenv/ruby-build.git .

export PATH="$HOME/.ruby-build/bin:$PATH"
echo 'export PATH="$HOME/.ruby-build/bin:$PATH"' >> ~/.bashrc.user
exec $SHELL
bash
source ~/.bashrc.user

ruby-build --version

# - install ruby without sudo -- now that ruby build was install
mkdir -p ~/.local
#    ruby-build 3.1.2 ~/.local/
rbenv install 3.1.2
rbenv global 3.1.2

ruby -v
which ruby

## - opam official install ref: https://opam.ocaml.org/doc/Install.html
mkdir -p ~/.local/bin
bash -c "sh <(curl -fsSL https://raw.githubusercontent.com/ocaml/opam/master/shell/install.sh)"
## type manually
~/.local/bin
## note since if it detects it in /usr/bin/opam it fails since then it tries to move opam from /usr/bin/opam to local

# -- setup opam like the original pycoq
opam init --disable-sandboxing
eval $(opam env --switch=default)
opam update --all
eval $(opam env)
# compiler + '_' + coq_serapi + '.' + coq_serapi_pin
# ref: https://stackoverflow.com/questions/74697011/how-does-one-install-a-specific-ocaml-compiler-when-it-doesnt-appear-on-the-opa
opam switch create ocaml-variants.4.07.1+flambda_coq-serapi.8.11.0+0.11.1 ocaml-variants.4.07.1+flambda
opam switch ocaml-variants.4.07.1+flambda_coq-serapi.8.11.0+0.11.1
eval $(opam env)

opam repo add coq-released https://coq.inria.fr/opam/released
# opam pin add -y coq 8.11.0
opam repo --all-switches add --set-default coq-released https://coq.inria.fr/opam/released
opam update --all
opam pin add -y coq 8.11.0

#opam install -y --switch ocaml-variants.4.07.1+flambda_coq-serapi_coq-serapi_8.11.0+0.11.1 coq-serapi 8.11.0+0.11.1
opam install -y coq-serapi

eval $(opam env)

# - install utop
opam install utop

# - make dara dir
mkdir ~/data/

# - get git projs
git clone git@github.com:FormalML/iit-term-synthesis.git
git clone git@github.com:brando90/ultimate-utils.git
git clone git@github.com:brando90/pycoq.git
#git clone git@github.com:brando90/proverbot9001.git

# - pytorch with gpu install
# pip3 install torch==1.9.1+cu111 torchvision==0.10.1+cu111 torchaudio==0.9.1 -f https://download.pytorch.org/whl/torch_stable.html
#pip install torch==1.9.1+cu111 torchvision==0.10.1+cu111 torchaudio==0.9.1 -f https://download.pytorch.org/whl/torch_stable.html
pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu113
pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu113 --upgrade

# - editable installs
pip uninstall iit-term-synthesis
pip uninstall ultimate-utils
pip uninstall pycoq
pip install -e ~/iit-term-synthesis
pip install -e ~/ultimate-utils
pip install -e ~/pycoq
#pip install -e ~/proverbot9001

# - check installs
python -c "import torch; print(torch.__version__)"
python -c "import uutils; uutils.hello()"
python -c "import uutils; uutils.torch_uu.gpu_test_torch_any_device()"

# in case pip -e gives issues...ignore for now, https://stackoverflow.com/questions/59903548/how-does-one-check-if-conda-develop-installed-my-project-packages
#python -c "import sys; [print(p) for p in sys.path]"
#conda develop ~/ultimate-utils
#conda develop ~/pycoq
#conda develop ~/iit-term-synthesis
## conda develop -u .

## - gpu installs (seem not needed?)
nvidia-smi
echo $CUDA_VISIBLE_DEVICES

# - wandb
echo "----> Contact Brando to get his wandb stuff"
#echo "going to append something to your .bashrc: export WANDB_API_KEY=SECRET"
#RUN echo "export WANDB_API_KEY=" >> ~/.bashrc
WANDB_API_KEY="SECRET"
pip install wandb
pip install wandb --upgrade

wandb login
wandb login --relogin

cat ~/.netrc