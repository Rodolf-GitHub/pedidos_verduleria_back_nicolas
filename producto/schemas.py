from ninja import Schema,ModelSchema
from .models import Producto
from typing import Optional,Literal
from datetime import timedelta
import math
from django.utils import timezone

class ProductoSchema(ModelSchema):
    precio_venta: Optional[float] = None
    actualizado_recientemente: Optional[bool] = None
    precio_compra_unitario: Optional[float] = None
    class Meta:
        model = Producto
        fields = '__all__'
    @staticmethod
    def resolve_precio_compra_unitario(producto: Producto):
        if producto.precio_compra is not None and producto.factor_division is not None and producto.factor_division != 0:
            return round(float(producto.precio_compra) / float(producto.factor_division), 2)
        return None
    @staticmethod
    def resolve_precio_venta(producto: Producto):
        if getattr(producto, "precio_venta", None) is not None:
            return float(producto.precio_venta)
        if producto.precio_compra is None or producto.factor_division in (None, 0) or producto.ganancia_porcentaje is None:
            return None
        try:
            base = float(producto.precio_compra) / float(producto.factor_division)
            precio = base * (1 + float(producto.ganancia_porcentaje) / 100)
            # Redondear a la decena superior terminada en 9
            decena = int(precio // 10) * 10
            if precio > decena + 9:
                decena += 10
            return float(decena + 9)
        except Exception:
            return None

    @staticmethod
    def resolve_actualizado_recientemente(producto: Producto):
        if not producto.ultima_actualizacion:
            return False
        return timezone.now() - producto.ultima_actualizacion < timedelta(hours=24)

class ProductoCreateSchema(Schema):
    nombre: str
    se_vende_en_unidad_medida: Optional[Literal['kg', 'unidades', 'litros', 'otros', 'atados','cajas','sacos','bandejas','planchas']] = 'kg'
    se_compra_en_unidad_medida: Optional[Literal['kg', 'unidades', 'litros', 'otros', 'atados','cajas','sacos','bandejas','planchas']] = 'kg'
    factor_division: Optional[float] = 1.0
    precio_compra: Optional[float] = 100.00
    ganancia_porcentaje: Optional[float] = 40.00

class ProductoUpdateSchema(Schema):
    nombre: Optional[str] = None
    se_vende_en_unidad_medida: Optional[Literal['kg', 'unidades', 'litros', 'otros', 'atados','cajas','sacos','bandejas','planchas']] = None
    precio_compra: Optional[float] = None
    ganancia_porcentaje: Optional[float] = None
    factor_division: Optional[float] = None
    se_compra_en_unidad_medida: Optional[Literal['kg', 'unidades', 'litros', 'otros', 'atados','cajas','sacos','bandejas','planchas']] = None