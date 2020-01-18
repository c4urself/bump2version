FROM themattrix/tox-base

RUN apt-get update && apt-get install -y git-core mercurial

# Update pyenv for access to newer Python releases.
RUN cd /.pyenv \
    && git fetch \
    && git checkout v1.2.15

# only install certain versions for tox to use
RUN pyenv versions
RUN pyenv global system 3.5.7 3.6.9 3.7.5 3.8.0 pypy3.6-7.2.0

RUN git config --global user.email "bumpversion_test@example.org"
RUN git config --global user.name "Bumpversion Test"

ENV PYTHONDONTWRITEBYTECODE = 1  # prevent *.pyc files

WORKDIR /code
COPY . .
CMD tox
