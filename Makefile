# Racing Line Optimizer — comandos principais
# Uso: make <alvo>   (ex.: make dev)

PY = .venv/Scripts/python

.PHONY: help install db-up db-down seed run dev test clean

help: ## Lista os alvos disponíveis
	@echo Alvos disponiveis:
	@echo   make install   - cria o venv e instala as dependencias
	@echo   make db-up     - sobe o Postgres (Docker) e espera ficar saudavel
	@echo   make db-down   - derruba o Postgres
	@echo   make seed      - cria tabelas, aplica migracoes e popula dados iniciais
	@echo   make run       - inicia o servidor em http://localhost:8000
	@echo   make dev       - db-up + seed + run (setup completo para testar a interface)
	@echo   make test      - roda a suite de testes
	@echo   make clean     - remove o venv e caches

install: ## Cria o venv e instala dependências
	python -m venv .venv
	$(PY) -m pip install -e ".[dev]"

db-up: ## Sobe o Postgres via Docker Compose
	docker compose up -d --wait

db-down: ## Derruba o Postgres
	docker compose down

seed: ## Tabelas + migrações + dados iniciais (idempotente)
	$(PY) -m app.seed

run: ## Servidor FastAPI + UI em http://localhost:8000
	$(PY) -m uvicorn app.main:app --port 8000

dev: db-up seed run ## Sobe tudo para testar via interface

test: ## Suite de testes do engine
	$(PY) -m pytest -q

# Alvo pensado para o cmd.exe (shell padrão do make no Windows).
clean: ## Remove venv e caches
	@if exist .venv rmdir /s /q .venv
	@if exist .pytest_cache rmdir /s /q .pytest_cache
	@for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
