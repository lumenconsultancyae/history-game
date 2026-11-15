# ChronoQuest (`history-game`)

**ChronoQuest** is an interactive historical timeline, chronological ordering challenge, era quiz, and branching historical decision-adventure game built with Clean/Hexagonal Architecture (`Python 3.12+`, `FastAPI`, `SQLAlchemy 2.0` + `Alembic` + `SQLite WAL`, and `React 19` + `TypeScript` + `Vite`).

## Architecture Overview

ChronoQuest strictly enforces inward-pointing Clean/Hexagonal layer boundaries under `src/history_game/`:

- **`domain/`**: Pure business entities (`Era`, `HistoricalEvent`, `ChallengeQuestion`, `GameSession`, `TurnSubmission`), value objects (`ScoreCard`, `Difficulty`, `GameMode`, `ChronologicalOrder`), domain events, typed domain exceptions, and repository ports (`ABC` interfaces). Imports zero outward layers or I/O libraries.
- **`application/`**: Use-case orchestration (`HistoryGameService`) coordinating gameplay lifecycles, chronological ordering verification, era trivia evaluation, streak bonuses, and leaderboard queries across domain ports.
- **`infrastructure/`**: SQLite WAL / SQLAlchemy 2.0 async persistence (`database.py`, `models.py`, `repositories.py`) and idempotent curated historical seed data (`seed_data.py`).
- **`api/`**: FastAPI `lifespan` entrypoint (`app.py`), modular `APIRouter` endpoints (`routes.py`), strict Pydantic v2 DTOs (`dto.py`), and centralized RFC 9457 `ProblemDetails` exception translation (`errors.py`).
- **`config/`**: Typed `Settings` leaf configuration via `pydantic-settings` (`settings.py`).
- **`utils/`**: Stateless formatting and year-label helpers (`formatting.py`).
- **`injection/`**: Explicit dependency injection composition root (`container.py`).
- **`frontend/`**: Interactive React + TypeScript + Vite web application featuring the Era Atlas explorer, Chronological Timeline Orderer, Trivia Challenge mode, and Hall of Records leaderboard.

## Quickstart

### Backend Setup & Migrations

```bash
pip install -e ".[dev]"
alembic upgrade head
uvicorn history_game.api.app:create_app --factory --reload --port 8000
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

## Testing & Verification

```bash
pytest -q
bash /root/.gemini/antigravity-cli/skills/.agents_architecture/scripts/check_architecture_gates.sh .
```

See the companion [`history-game-docs`](https://github.com/lumenconsultancyae/history-game-docs) repository for full Domain-Driven Design (DDD), Product Requirements (PRD), System Design (SDD), Architecture Decision Records (ADRs), `docker-compose.yml`, and Gherkin BDD acceptance suites.
