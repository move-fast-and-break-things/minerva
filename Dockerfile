FROM python:3.12

RUN pip install poetry==2.2.1

COPY poetry.lock pyproject.toml ./
RUN poetry install --no-root
RUN poetry run playwright install --with-deps chromium

COPY . .

RUN poetry install --only-root

CMD ["poetry", "run", "minerva"]
