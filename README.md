uv run black . - format
docker compose up -d postgres redis - start postgres redis
uv run alembic revision --autogenerate -m "migration name" generate migration file
uv run alembic upgrade head - create migration
