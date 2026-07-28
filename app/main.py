from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import init_db_pool
from app.routes.transactions import router as transactions_router
from dotenv import load_dotenv

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db_pool()
    yield

app = FastAPI(
    title="Mini Ledger",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(transactions_router)

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}