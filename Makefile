
test:
	docker-compose build test
	docker-compose run test

debug_test:
	docker-compose build test
	docker-compose run test /bin/bash
