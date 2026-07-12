.PHONY: install run test lint format typecheck docker-up docker-down reset

install:
	pip install -r requirements.txt

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest

lint:
	ruff check .

format:
	black .
	ruff check . --fix

typecheck:
	mypy app scripts

docker-up:
	docker compose up --build

docker-down:
	docker compose down

reset:
	python scripts/reset_storage.py

