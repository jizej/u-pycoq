# 

To build the docker image that is interactable from the Dockerfile using the tag flag '-t' do:
```bash
docker build -t brandojazz/pycoq:test_brando ~/pycoq/tutorial/
```
Optionally push it to your dockerhub:
```bash
docker login
docker push brandojazz/pycoq:test_brando
```
confirm it's in your system:
```bash
docker images
```
something like this should show:
```bash
REPOSITORY         TAG           IMAGE ID       CREATED              SIZE
brandojazz/pycoq   test_brando   64e3ccc0bf3f   About a minute ago   1.33GB
```
Then run the docker image voluming your local pycoq repo to the one in the docker image.
Note the docker image pip install pycoq (so all the depedencies should be there and be prebuilt to be quicker)
and it also create a `.bashrc` file with `pip install -e /home/bot/pycoq` so when you login to your docker container 
your docker pycoq repo should be linked to your local one in defelopment mode.
```bash
docker run -v /Users/brandomiranda/pycoq:/home/bot/pycoq -ti brandojazz/pycoq:test_brando bash
```
note `/home/bot` is the home directory for bot.