import argparse
import asyncio
from pathlib import Path
import sys

from sqlalchemy import func, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import AsyncSessionLocal
from app.models.usuario import Usuario


async def main(email: str) -> None:
    async with AsyncSessionLocal() as db:
        user = await db.scalar(select(Usuario).where(func.lower(Usuario.email) == email.lower()))
        if not user:
            raise SystemExit(f"No existe un usuario con el correo {email}")
        user.es_superadmin = True
        await db.commit()
        print(f"Superadministrador habilitado: {user.email}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    args = parser.parse_args()
    asyncio.run(main(args.email))
