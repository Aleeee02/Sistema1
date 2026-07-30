from datetime import date
from decimal import Decimal

from app.schemas.common import ORMModel


class SeriePunto(ORMModel):
    fecha: date
    valor: Decimal


class CategoriaValor(ORMModel):
    nombre: str
    cantidad: Decimal
    valor: Decimal = Decimal("0")


class EstadisticasRead(ORMModel):
    ingresos: Decimal
    por_cobrar: Decimal
    ordenes_creadas: int
    ordenes_cerradas: int
    ordenes_activas: int
    ticket_promedio: Decimal
    ingresos_diarios: list[SeriePunto]
    ordenes_por_estado: list[CategoriaValor]
    servicios_principales: list[CategoriaValor]
    pagos_por_metodo: list[CategoriaValor]
