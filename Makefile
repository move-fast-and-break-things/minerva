lint:
	poetry run ruff check

lint-fix:
	poetry run ruff format

test:
	poetry run pytest tests
