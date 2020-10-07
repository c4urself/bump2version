test:
	docker-compose build test
	docker-compose run test

local_test:
	PYTHONPATH=. pytest tests/

lint:
	pip install pylint
	pylint bumpversion

debug_test:
	docker-compose build test
	docker-compose run test /bin/bash

clean:
	rm -rf dist build *.egg-info

dist:	clean
	python3 setup.py sdist bdist_wheel

upload:
	twine upload dist/*

.PHONY: dist upload test debug_test
