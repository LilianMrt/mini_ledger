# Mini Ledger

A small asynchronous double-entry bookkeeping API built with FastAPI and Postgres. Every transaction is recorded as a set of balanced debit/credit entries, written atomically with idempotency-key support to make retries safe.

🚀 **Live Demo:** [`https://miniledger.lilianmrt.duckdns.org/docs`](https://miniledger.lilianmrt.duckdns.org/docs) (Interactive Swagger UI hosted on a self-managed, secure VPS)

### Key Architectural Showcases
1. **Strict Data Correctness:** Double-entry ledger architecture (Debits/Credits balance to 0).
2. **Idempotent Design:** Middleware to capture, cache, and safely replay API requests via unique `Idempotency-Key` headers.
3. **Async Performance:** Built with FastAPI and `asyncpg` to unlock completely non-blocking database pools.

[![Deploy](https://github.com/LilianMrt/mini_ledger/actions/workflows/deploy.yaml/badge.svg)](https://github.com/LilianMrt/mini_ledger/actions/workflows/deploy.yaml)
![Python](https://img.shields.io/badge/python-3-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791)

## Why this project

This is a small, focused showcase of backend fundamentals that matter for financial systems: enforcing invariants at the write boundary (entries must balance to zero, atomically, before anything touches the database), making writes safe to retry with idempotency keys, and keeping money as `Decimal`/`NUMERIC` rather than floats The API is deployed and kept live through its own CI/CD pipeline (GitHub Actions → VPS, `nginx` + `certbot` in front), so the link above reflects the actual running system.

## Tech stack

- **FastAPI** + **Pydantic** — async HTTP API and request/response validation
- **PostgreSQL** — durable storage for accounts, transactions, and entries
- **asyncpg** — direct async driver (no ORM), with a shared connection pool
- **Docker Compose** — reproducible local environment (API + Postgres)

## Key design points

- **Double-entry invariant**: a transaction must have at least 2 entries, and their amounts must sum to exactly zero. This is validated in the API before anything is written.
- **Idempotency**: every write requires an `Idempotency-Key` header. Keys and their responses are stored in Postgres, so retried requests replay the original response instead of creating a duplicate transaction.
- **Atomicity**: the idempotency record and the ledger write happen inside a single database transaction — if the ledger write fails, the idempotency key is rolled back too.
- **Precision**: monetary amounts use `Decimal` and Postgres `NUMERIC(12,4)`, never floats.

## Project structure

```
app/
├── main.py                    # FastAPI app + lifespan (DB pool startup)
├── database.py                # asyncpg connection pool
├── dependencies/
│   └── idempotency.py         # Idempotency-Key validation/replay
└── routes/
    └── transactions.py        # POST /transactions endpoint
initialization/
├── 01_schema.sql              # Tables + indexes (safe to re-run in production)
├── 02_mock_seed.sql           # Dev-only sample accounts
└── init_db.py                 # Applies schema.sql, and mock_seed.sql with --with-mock
tests/
├── conftest.py                 # Testcontainers Postgres fixture + httpx client
├── test_health.py
└── test_transactions.py        # Balance invariant, idempotency, atomicity, precision
```

## Running locally

Requirements: Docker, Python 3, a `.venv` in the parent directory.

```bash
cp .env.example .env
./init.sh
```

This starts Postgres and the API via Docker Compose, waits for the database to be ready, and applies the schema.

The API is then available at `http://localhost:5000`.

## Running tests

Integration tests exercise the FastAPI app against a real, ephemeral Postgres instance (via [Testcontainers](https://testcontainers.com/)) — no need to run `./init.sh` first, just Docker running locally:

```bash
pip install -r requirements-dev.txt
pytest -v
```

Tests cover the double-entry balance invariant, idempotency-key replay, and that a failed write rolls back its idempotency record — not just HTTP status codes, but actual Postgres state after each request.

## Deploying to production

`.github/workflows/deploy.yaml` runs on every push/PR to `main`: a `test` job runs the suite above, and a `deploy` job — gated on `needs: test`, and skipped on pull requests — rsyncs the repo to the VPS over SSH, writes `.env` from GitHub secrets, runs `docker compose up -d --build --wait`, and applies `01_schema.sql` via `init_db.py`. A failing test suite blocks deployment.

Production topology: `nginx` + `certbot` on the VPS host terminate TLS and reverse-proxy to the `api` container, which — like `postgres` — is bound to `127.0.0.1` only and never exposed directly to the internet.

One-time VPS setup:
- A dedicated `deploy` user, in the `docker` group only, with `/opt/mini_ledger` as the deploy path.
- An SSH keypair generated locally for GitHub Actions to use, with its public half installed for `deploy`.
- The VPS's SSH host key captured with `ssh-keyscan` so the workflow can verify the server's identity.

Required GitHub secrets (repo/environment `production`):

| Secret | Purpose |
|---|---|
| `VPS_HOST` | VPS IP or domain |
| `VPS_USER` | `deploy` |
| `VPS_SSH_PORT` | SSH custom port|
| `VPS_SSH_KEY` | Private half of the GitHub Actions deploy keypair |
| `VPS_HOST_KEY` | Output of `ssh-keyscan` against the VPS, for host verification |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD` | Production DB credentials |

## Example request

```bash
curl -X POST http://localhost:5000/transactions \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: 3f1b2c4a-0000-0000-0000-000000000001" \
  -d '{
    "description": "Revolut payment",
    "entries": [
      { "account_id": "a0000000-0000-0000-0000-000000000001", "amount": "64.0000" },
      { "account_id": "b0000000-0000-0000-0000-000000000002", "amount": "-64.0000" }
    ]
  }'
```
