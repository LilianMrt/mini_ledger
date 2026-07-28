import json
from fastapi import Header, HTTPException, Depends
from app.database import get_db
import asyncpg

async def check_idempotency(
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: asyncpg.Connection = Depends(get_db)
):
    row = await db.fetchrow(
        "SELECT response_code, response_body FROM idempotency_keys WHERE idempotency_key = $1;", 
        idempotency_key
    )
    
    if row:
        body = json.loads(row['response_body'])
        raise HTTPException(
            status_code=row['response_code'],
            detail=body
        )
    return idempotency_key