.PHONY: help up-dev-env fastapi-dev precommit-check sync-all test

DEV_SERVICES = db elasticsearch kibana init-data outbox-worker

help:
	@echo "Доступные команды:"
	@echo "	make up-dev-env				- Запустить dev окружение (Postgres, ES, Kibana, init-data)"
	@echo "	make down-dev-env			- Остановить dev окружение (Postgres, ES, Kibana, init-data)"
	@echo "	make fastapi-dev			- Запустить FastAPI в dev режиме"
	@echo "	make install-precommit			- Установить pre-commit хуки"
	@echo "	make precommit-check			- Запустить проверку pre-commit"
	@echo "	make sync-all				- Синхронизировать все uv пакеты"
	@echo "	make test				- Запустить тесты"

# Start development environment (Postgres, ES, Kibana, init-data)
up-dev-env:
	docker compose -f compose.yml up --build -d ${DEV_SERVICES}

# Stop development environment (Postgres, ES, Kibana, init-data)
down-dev-env:
	docker compose -f compose.yml down ${DEV_SERVICES}

# Run FastAPI in development mode
fastapi-dev:
	uv run fastapi dev

# Register pre-commit hooks
install-precommit:
	uv run prek install -f

# Run pre-commit checks
precommit-check:
	uv run prek run --all-files

# Sync all uv packages
sync-all:
	uv sync --all-packages

# Запуске тестов
test:
	uv run pytest --cov=app --cov-report=term-missing --cov-report=html
