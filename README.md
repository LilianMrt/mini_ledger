# Mini Ledger

A small double-entry bookkeeping API built with FastAPI and Postgres. Every transaction is recorded as a set of balanced debit/credit entries, written atomically with idempotency-key support to make retries safe.

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
├── 01_init.sql                # Schema + seed accounts
└── init_db.py                 # Applies the schema to Postgres
```

## Running locally

Requirements: Docker, Python 3, a `.venv` in the parent directory.

```bash
cp .env.example .env
./init.sh
```

This starts Postgres and the API via Docker Compose, waits for the database to be ready, and applies the schema.

The API is then available at `http://localhost:5000`.

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
