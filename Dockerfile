# Dockerfile
FROM python:3.11-slim as python-base

# Configuraciones de Python y Poetry
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION=1.6.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    PYSETUP_PATH="/opt/pysetup" \
    VENV_PATH="/opt/pysetup/.venv"

ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"

# Etapa de construcción
FROM python-base as builder-base
RUN apt-get update && apt-get install --no-install-recommends -y curl build-essential

# Instalar Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Instalar dependencias
WORKDIR $PYSETUP_PATH
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main

# Etapa final de ejecución
FROM python-base as development
WORKDIR /app
COPY --from=builder-base $PYSETUP_PATH $PYSETUP_PATH
COPY . .

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]