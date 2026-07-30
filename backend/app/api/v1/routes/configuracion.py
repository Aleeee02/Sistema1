from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentContext
from app.db.session import get_db
from app.schemas.configuracion import EmpresaConfigRead, EmpresaConfigUpdate
from app.services.auditoria import record_audit

router = APIRouter()


@router.get("", response_model=EmpresaConfigRead)
async def get_configuration(context: CurrentContext):
    return EmpresaConfigRead.model_validate(context.empresa)


@router.put("", response_model=EmpresaConfigRead)
async def update_configuration(
    payload: EmpresaConfigUpdate,
    context: CurrentContext,
    db: AsyncSession = Depends(get_db),
):
    before = {
        "nombre_comercial": context.empresa.nombre_comercial,
        "ruc": context.empresa.ruc,
        "porcentaje_impuesto": str(context.empresa.porcentaje_impuesto),
    }
    values = payload.model_dump()
    for key, value in values.items():
        if isinstance(value, str):
            value = value.strip() or None
        if key in {"moneda", "prefijo_orden", "prefijo_cotizacion"} and value:
            value = value.upper()
        setattr(context.empresa, key, value)
    record_audit(
        db, context, "actualizar", "empresas", context.empresa.id,
        before=before,
        after=payload.model_dump(mode="json"),
    )
    await db.commit()
    await db.refresh(context.empresa)
    return EmpresaConfigRead.model_validate(context.empresa)
