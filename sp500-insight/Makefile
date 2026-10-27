.PHONY: up down logs migrate seed-universe etl-daily etl-backfill frontend backend shell-db clean status

# Start core services
up:
	docker compose up -d db prefect backend
	@echo ""
	@echo "Services starting..."
	@echo "  - PostgreSQL + TimescaleDB : localhost:5432"
	@echo "  - Prefect UI               : http://localhost:4200"
	@echo "  - FastAPI docs             : http://localhost:8000/docs"
	@echo ""
	@echo "Wait ~10-15 seconds for the database to be ready, then run:"
	@echo "  make migrate"
	@echo "  make seed-universe"

down:
	docker compose down

logs:
	docker compose logs -f

status:
	docker compose ps

# Database
migrate:
	docker compose exec backend alembic upgrade head
	@echo "Migrations applied."

seed-universe:
	docker compose exec backend python -m app.scripts.seed_universe

# ETL (run from host with local Python env or inside a worker container)
etl-daily:
	cd etl && python -m flows.daily_pipeline

etl-backfill:
	cd etl && python -m flows.backfill

# Frontend (run on host)
frontend:
	cd frontend && npm install && npm run dev

# Backend shell
backend:
	docker compose exec backend bash

shell-db:
	docker compose exec db psql -U sp500 -d sp500_insight

# Cleanup
clean:
	docker compose down -v
	@echo "Volumes removed. Data is gone."
