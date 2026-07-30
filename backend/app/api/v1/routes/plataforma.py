import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SuperadminContext
from app.core.security import hash_password
from app.db.session import get_db
from app.models.empresa import Empresa, Sucursal
from app.models.orden import OrdenTrabajo
from app.models.usuario import Rol, Usuario, UsuarioEmpresa, UsuarioSucursal
from app.schemas.plataforma import (
    EmpresaPlataformaCreate,
    EmpresaPlataformaRead,
    EmpresaPlataformaUpdate,
    ResumenPlataforma,
)

router = APIRouter()


async def _serialize(db: AsyncSession, empresa: Empresa) -> EmpresaPlataformaRead:
    usuarios = await db.scalar(
        select(func.count(UsuarioEmpresa.id)).where(
            UsuarioEmpresa.empresa_id == empresa.id,
            UsuarioEmpresa.estado == "activo",
        )
    )
    sucursales = await db.scalar(
        select(func.count(Sucursal.id)).where(
            Sucursal.empresa_id == empresa.id, Sucursal.estado == "activo"
        )
    )
    ordenes = await db.scalar(
        select(func.count(OrdenTrabajo.id)).where(OrdenTrabajo.empresa_id == empresa.id)
    )
    return EmpresaPlataformaRead.model_validate(
        {
            **{column.name: getattr(empresa, column.name) for column in Empresa.__table__.columns},
            "usuarios_activos": usuarios or 0,
            "sucursales_activas": sucursales or 0,
            "ordenes_total": ordenes or 0,
        }
    )


@router.get("/resumen", response_model=ResumenPlataforma)
async def resumen(_: SuperadminContext, db: AsyncSession = Depends(get_db)):
    total = await db.scalar(select(func.count(Empresa.id)))
    activas = await db.scalar(select(func.count(Empresa.id)).where(Empresa.estado == "activo"))
    pruebas = await db.scalar(
        select(func.count(Empresa.id)).where(Empresa.suscripcion_estado == "prueba")
    )
    vencidas = await db.scalar(
        select(func.count(Empresa.id)).where(Empresa.suscripcion_estado == "vencida")
    )
    usuarios = await db.scalar(
        select(func.count(UsuarioEmpresa.id)).where(UsuarioEmpresa.estado == "activo")
    )
    return ResumenPlataforma(
        empresas_total=total or 0,
        empresas_activas=activas or 0,
        empresas_prueba=pruebas or 0,
        empresas_vencidas=vencidas or 0,
        usuarios_activos=usuarios or 0,
    )


@router.get("/empresas", response_model=list[EmpresaPlataformaRead])
async def list_companies(_: SuperadminContext, db: AsyncSession = Depends(get_db)):
    companies = (
        await db.scalars(select(Empresa).order_by(Empresa.created_at.desc()))
    ).all()
    return [await _serialize(db, company) for company in companies]


@router.post("/empresas", response_model=EmpresaPlataformaRead, status_code=status.HTTP_201_CREATED)
async def create_company(
    payload: EmpresaPlataformaCreate,
    context: SuperadminContext,
    db: AsyncSession = Depends(get_db),
):
    if await db.scalar(select(Usuario.id).where(func.lower(Usuario.email) == payload.admin_email.lower())):
        raise HTTPException(status_code=409, detail="El correo del administrador ya está registrado")
    role = await db.scalar(
        select(Rol).where(
            Rol.codigo == "administrador",
            Rol.estado == "activo",
            Rol.empresa_id.is_(None),
        )
    )
    if not role:
        raise HTTPException(status_code=409, detail="No existe el rol de administrador del sistema")

    company = Empresa(
        nombre_comercial=payload.nombre_comercial.strip(),
        razon_social=payload.razon_social.strip(),
        ruc=payload.ruc,
        email=str(payload.email) if payload.email else None,
        telefono=payload.telefono,
        plan_codigo=payload.plan_codigo,
        suscripcion_estado="prueba",
        suscripcion_fin=payload.suscripcion_fin,
        max_usuarios=payload.max_usuarios,
        max_sucursales=payload.max_sucursales,
    )
    admin = Usuario(
        email=str(payload.admin_email).lower(),
        password_hash=hash_password(payload.admin_password),
        nombres=payload.admin_nombres.strip(),
        apellidos=payload.admin_apellidos.strip(),
    )
    try:
        db.add_all([company, admin])
        await db.flush()
        branch = Sucursal(
            empresa_id=company.id,
            nombre="Principal",
            codigo="PRINCIPAL",
            es_principal=True,
        )
        membership = UsuarioEmpresa(
            usuario_id=admin.id, empresa_id=company.id, rol_id=role.id
        )
        db.add_all([branch, membership])
        await db.flush()
        db.add(
            UsuarioSucursal(
                usuario_empresa_id=membership.id, sucursal_id=branch.id
            )
        )
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="El RUC, correo o empresa ya existe") from exc
    await db.refresh(company)
    return await _serialize(db, company)


@router.patch("/empresas/{empresa_id}", response_model=EmpresaPlataformaRead)
async def update_company(
    empresa_id: uuid.UUID,
    payload: EmpresaPlataformaUpdate,
    _: SuperadminContext,
    db: AsyncSession = Depends(get_db),
):
    company = await db.get(Empresa, empresa_id)
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(company, key, value.strip() if isinstance(value, str) else value)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="No se pudo actualizar la empresa") from exc
    await db.refresh(company)
    return await _serialize(db, company)
