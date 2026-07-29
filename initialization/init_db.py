import asyncio
import os
import sys
import asyncpg


async def main():
    with_mock = "--with-mock" in sys.argv

    conn = await asyncpg.connect(
        host=os.getenv("DB_HOST"),
        port=5432,
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

    try:
        with open("initialization/01_schema.sql", "r") as f:
            await conn.execute(f.read())
        print("Schema applied successfully!")

        if with_mock:
            with open("initialization/02_mock_seed.sql", "r") as f:
                await conn.execute(f.read())
            print("Mock data seeded successfully!")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
