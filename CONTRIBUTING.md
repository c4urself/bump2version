# How to contribute

We'd love to accept your patches and contributions to this project. There are just a few small guidelines you need to follow.

## Guidelines
1. Write your patch
1. Add a test case to your patch
1. Make sure that `make test` runs properly
1. Send your patch as a PR

## Setup

1. Fork & clone the repo
1. Install [Docker](https://docs.docker.com/install/)
1. Install [docker-compose](https://docs.docker.com/compose/install/)
1. Run `make test` from the root directory


## How to release bumpversion itself

Execute the following commands:

    git checkout master
    git pull
    make test
    make lint
    bump2version release
    make dist
    make upload
    bump2version --no-tag patch
    git push origin master --tags
