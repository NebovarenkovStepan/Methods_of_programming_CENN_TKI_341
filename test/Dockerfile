# syntax=docker/dockerfile:1.7

FROM python:3.12-slim

WORKDIR /app

COPY requirements-test.txt /app/test/requirements-test.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r /app/test/requirements-test.txt

RUN groupadd --system app \
    && useradd --system --gid app --home /app app \
    && chown -R app:app /app

COPY --chown=app:app . /app/test/

USER app

CMD ["python", "-m", "pytest", "/app/test/test_system_scenarios.py", "-v", "--tb=short"]