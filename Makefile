lint:
	poetry run pycodestyle .

lint-fix:
	poetry run autopep8 --in-place --recursive .

test:
	poetry run pytest tests
