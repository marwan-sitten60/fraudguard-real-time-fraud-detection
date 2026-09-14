.PHONY: install dev test test-unit test-integration lint typecheck format up down logs benchmark
install:
	uv sync --locked
dev:
	uv run python -m fraudguard
test:
	uv run pytest
test-unit:
	uv run pytest tests/unit
test-integration:
	uv run pytest -m integration tests/integration
lint:
	uv run ruff check .
typecheck:
	uv run mypy
format:
	uv run ruff format .
up:
	docker compose up --build -d
down:
	docker compose down
logs:
	docker compose logs -f api
benchmark:
	k6 run tests/performance/scoring.js
