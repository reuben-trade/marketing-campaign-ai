.PHONY: help install dev run test lint format migrate docker-up docker-down celery-worker celery-beat

# Default target
help:
	@echo "Marketing AI - Available Commands:"
	@echo ""
	@echo "  install       Install dependencies with Poetry"
	@echo "  dev           Run the development server (PORT=8000 by default)"
	@echo "  dev-alt       Run development server on alternate port (8001)"
	@echo "  dev-alt2      Run development server on second alternate port (8002)"
	@echo "  run           Run the production server"
	@echo "  test          Run tests with pytest"
	@echo "  lint          Run linting with ruff"
	@echo "  format        Format code with ruff"
	@echo "  migrate       Run database migrations"
	@echo "  migrate-new   Create a new migration (usage: make migrate-new MSG='description')"
	@echo "  docker-up     Start Docker services (Redis)"
	@echo "  docker-down   Stop Docker services"
	@echo "  celery-worker Start Celery worker"
	@echo "  celery-beat   Start Celery beat scheduler"
	@echo "  celery-flower Start Celery Flower monitoring"
	@echo ""

# Install dependencies
install:
	poetry install

# Run development server
dev:
	poetry run uvicorn app.main:app --reload --host $${HOST:-0.0.0.0} --port $${PORT:-8000}

# Run production server
run:
	poetry run uvicorn app.main:app --host $${HOST:-0.0.0.0} --port $${PORT:-8000}

# Run second instance on port 8001
dev-alt:
	PORT=8001 poetry run uvicorn app.main:app --reload --host $${HOST:-0.0.0.0} --port 8001

# Run third instance on port 8002
dev-alt2:
	PORT=8002 poetry run uvicorn app.main:app --reload --host $${HOST:-0.0.0.0} --port 8002

# Run tests
test:
	poetry run pytest tests/ -v

# Run tests with coverage
test-cov:
	poetry run pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing

# Run linting
lint:
	poetry run ruff check app/ tests/

# Format code
format:
	poetry run ruff format app/ tests/
	poetry run ruff check --fix app/ tests/

# Run database migrations
migrate:
	poetry run alembic upgrade head

# Create new migration
migrate-new:
	poetry run alembic revision --autogenerate -m "$(MSG)"

# Show migration history
migrate-history:
	poetry run alembic history

# Rollback last migration
migrate-rollback:
	poetry run alembic downgrade -1

# Start Docker services
docker-up:
	docker-compose up -d redis

# Stop Docker services
docker-down:
	docker-compose down

# Start Celery worker
celery-worker:
	poetry run celery -A app.tasks.celery_app worker --loglevel=info --queues=default,discovery,retrieval,analysis

# Start Celery beat scheduler
celery-beat:
	poetry run celery -A app.tasks.celery_app beat --loglevel=info

# Start Celery Flower monitoring
celery-flower:
	poetry run celery -A app.tasks.celery_app flower --port=5555

# Start all services for development
dev-all:
	docker-compose up -d redis
	@echo "Redis started. Run 'make dev', 'make celery-worker', and 'make celery-beat' in separate terminals."

# Clean up
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete

# Shell
shell:
	poetry run python -c "from app.database import *; from app.models import *; import asyncio"

# Generate OpenAPI schema
openapi:
	poetry run python -c "from app.main import app; import json; print(json.dumps(app.openapi(), indent=2))" > openapi.json
