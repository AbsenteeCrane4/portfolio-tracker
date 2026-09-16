# portfolio-tracker

Self-hosted portfolio tracker modelled on Sharesight, extended with a pluggable
market-analysis layer. Single-user, UK tax rules, free-tier price data.

See [CLAUDE.md](CLAUDE.md) for the architecture and the rules this codebase enforces,
and [USER_STORIES.md](USER_STORIES.md) for the backlog.

## Local setup

Requires [uv](https://docs.astral.sh/uv/) — everything else is installed by it.

```sh
# 1. install uv (macOS/Linux; see uv docs for Windows)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. clone and enter
git clone https://github.com/AbsenteeCrane4/portfolio-tracker.git
cd portfolio-tracker

# 3. create the venv and install everything, including dev tools
uv sync

# 4. configure — every key is documented in the example, secrets stay out of git
cp .env.example .env

# 5. start a local Postgres (dev database `portfolio`, test database `portfolio_test`)
docker compose up -d

# 6. apply migrations
uv run alembic upgrade head

# 7. run the checks
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

`uv run <cmd>` executes inside the project venv, so activating it is optional.

The local Postgres URL is `postgresql+asyncpg://portfolio:portfolio@localhost:5432/portfolio`;
put that in `.env` as `DATABASE_URL` to develop against it instead of Supabase.

## Database

SQLAlchemy 2.0 async over asyncpg, with Alembic for migrations. `src/portfolio/core/db.py`
holds the declarative `Base` (naming convention for constraints, `Decimal` → `NUMERIC`,
`datetime` → `TIMESTAMPTZ`) and the `Money` / `Quantity` column annotations every
model should use for amounts and unit counts.

Every schema change ships with a migration in the same commit:

```sh
uv run alembic revision --autogenerate -m "add instruments table"
uv run alembic upgrade head
uv run alembic downgrade -1
```

`migrations/env.py` reads `DATABASE_URL` from the application settings; `alembic.ini`
holds no URL. New revision files are run through ruff automatically.

### Database-backed tests

Tests that need Postgres take the `db_session` fixture (a session inside a transaction
that is rolled back after each test) and read `TEST_DATABASE_URL`. Without it they
skip; CI always sets it. Locally, with the compose stack running:

```sh
TEST_DATABASE_URL=postgresql+asyncpg://portfolio:portfolio@localhost:5432/portfolio_test uv run pytest
```

## Layout

```
src/portfolio/
  core/         stable domain logic — never imports from features/
  interfaces/   Protocols only, no implementations
  features/     providers, importers, reports, roundup
  api/          FastAPI routers, thin
tests/
```

The boundary rules are enforced by `tests/test_layout.py`, not just by review.

## Before you commit

`ruff check`, `ruff format --check`, `mypy`, and `pytest` must all pass. CI runs the
same four commands on every push and pull request.
