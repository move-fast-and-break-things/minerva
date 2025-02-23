FROM python:3.12

RUN pip install poetry==2.1.1

COPY poetry.lock pyproject.toml ./
RUN poetry install --no-root

COPY . .

RUN poetry install --only-root

CMD ["poetry", "run", "minerva"]
