lint:
	poetry run flake8 .

lint-fix:
	poetry run autopep8 .

test:
	poetry run pytest tests
