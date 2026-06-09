# syntax=docker/dockerfile:1
# Build from repo root: docker compose build harness-backend

FROM cgr.dev/chainguard/python:latest-dev AS builder

WORKDIR /app

ENV VIRTUAL_ENV=/app/venv
RUN python -m venv "${VIRTUAL_ENV}"
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

COPY backend/pyproject.toml .
COPY backend/app ./app
COPY backend/tests ./tests
RUN pip install --no-cache-dir ".[dev]"

FROM cgr.dev/chainguard/python:latest

WORKDIR /app

ENV VIRTUAL_ENV=/app/venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"
ENV PYTHONUNBUFFERED=1

COPY --from=builder /app/venv /app/venv
COPY backend/ .
COPY reference/ /app/reference-baked/

EXPOSE 5998

ENTRYPOINT ["python", "/app/docker_entrypoint.py"]
CMD ["-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5998"]
