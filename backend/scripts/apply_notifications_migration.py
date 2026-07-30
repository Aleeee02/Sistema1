import asyncio
from pathlib import Path
import sys
import asyncpg
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import settings
async def main():
    url=settings.database_url.replace("postgresql+asyncpg://","postgresql://",1)
    sql=(Path(__file__).resolve().parents[1]/"sql"/"2026_07_29_notificaciones.sql").read_text(encoding="utf-8")
    connection=await asyncpg.connect(url,ssl="require" if settings.database_ssl else None)
    try:
        await connection.execute(sql)
        if await connection.fetchval("SELECT to_regclass('public.notificaciones')::text")!="notificaciones": raise RuntimeError("No se pudo verificar notificaciones")
        print("Migración aplicada: notificaciones")
    finally: await connection.close()
if __name__=="__main__": asyncio.run(main())
