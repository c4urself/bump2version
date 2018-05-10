FROM themattrix/tox-base

RUN apt-get update && apt-get install -y git-core mercurial

# Update pyenv for access to newer Python releases.
RUN cd /.pyenv \
    && git fetch \
    && git checkout v1.2.3

ENV PYPY_VERSION=pypy2.7-5.10.0 \
    PYPY3_VERSION=pypy3.5-5.10.1

# install a newer version op pypy and pypy3 that doesn't have troubles
RUN pyenv install "$PYPY_VERSION"
RUN pyenv install "$PYPY3_VERSION"

# only install certain versions for tox to use
RUN pyenv global system 2.7.13 3.4.5 3.5.2 3.6.0 "$PYPY_VERSION" "$PYPY3_VERSION"

RUN git config --global user.email "bumpversion_test@example.org"
RUN git config --global user.name "Bumpversion Test"

ENV PYTHONDONTWRITEBYTECODE = 1  # prevent *.pyc files

WORKDIR /code
COPY . .
CMD tox
