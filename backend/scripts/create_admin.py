"""Crea el primer administrador utilizando una empresa existente."""

import argparse
import asyncio
import getpass
import uuid

from sqlalchemy import func, select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal, engine
from app.models.empresa import Empresa
from app.models.usuario import Rol, Usuario, UsuarioEmpresa


async def main() -> None:
    parser = argparse.ArgumentParser(description="Crear administrador")
    parser.add_argument("--empresa-id", help="UUID de una empresa existente")
    parser.add_argument("--email")
    parser.add_argument("--nombres")
    parser.add_argument("--apellidos")
    args = parser.parse_args()

    async with AsyncSessionLocal() as db:
        empresas = list(
            (
                await db.scalars(
                    select(Empresa)
                    .where(Empresa.estado == "activo")
                    .order_by(Empresa.nombre_comercial)
                )
            ).all()
        )
        if not empresas:
            raise SystemExit("No existe ninguna empresa activa en la base de datos.")

        print("Empresas disponibles:")
        for empresa in empresas:
            print(f"- {empresa.nombre_comercial}: {empresa.id}")

        empresa_text = args.empresa_id or input("UUID de la empresa: ").strip()
        try:
            empresa_id = uuid.UUID(empresa_text)
        except ValueError:
            raise SystemExit("El UUID de empresa no es válido.") from None

        empresa = await db.scalar(
            select(Empresa).where(
                Empresa.id == empresa_id,
                Empresa.estado == "activo",
            )
        )
        if not empresa:
            raise SystemExit("La empresa indicada no existe o está inactiva.")

        email = (args.email or input("Correo: ")).strip().lower()
        nombres = (args.nombres or input("Nombres: ")).strip()
        apellidos = (args.apellidos or input("Apellidos: ")).strip()
        password = getpass.getpass("Contraseña (mínimo 8 caracteres): ")
        confirmation = getpass.getpass("Repite la contraseña: ")
        if len(password) < 8:
            raise SystemExit("La contraseña debe tener al menos 8 caracteres.")
        if password != confirmation:
            raise SystemExit("Las contraseñas no coinciden.")

        existing = await db.scalar(
            select(Usuario).where(func.lower(Usuario.email) == email)
        )
        if existing:
            raise SystemExit("Ya existe un usuario con ese correo.")

        rol = await db.scalar(select(Rol).where(Rol.codigo == "administrador"))
        if not rol:
            raise SystemExit("No existe el rol inicial 'administrador'.")

        usuario = Usuario(
            email=email,
            password_hash=hash_password(password),
            nombres=nombres,
            apellidos=apellidos,
            estado="activo",
        )
        db.add(usuario)
        await db.flush()
        db.add(
            UsuarioEmpresa(
                usuario_id=usuario.id,
                empresa_id=empresa.id,
                rol_id=rol.id,
                estado="activo",
            )
        )
        await db.commit()
        print(f"Administrador creado para {empresa.nombre_comercial}.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
