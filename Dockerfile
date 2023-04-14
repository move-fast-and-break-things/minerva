FROM python:3.11

RUN pip install poetry

COPY poetry.lock pyproject.toml ./
RUN poetry install

COPY . .

CMD ["poetry", "run", "minerva"]
