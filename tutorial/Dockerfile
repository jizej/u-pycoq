FROM ubuntu:20.04

MAINTAINER Brando Miranda "brandojazz@gmail.com"

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    ssh \
    git \
    m4 \
    libgmp-dev \
    opam \
    wget \
    ca-certificates \
    rsync \
    strace

RUN useradd -m bot
WORKDIR /home/bot
USER bot

RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
  && bash Miniconda3-latest-Linux-x86_64.sh -b -f
ENV PATH="/home/bot/miniconda3/bin:${PATH}"
RUN conda create -n pycoq python=3.9 -y
# somehow this "works" but conda isn't fully aware of this. Fix later?
ENV PATH="/home/bot/miniconda3/envs/pycoq/bin:${PATH}"

ADD https://api.github.com/repos/IBM/pycoq/git/refs/heads/main version.json

# TODO: doesn't seem to work...try later perhaps: https://stackoverflow.com/questions/55123637/activate-conda-environment-in-docker
# TODO: if you run VP's image and attack a volume that seems enough for now.
# RUN conda init bash
# RUN echo "conda activate pycoq" > ~/.bashrc
# RUN conda activate pycoq
#RUN conda update -n base -c defaults conda
#RUN conda install conda-build

# - setp up opam
#RUN conda install -c conda-forge opam
# https://stackoverflow.com/questions/72649679/how-to-use-apt-get-install-in-docker-when-there-is-a-could-not-open-lock-file-v
# USER root
# RUN apt-get update && apt-get install -y --no-install-recommends bubblewrap
# RUN opam init
RUN opam init --disable-sandboxing
RUN opam switch create debug_proj_4.09.1 4.09.1
RUN opam switch debug_proj_4.09.1
RUN eval $(opam env)
RUN opam repo add coq-released https://coq.inria.fr/opam/released
RUN opam pin add coq 8.11.0

# - install coq-serapi
RUN opam install coq-serapi

# Don't think it should work since dockerfiles are not suppose to be editable. Need to run this every time you log?
# makes sure depedencies are installed once already in the docker image
RUN pip install pycoq
# then make sure editable mode is done to be able to use changing pycoq from system
RUN echo "pip install -e /home/bot/pycoq" >> ~/.bashrc
# RUN echo "LIGHT_GREY='\e[0;37m'" >> ~/.bashrc
# RUN echo "LIGHT_BLUE='\e[1;34m'" >> ~/.bashrc
# RUN echo "export PS1='\[$LIGHT_BLUE\][\u@\h \W]\$\[$LIGHT_GREY\] '" >> ~/.bashrc
# RUN echo "eval $(opam env)" >> ~/.bashrc
# - set env variable for bash terminal prompt p1 to be nicely colored
ENV force_color_prompt=yes

# RUN pytest --pyargs pycoq
