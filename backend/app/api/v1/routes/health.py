from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter(prefix="/health", tags=["system"])


@router.get("")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/database")
async def database_health(
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="No fue posible conectar con PostgreSQL",
        ) from exc
    return {"status": "ok", "database": "connected"}

