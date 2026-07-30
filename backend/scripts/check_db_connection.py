import asyncio

from app.db.session import engine


async def main() -> None:
    try:
        async with engine.connect() as connection:
            await connection.exec_driver_sql("SELECT 1")
        print("DB_OK")
    except Exception as exc:
        print(type(exc).__name__)
        print(str(exc).replace("\n", " ")[:800])
        raise SystemExit(1) from exc
    finally:
        await engine.dispose()


asyncio.run(main())
