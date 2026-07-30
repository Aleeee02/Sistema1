import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SuperadminContext
from app.core.security import hash_password
from app.db.session import get_db
from app.models.empresa import Empresa, PlanSaaS, Sucursal
from app.models.orden import OrdenTrabajo
from app.models.usuario import Rol, Usuario, UsuarioEmpresa, UsuarioSucursal
from app.schemas.plataforma import (
    EmpresaPlataformaCreate,
    EmpresaPlataformaRead,
    EmpresaPlataformaUpdate,
    PlanSaaSRead,
    PlanSaaSUpdate,
    ResumenPlataforma,
)

router = APIRouter()

MODULES = {
    "dashboard", "agenda", "clientes", "vehiculos", "ordenes", "cotizaciones",
    "inspecciones", "pagos", "servicios", "inventario", "transferencias",
    "empleados", "sucursales", "usuarios", "estadisticas", "reportes",
    "configuracion", "comprobantes", "auditoria",
}


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


@router.get("/planes", response_model=list[PlanSaaSRead])
async def list_plans(_: SuperadminContext, db: AsyncSession = Depends(get_db)):
    return list((await db.scalars(select(PlanSaaS).order_by(PlanSaaS.precio_mensual, PlanSaaS.nombre))).all())


@router.patch("/planes/{plan_id}", response_model=PlanSaaSRead)
async def update_plan(
    plan_id: uuid.UUID,
    payload: PlanSaaSUpdate,
    _: SuperadminContext,
    db: AsyncSession = Depends(get_db),
):
    plan = await db.get(PlanSaaS, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    values = payload.model_dump(exclude_unset=True)
    if "modulos" in values:
        invalid = set(values["modulos"]) - MODULES
        if invalid:
            raise HTTPException(status_code=422, detail=f"Módulos desconocidos: {', '.join(sorted(invalid))}")
        values["modulos"] = sorted(set(values["modulos"]) | {"dashboard"})
    for key, value in values.items():
        setattr(plan, key, value.strip() if isinstance(value, str) else value)
    await db.commit()
    await db.refresh(plan)
    return plan


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
    plan = await db.scalar(
        select(PlanSaaS).where(
            PlanSaaS.codigo == payload.plan_codigo, PlanSaaS.estado == "activo"
        )
    )
    if not plan:
        raise HTTPException(status_code=422, detail="El plan seleccionado no está disponible")

    company = Empresa(
        nombre_comercial=payload.nombre_comercial.strip(),
        razon_social=payload.razon_social.strip(),
        ruc=payload.ruc,
        email=str(payload.email) if payload.email else None,
        telefono=payload.telefono,
        plan_codigo=payload.plan_codigo,
        suscripcion_estado="prueba",
        suscripcion_fin=payload.suscripcion_fin,
        max_usuarios=plan.max_usuarios,
        max_sucursales=plan.max_sucursales,
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
    values = payload.model_dump(exclude_unset=True)
    if "plan_codigo" in values and values["plan_codigo"] != company.plan_codigo:
        plan = await db.scalar(
            select(PlanSaaS).where(
                PlanSaaS.codigo == values["plan_codigo"], PlanSaaS.estado == "activo"
            )
        )
        if not plan:
            raise HTTPException(status_code=422, detail="El plan seleccionado no está disponible")
        values.setdefault("max_usuarios", plan.max_usuarios)
        values.setdefault("max_sucursales", plan.max_sucursales)
    for key, value in values.items():
        setattr(company, key, value.strip() if isinstance(value, str) else value)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="No se pudo actualizar la empresa") from exc
    await db.refresh(company)
    return await _serialize(db, company)
