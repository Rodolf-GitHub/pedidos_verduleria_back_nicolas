from ninja import Schema
from typing import Optional, Literal
from producto.schemas import ProductoSchema


class PedidoDiarioTotalPorUnidadSchema(Schema):
    unidad_medida: Optional[str] = None
    cantidad_total: float


class PedidoDiarioCantidadNegocioSchema(Schema):
    negocio_id: int
    negocio_nombre: str
    cantidad: float
    unidad_medida: Optional[str] = None


class PedidoDiarioUnidadSchema(Schema):
    unidad_pedido: Optional[str] = None
    totales_por_unidad: list[PedidoDiarioTotalPorUnidadSchema] = []
    estado_compra: Optional[Literal['comprado', 'no_comprado']] = None
    precio_compra: Optional[float] = None
    factor_division: Optional[float] = None
    ganancia_aplicada: Optional[float] = None
    motivo_no_compra: Optional[str] = None


class PedidoDiarioProductoSchema(Schema):
    producto: ProductoSchema
    cantidades_por_negocio: list[PedidoDiarioCantidadNegocioSchema] = []
    total: PedidoDiarioUnidadSchema


class PedidoDiarioSchema(Schema):
    fecha: str
    estado: Optional[Literal['en_proceso', 'completado']] = None
    items: list[PedidoDiarioProductoSchema] = []



class PedidoDiarioEstadoUpdateSchema(Schema):
    producto_id: int
    estado_compra: Literal['comprado', 'no_comprado']
    motivo_no_compra: Optional[str] = None
    precio_compra: Optional[float] = None
    factor_division: Optional[float] = None
    ganancia_aplicada: Optional[float] = None


class PedidoDiarioUpdateSchema(Schema):
	estado: Literal['en_proceso', 'completado']

class PedidosSinCompletarSchema(Schema):
    fecha: str
    urgencia: Literal['sin_urgencia', 'a_tiempo', 'pendiente', 'critico']
    