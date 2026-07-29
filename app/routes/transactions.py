from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from typing import List
from decimal import Decimal
from uuid import UUID
import json
from asyncpg import Connection

from app.database import get_db
from app.dependencies.idempotency import check_idempotency

router = APIRouter(prefix="/transactions", tags=["Transactions"])

class EntryCreate(BaseModel):
    account_id: UUID
    amount: Decimal = Field(..., max_digits=12, decimal_places=4, examples=[Decimal("-64.0000")])

class TransactionCreate(BaseModel):
    description: str = Field(..., examples=["Revolut payment"])
    entries: List[EntryCreate]

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "description": "Request description",
                    "entries": [
                        {"account_id": "b0000000-0000-0000-0000-000000000002", "amount": "1500.0000"},
                        {"account_id": "a0000000-0000-0000-0000-000000000001", "amount": "-1500.0000"},
                    ],
                }
            ]
        }
    )

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_transaction(
    payload: TransactionCreate,
    db: Connection = Depends(get_db),
    idem_key: str = Depends(check_idempotency)
):
    if len(payload.entries) < 2:
        raise HTTPException(status_code=400, detail="Invalid transaction structure. Minimum 2 entries required.")

    total_balance = sum(e.amount for e in payload.entries)
    if round(total_balance, 4) != Decimal("0.0000"):
        raise HTTPException(status_code=422, detail="Transaction imbalance. Credits and Debits must have the same absolute value.")

    async with db.transaction():
        try:
            await db.execute(
                """
                INSERT INTO idempotency_keys (idempotency_key, status) 
                VALUES ($1, 'PROCESSING');
                """,
                idem_key
            )

            tx_id = await db.fetchval(
                "INSERT INTO transactions (description, idempotency_key) VALUES ($1, $2) RETURNING id;",
                payload.description, idem_key
            )
            
            for entry in payload.entries:
                await db.execute(
                    "INSERT INTO entries (transaction_id, account_id, amount) VALUES ($1, $2, $3);",
                    tx_id, entry.account_id, entry.amount
                )
                
            response_body = {"status": "success", "transaction_id": str(tx_id)}
            status_code = 201
            
            await db.execute(
                """
                UPDATE idempotency_keys 
                SET status = 'COMPLETED', response_code = $2, response_body = $3 
                WHERE idempotency_key = $1;
                """,
                idem_key, status_code, json.dumps(response_body)
            )
            
            return response_body

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal ledger execution failed: {str(e)}")