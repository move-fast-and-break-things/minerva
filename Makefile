lint:
	poetry run ruff check

lint-fix:
	poetry run ruff format

test:
	poetry run pytest .

type-check:
	poetry run pyright .
