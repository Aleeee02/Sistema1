"""Comprueba la URL y clave privada de Supabase sin mostrarlas."""

import asyncio

import httpx

from app.core.config import settings


async def main() -> None:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        print("STATUS=FAILED")
        print("ERROR=Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY")
        raise SystemExit(1)

    headers = {"apikey": settings.supabase_service_role_key}
    if settings.supabase_service_role_key.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {settings.supabase_service_role_key}"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"{settings.supabase_url.rstrip('/')}/rest/v1/",
                headers=headers,
            )
        print(f"STATUS_CODE={response.status_code}")
        if response.status_code == 200:
            print("STATUS=CONNECTED")
        elif response.status_code in (401, 403):
            print("STATUS=INVALID_KEY")
            raise SystemExit(1)
        else:
            print("STATUS=FAILED")
            raise SystemExit(1)
    except httpx.HTTPError as exc:
        print("STATUS=FAILED")
        print(f"ERROR_TYPE={type(exc).__name__}")
        raise SystemExit(1) from None


if __name__ == "__main__":
    asyncio.run(main())
