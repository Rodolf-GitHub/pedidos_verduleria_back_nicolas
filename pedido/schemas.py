from ninja import Schema,ModelSchema
from .models import Pedido, PedidoProducto
from typing import Optional,Literal
from producto.schemas import ProductoSchema
from datetime import datetime

class PedidoSimpleSchema(ModelSchema):
    cantidad_productos: int = 0
    creado_por_nombre: str
    class Meta:
        model = Pedido
        fields = "__all__"
    @staticmethod
    def resolve_cantidad_productos(pedido: Pedido):
        if hasattr(pedido, "cantidad_productos"):
            return pedido.cantidad_productos
        return PedidoProducto.objects.filter(pedido=pedido).count()
    @staticmethod
    def resolve_creado_por_nombre(pedido: Pedido):
        return pedido.creado_por.nombre


class PedidoProductoSchema(ModelSchema):
    producto: ProductoSchema
    class Meta:
        model = PedidoProducto
        fields = ["id", "producto", "cantidad", "unidad_medida"]
    
    @staticmethod
    def resolve_producto(pedido_producto: PedidoProducto):
        return ProductoSchema.from_orm(pedido_producto.producto)

class PedidoSchema(ModelSchema):
    productos: list[PedidoProductoSchema] = []
    creado_por_nombre: str
    class Meta:
        model = Pedido
        fields = '__all__'
    @staticmethod
    def resolve_productos(pedido: Pedido):
        productos = PedidoProducto.objects.filter(pedido=pedido).select_related('producto')
        return [PedidoProductoSchema.from_orm(pp) for pp in productos]

    @staticmethod
    def resolve_creado_por_nombre(pedido: Pedido):
        return pedido.creado_por.nombre

class PedidoCreateSchema(Schema):
    negocio_id: int

class AgregarProductoPedidoSchema(Schema):
    producto_id: int
    cantidad: float
    unidad_medida: Optional[Literal['kg', 'unidades', 'litros', 'otros', 'atados','cajas','sacos','bandejas','planchas']] = 'cajas'
    

class EliminarProductoPedidoSchema(Schema):
    producto_id: int

class ActualizarProductoPedidoSchema(Schema):
    producto_id: int
    cantidad: Optional[float] = None
    unidad_medida: Optional[Literal['kg', 'unidades', 'litros', 'otros', 'atados','cajas','sacos','bandejas','planchas']] = None

class PedidoUpdateSchema(Schema):
    estado: Optional[Literal['en_proceso', 'completado']] = None

class PedidoActualizarFechaSchema(Schema):
    fecha_creacion: datetime




