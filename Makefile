SHELL := /bin/bash
COMPOSE := docker compose
DATABASE_URL ?= postgresql://silabus:silabus@localhost:5433/silabus
export DATABASE_URL

.PHONY: help up down logs migrate reset-db taxonomy-sync ingest eval api dash test lint fmt typecheck check

help: ## show targets
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-14s\033[0m %s\n", $$1, $$2}'

up: ## start Postgres and wait until healthy
	$(COMPOSE) up -d --wait

down: ## stop containers, keep the volume
	$(COMPOSE) down

logs: ## tail Postgres logs
	$(COMPOSE) logs -f db

migrate: ## apply pending db/migrations
	uv run silabus migrate

reset-db: ## DESTRUCTIVE: drop the volume, recreate, migrate
	$(COMPOSE) down -v
	$(MAKE) up
	$(MAKE) migrate

taxonomy-sync: ## sync skills.yaml into the skills table
	uv run silabus taxonomy-sync

ingest: ## ingest postings; SOURCE=fixtures|greenhouse|workable, BOARD=acme
	uv run silabus ingest --source $${SOURCE:-fixtures} $${BOARD:+--board $${BOARD}}

eval: ## score extraction; MODE=smoke (reports only) or full (gates)
	uv run silabus eval --mode $${MODE:-smoke}

api: ## run FastAPI with reload on :8000
	uv run uvicorn silabus.api.main:app --reload --port 8000

dash: ## run the Streamlit dashboard
	uv run streamlit run dashboards/streamlit/app.py

test: ## run the test suite
	uv run pytest

lint: ## ruff check + format check
	uv run ruff check .
	uv run ruff format --check .

fmt: ## auto-fix and format
	uv run ruff check --fix .
	uv run ruff format .

typecheck: ## mypy strict
	uv run mypy

check: lint typecheck test ## what CI runs
