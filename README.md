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

# 5. run the checks
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

`uv run <cmd>` executes inside the project venv, so activating it is optional.

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
