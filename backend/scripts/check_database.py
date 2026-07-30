"""Comprueba la conexión sin imprimir credenciales."""

import asyncio

from sqlalchemy import text

from app.db.session import engine


async def main() -> None:
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    """
                    SELECT
                        current_database() AS database_name,
                        current_user AS database_user,
                        version() AS database_version
                    """
                )
            )
            row = result.one()
            counts = (
                await connection.execute(
                    text(
                        """
                        SELECT
                            (SELECT count(*) FROM public.empresas
                             WHERE estado = 'activo') AS active_companies,
                            (SELECT count(*) FROM public.usuarios) AS users,
                            (SELECT count(*) FROM public.usuarios
                             WHERE estado = 'activo'
                               AND password_hash IS NOT NULL) AS login_ready_users,
                            (SELECT count(*) FROM public.usuarios_empresas
                             WHERE estado = 'activo') AS active_memberships,
                            (SELECT count(*) FROM public.roles) AS roles
                        """
                    )
                )
            ).one()
            print("STATUS=CONNECTED")
            print(f"DATABASE={row.database_name}")
            print(f"USER={row.database_user}")
            print(f"VERSION={row.database_version.split(',')[0]}")
            print(f"ACTIVE_COMPANIES={counts.active_companies}")
            print(f"USERS={counts.users}")
            print(f"LOGIN_READY_USERS={counts.login_ready_users}")
            print(f"ACTIVE_MEMBERSHIPS={counts.active_memberships}")
            print(f"ROLES={counts.roles}")
    except Exception as exc:
        print("STATUS=FAILED")
        print(f"ERROR_TYPE={type(exc).__name__}")
        print(f"ERROR={exc}")
        raise SystemExit(1) from None
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
