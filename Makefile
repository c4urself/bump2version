test:
	docker-compose build test
	docker-compose run test

lint:
	pip install pylint
	pylint bumpversion

debug_test:
	docker-compose build test
	docker-compose run test /bin/bash

clean:
	rm -rf dist build *.egg-info

dist:	clean
	python setup.py bdist_wheel

upload:
	twine upload dist/*

.PHONY: dist upload test debug_test
