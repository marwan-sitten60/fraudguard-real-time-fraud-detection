FROM python:3.12.13-slim-bookworm AS builder
WORKDIR /build
COPY requirements.lock requirements-build.lock ./
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --retries 3 --timeout 120 --require-hashes -r requirements.lock
RUN python -m venv /opt/build \
    && /opt/build/bin/pip install --no-cache-dir --retries 3 --timeout 120 --require-hashes -r requirements-build.lock
COPY pyproject.toml README.md ./
COPY src ./src
RUN /opt/build/bin/python -m hatchling build -t wheel \
    && /opt/venv/bin/pip install --no-deps dist/*.whl

FROM python:3.12.13-slim-bookworm AS runtime
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 APP_HOST=0.0.0.0
RUN groupadd --gid 10001 fraudguard && useradd --uid 10001 --gid fraudguard --create-home fraudguard
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY alembic.ini ./
COPY infrastructure/database ./infrastructure/database
USER fraudguard
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('APP_PORT','8000')+'/health',timeout=2)"
CMD ["python", "-m", "fraudguard"]
