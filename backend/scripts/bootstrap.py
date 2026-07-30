"""Crea de forma interactiva la primera empresa, sucursal y administrador."""

import asyncio
import getpass
import re

from sqlalchemy import func, select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal, engine
from app.models.empresa import Empresa, Sucursal
from app.models.usuario import Rol, Usuario, UsuarioEmpresa


async def main() -> None:
    print("Configuración inicial del sistema")
    print("--------------------------------")
    nombre_comercial = input("Nombre comercial: ").strip()
    razon_social = input("Razón social: ").strip()
    ruc = input("RUC (11 dígitos): ").strip()
    if not re.fullmatch(r"\d{11}", ruc):
        raise SystemExit("El RUC debe contener exactamente 11 dígitos.")

    email = input("Correo del administrador: ").strip().lower()
    nombres = input("Nombres del administrador: ").strip()
    apellidos = input("Apellidos del administrador: ").strip()
    password = getpass.getpass("Contraseña (mínimo 8 caracteres): ")
    confirmation = getpass.getpass("Repite la contraseña: ")
    if len(password) < 8:
        raise SystemExit("La contraseña debe tener al menos 8 caracteres.")
    if password != confirmation:
        raise SystemExit("Las contraseñas no coinciden.")

    async with AsyncSessionLocal() as db:
        if await db.scalar(select(Empresa).where(Empresa.ruc == ruc)):
            raise SystemExit("Ya existe una empresa con ese RUC.")
        if await db.scalar(
            select(Usuario).where(func.lower(Usuario.email) == email)
        ):
            raise SystemExit("Ya existe un usuario con ese correo.")

        rol = await db.scalar(select(Rol).where(Rol.codigo == "administrador"))
        if not rol:
            raise SystemExit("No existe el rol inicial 'administrador'.")

        empresa = Empresa(
            nombre_comercial=nombre_comercial,
            razon_social=razon_social,
            ruc=ruc,
            estado="activo",
        )
        db.add(empresa)
        await db.flush()

        db.add(
            Sucursal(
                empresa_id=empresa.id,
                nombre="Sucursal principal",
                codigo="PRINCIPAL",
                es_principal=True,
                estado="activo",
            )
        )

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

        print("")
        print("Configuración completada.")
        print(f"Empresa: {empresa.nombre_comercial}")
        print(f"Correo de acceso: {usuario.email}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
