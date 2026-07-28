import asyncio
import os
import asyncpg

async def main():
    conn = await asyncpg.connect(
        host=os.getenv("DB_HOST"),
        port=5432,
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

    try:
        with open("initialization/01_init.sql", "r") as f:
            sql_commands = f.read()

        await conn.execute(sql_commands)
        print("Database initialized successfully!")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())