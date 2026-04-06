from ninja import Schema,ModelSchema
from .models import Compra, CompraProducto
from typing import Optional,Literal
from decimal import Decimal
from producto.schemas import ProductoSchema
from pedido.schemas import PedidoSchema
from pedido.models import PedidoProducto

class CompraProductoSchema(ModelSchema):
    producto: ProductoSchema
    producto_nombre: str
    producto_imagen: Optional[str] = None
    precio_venta: float

    class Meta:
        model = CompraProducto
        fields = ['unidad_medida', 'cantidad', 'estado_compra', 'motivo_no_compra', 'precio_de_compra', 'ganancia_deseada']

    @staticmethod
    def resolve_producto(compra_producto: CompraProducto):
        return ProductoSchema.from_orm(compra_producto.producto)

    @staticmethod
    def resolve_producto_nombre(compra_producto: CompraProducto):
        return compra_producto.producto.nombre

    @staticmethod
    def resolve_producto_imagen(compra_producto: CompraProducto):
        imagen = compra_producto.producto.imagen
        return imagen.url if imagen else None

    @staticmethod
    def resolve_precio_venta(compra_producto: CompraProducto):
        precio = Decimal(compra_producto.precio_de_compra or 0)
        ganancia = Decimal(compra_producto.ganancia_deseada or 0)
        return float(precio + (precio * ganancia / Decimal(100)))
    

class CompraSchema(ModelSchema):
    productos: list[CompraProductoSchema] = []
    pedido: PedidoSchema
    pedido_productos: list["PedidoProductoCompraSchema"] = []
    creado_por_nombre: str
    class Meta:
        model = Compra
        fields = '__all__'
    
    @staticmethod
    def resolve_productos(compra: Compra):
        productos = CompraProducto.objects.filter(compra=compra).select_related('producto')
        return [CompraProductoSchema.from_orm(cp) for cp in productos]

    @staticmethod
    def resolve_pedido(compra: Compra):
        return compra.en_respuesta_a_pedido

    @staticmethod
    def resolve_pedido_productos(compra: Compra):
        productos_pedido = PedidoProducto.objects.filter(
            pedido=compra.en_respuesta_a_pedido
        ).select_related("producto")

        compra_productos = {
            cp.producto_id: cp
            for cp in CompraProducto.objects.filter(compra=compra).select_related("producto")
        }

        resultado = []
        for pp in productos_pedido:
            cp = compra_productos.get(pp.producto_id)
            resultado.append(
                PedidoProductoCompraSchema(
                    id=pp.id,
                    producto=ProductoSchema.from_orm(pp.producto),
                    cantidad_solicitada=pp.cantidad,
                    unidad_medida=pp.unidad_medida,
                    estado_compra=cp.estado_compra if cp else None,
                    motivo_no_compra=cp.motivo_no_compra if cp else None,
                )
            )
        return resultado

    @staticmethod
    def resolve_creado_por_nombre(compra: Compra):
        return compra.creado_por.nombre


class PedidoProductoCompraSchema(Schema):
    id: int
    producto: ProductoSchema
    cantidad_solicitada: float
    unidad_medida: str
    estado_compra: Optional[Literal['comprado', 'no_comprado']] = None
    motivo_no_compra: Optional[str] = None

class CompraCreateSchema(Schema):
    en_respuesta_a_pedido_id: int

class AgregarProductoCompraSchema(Schema):
    producto_id: int
    pedido_producto_id: Optional[int] = None  # Linkear a PedidoProducto opcional
    cantidad: Optional[float] = None
    unidad_medida: Optional[str] = None
    precio_de_compra: float
    ganancia_deseada: Optional[float] = None
    estado_compra: Optional[Literal['comprado', 'no_comprado']] = 'comprado'
    motivo_no_compra: Optional[str] = None

class EliminarProductoCompraSchema(Schema):
    producto_id: int

class ActualizarProductoCompraSchema(Schema):
    producto_id: int
    cantidad: Optional[float] = None
    unidad_medida: Optional[str] = None
    precio_de_compra: Optional[float] = None
    ganancia_deseada: Optional[float] = None
    estado_compra: Optional[Literal['comprado', 'no_comprado']] = None
    motivo_no_compra: Optional[str] = None

class CompraUpdateSchema(Schema):
    estado: Optional[Literal['en_proceso', 'completado']] = None






    