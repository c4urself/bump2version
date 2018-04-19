FROM themattrix/tox-base

RUN apt-get update && apt-get install -y git-core mercurial

# install a newer version op pypy and pypy3 that doesn't have troubles
RUN pyenv install pypy-5.6.0
RUN pyenv install pypy3.3-5.5-alpha

# only install certain versions for tox to use
RUN pyenv global system 2.7.13 3.4.5 3.5.2 3.6.0 pypy-5.6.0 pypy3.3-5.5-alpha

RUN git config --global user.email "bumpversion_test@example.org"
RUN git config --global user.name "Bumpversion Test"

ENV PYTHONDONTWRITEBYTECODE = 1  # prevent *.pyc files

WORKDIR /code
COPY . .
CMD tox
