import uuid

import pytest

REVENUE_ACCOUNT = "a0000000-0000-0000-0000-000000000001"
ASSET_ACCOUNT = "b0000000-0000-0000-0000-000000000002"
CLIENT_ACCOUNT = "c0000000-0000-0000-0000-000000000003"
NONEXISTENT_ACCOUNT = "ffffffff-0000-0000-0000-000000000099"


def new_key():
    return str(uuid.uuid4())


async def post_transaction(client, payload, key=None):
    return await client.post(
        "/transactions",
        headers={"Idempotency-Key": key or new_key()},
        json=payload,
    )


def balanced_payload(description="Test transaction", amount="1500.0000"):
    return {
        "description": description,
        "entries": [
            {"account_id": ASSET_ACCOUNT, "amount": amount},
            {"account_id": REVENUE_ACCOUNT, "amount": f"-{amount}"},
        ],
    }


async def test_balanced_two_entry_transaction_succeeds(client, db_pool):
    response = await post_transaction(client, balanced_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "success"
    tx_id = body["transaction_id"]

    rows = await db_pool.fetch(
        "SELECT account_id, amount FROM entries WHERE transaction_id = $1 ORDER BY amount", tx_id
    )
    assert len(rows) == 2
    assert str(rows[0]["account_id"]) == REVENUE_ACCOUNT
    assert str(rows[1]["account_id"]) == ASSET_ACCOUNT


async def test_balanced_multi_entry_split_succeeds(client, db_pool):
    payload = {
        "description": "Split payment",
        "entries": [
            {"account_id": ASSET_ACCOUNT, "amount": "100.0000"},
            {"account_id": REVENUE_ACCOUNT, "amount": "-60.0000"},
            {"account_id": CLIENT_ACCOUNT, "amount": "-40.0000"},
        ],
    }

    response = await post_transaction(client, payload)

    assert response.status_code == 201
    tx_id = response.json()["transaction_id"]
    count = await db_pool.fetchval("SELECT count(*) FROM entries WHERE transaction_id = $1", tx_id)
    assert count == 3


async def test_imbalanced_entries_rejected(client, db_pool):
    payload = {
        "description": "Broken transaction",
        "entries": [
            {"account_id": ASSET_ACCOUNT, "amount": "100.0000"},
            {"account_id": REVENUE_ACCOUNT, "amount": "-99.0000"},
        ],
    }
    key = new_key()

    response = await post_transaction(client, payload, key=key)

    assert response.status_code == 422
    tx_count = await db_pool.fetchval("SELECT count(*) FROM transactions")
    assert tx_count == 0

    # The balance check runs before the idempotency record is written, so no
    # PROCESSING/COMPLETED row exists for this key at all.
    idem_row = await db_pool.fetchrow(
        "SELECT 1 FROM idempotency_keys WHERE idempotency_key = $1", key
    )
    assert idem_row is None


async def test_single_entry_rejected(client, db_pool):
    payload = {
        "description": "Not a real transaction",
        "entries": [{"account_id": ASSET_ACCOUNT, "amount": "100.0000"}],
    }

    response = await post_transaction(client, payload)

    assert response.status_code == 400
    tx_count = await db_pool.fetchval("SELECT count(*) FROM transactions")
    assert tx_count == 0


async def test_idempotency_replay_does_not_duplicate_the_write(client, db_pool):
    key = new_key()
    payload = balanced_payload()

    first = await post_transaction(client, payload, key=key)
    second = await post_transaction(client, payload, key=key)

    assert first.status_code == 201
    assert second.status_code == first.status_code

    # Replays go through check_idempotency's `raise HTTPException(status_code=..., detail=body)`,
    # which FastAPI wraps under a "detail" key even for the stored success body - so the replayed
    # response is same-status but not byte-identical to the original. Documented here as actual
    # behavior, not the ideal behavior.
    assert second.json() == {"detail": first.json()}

    tx_count = await db_pool.fetchval("SELECT count(*) FROM transactions")
    assert tx_count == 1


async def test_missing_idempotency_key_header_rejected(client):
    response = await client.post("/transactions", json=balanced_payload())

    assert response.status_code == 422


async def test_fk_violation_rolls_back_idempotency_record(client, db_pool):
    payload = {
        "description": "Bad account reference",
        "entries": [
            {"account_id": NONEXISTENT_ACCOUNT, "amount": "50.0000"},
            {"account_id": REVENUE_ACCOUNT, "amount": "-50.0000"},
        ],
    }
    key = new_key()

    response = await post_transaction(client, payload, key=key)

    assert response.status_code == 500

    tx_count = await db_pool.fetchval("SELECT count(*) FROM transactions")
    assert tx_count == 0

    idem_row = await db_pool.fetchrow(
        "SELECT status FROM idempotency_keys WHERE idempotency_key = $1", key
    )
    assert idem_row is None, "idempotency key insert should have rolled back with the failed write"


async def test_decimal_precision_round_trips_exactly(client, db_pool):
    response = await post_transaction(client, balanced_payload(amount="1500.0000"))

    assert response.status_code == 201
    tx_id = response.json()["transaction_id"]

    amounts = await db_pool.fetch(
        "SELECT amount FROM entries WHERE transaction_id = $1 ORDER BY amount", tx_id
    )
    assert [str(row["amount"]) for row in amounts] == ["-1500.0000", "1500.0000"]
