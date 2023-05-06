lint:
	poetry run flake8 .

lint-fix:
	poetry run autopep8 --in-place --recursive --ignore E127 .

test:
	poetry run pytest tests
