FROM python:3.12-slim

RUN pip install poetry

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV POETRY_VERSION=1.8.3 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR='/var/cache/pypoetry' \
    POETRY_HOME='/usr/local' \
    PYTHONPATH='/app'

WORKDIR /app

COPY ./pyproject.toml ./poetry.lock /app/

RUN poetry config virtualenvs.create false \
    && poetry install --no-root

COPY ./src ./src
