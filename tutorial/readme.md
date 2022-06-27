# Running pycoq for development in an interactive docker container

## Quick: pull the image from Brando's docker hub

For a dev using a pre-built image do:
```bash
docker pull brandojazz/pycoq:test_brando
```

Now you can do the `docker run -v ...` command mentioned bellow.

## Building image from scratch

To build the docker image that is interactable from the Dockerfile using the tag flag '-t' do:
```bash
docker build -t brandojazz/pycoq:test_brando ~/pycoq/tutorial/
docker build -t brandojazz/pycoq:test_brando_vp ~/pycoq/tutorial/

docker build -t brandojazz/pycoq:test ~/pycoq/
```
Optionally push it to your dockerhub:
```bash
docker login
docker push brandojazz/pycoq:test_brando
docker push brandojazz/pycoq:test_brando_vp

docker push brandojazz/pycoq:test
```
confirm it's in your system:
```bash
docker images
```
something like this should show:
```bash
REPOSITORY         TAG              IMAGE ID       CREATED          SIZE
brandojazz/pycoq   test_brando_vp   0c6ab0abe75f   47 seconds ago   5.03GB
brandojazz/pycoq   test_brando      e73bd9084e77   5 hours ago      4.28GB
```
Then run the docker image voluming your local pycoq repo to the one in the docker image.
Note the docker image pip install pycoq (so all the depedencies should be there and be prebuilt to be quicker)
and it also create a `.bashrc` file with `pip install -e /home/bot/pycoq` so when you login to your docker container 
your docker pycoq repo should be linked to your local one in defelopment mode.
```bash
docker run -v /Users/brandomiranda/pycoq:/home/bot/pycoq -ti brandojazz/pycoq:test_brando bash
docker run -v /Users/brandomiranda/pycoq:/home/bot/pycoq -ti brandojazz/pycoq:test_brando_vp bash

docker run -v /Users/brandomiranda/pycoq:/home/bot/pycoq -ti brandojazz/pycoq:test bash
```
note `/home/bot` is the home directory for bot.
```bash
docker run -v /Users/brandomiranda/pycoq:/home/bot/pycoq \
           -v /Users/brandomiranda/ultimate-utils:/home/bot/ultimate-utils \
           -ti brandojazz/iit-term-synthesis:test bash
```

```bash
python ~/pycoq/tutorial/brandos_pycoq_tutorial.py
```

To run from Vasily's original docker container do:
```bash
docker run -v /Users/brandomiranda/pycoq:/home/bot/pycoq -ti brandojazz/pycoq:test bash
```

To run Vasily's original pytests do:
```bash
pytest --pyargs pycoq
```