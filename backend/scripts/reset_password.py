"""Restablece de forma interactiva la contraseña de un usuario."""

import asyncio
import getpass

from sqlalchemy import func, select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal, engine
from app.models.usuario import Usuario


async def main() -> None:
    email = input("Correo del usuario: ").strip().lower()
    password = getpass.getpass("Nueva contraseña (mínimo 8 caracteres): ")
    confirmation = getpass.getpass("Repite la nueva contraseña: ")

    if len(password) < 8:
        raise SystemExit("La contraseña debe tener al menos 8 caracteres.")
    if password != confirmation:
        raise SystemExit("Las contraseñas no coinciden.")

    async with AsyncSessionLocal() as db:
        usuario = await db.scalar(
            select(Usuario).where(func.lower(Usuario.email) == email)
        )
        if not usuario:
            raise SystemExit("No existe un usuario con ese correo.")

        usuario.password_hash = hash_password(password)
        usuario.estado = "activo"
        await db.commit()
        print("Contraseña actualizada correctamente.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
