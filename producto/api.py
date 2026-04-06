from ninja import Router
from .schemas import ProductoSchema, ProductoCreateSchema, ProductoUpdateSchema
from usuarios.auth import AuthBearer,require_verdulero,require_admin
from .models import Producto
from django.shortcuts import get_object_or_404
from ninja import File, UploadedFile
from ninja.errors import HttpError
from core.utils.compress_image import compress_image
from core.utils.delete_image_file import delete_image_file
from core.utils.search_filter import search_filter
from ninja.pagination import paginate
from core.utils.auth import get_current_usuario
router = Router(tags=["Productos"])


def _calcular_precio_venta(precio_compra, factor_division, ganancia):
    if precio_compra is None or ganancia is None:
        return None
    try:
        factor = float(factor_division) if factor_division not in (None, 0) else 1.0
        precio = (float(precio_compra) / factor) * (1 + float(ganancia) / 100)
        decena = int(precio // 10) * 10
        if precio > decena + 9:
            decena += 10
        return float(decena + 9)
    except Exception:
        return None


def _ocultar_datos_compra_respuesta(producto: Producto):
    producto.precio_venta = _calcular_precio_venta(
        producto.precio_compra,
        producto.factor_division,
        producto.ganancia_porcentaje,
    )
    producto.precio_compra = None
    producto.precio_compra_unitario = None
    producto.ganancia_porcentaje = None
    return producto

@router.get("/listar", response=list[ProductoSchema], auth=AuthBearer())
@paginate
@search_filter(['nombre'])
def listar_productos(request):
    usuario = get_current_usuario(request)
    productos = Producto.objects.all().order_by('-ultima_actualizacion')

    if usuario.rol == 'verdulero':
        productos = [_ocultar_datos_compra_respuesta(producto) for producto in productos]

    return productos

@router.post("/crear", response=ProductoSchema, auth=AuthBearer())
def crear_producto(request, payload: ProductoCreateSchema, imagen: File[UploadedFile] = None):
    try:
        usuario = get_current_usuario(request)
        # Restricción: no permitir crear más de 500 productos
        total_productos = Producto.objects.count()
        if total_productos >= 500:
            raise HttpError(400, "Límite de productos alcanzado (500). No se puede crear un nuevo producto.")
        producto = Producto(
            nombre=payload.nombre,
            se_vende_en_unidad_medida=payload.se_vende_en_unidad_medida,
            se_pide_en_unidad_medida=payload.se_compra_en_unidad_medida,
            precio_compra=payload.precio_compra,
            ganancia_porcentaje=payload.ganancia_porcentaje,
            factor_division=payload.factor_division,
        )
        if imagen:
            # Comprimir imagen a ~50KB
            imagen_comprimida = compress_image(imagen, max_size_kb=50)
            producto.imagen = imagen_comprimida
        producto.save()
        if usuario.rol == 'verdulero':
            return _ocultar_datos_compra_respuesta(producto)
        return producto
    except Exception as e:
        raise HttpError(400, f"Error al crear el producto: {str(e)}")

@router.put("/actualizar/{producto_id}", response=ProductoSchema, auth=AuthBearer())
def actualizar_producto(request, producto_id: int, payload: ProductoUpdateSchema, imagen: File[UploadedFile] = None):
    try:
        from core.utils.auth import get_current_usuario
        from pedido.models import PedidoProducto
        usuario = get_current_usuario(request)
        producto = get_object_or_404(Producto, id=producto_id)
        
        # Calcular si hay diferencia relevante en precio_compra, ganancia_porcentaje y factor_division
        def cambio_relevante(actual, nuevo):
            try:
                if actual is None:
                    return True
                return abs(float(actual) - float(nuevo)) >= 0.01
            except Exception:
                return True

        precio_compra_cambia = payload.precio_compra is not None and cambio_relevante(producto.precio_compra, payload.precio_compra)
        ganancia_cambia = payload.ganancia_porcentaje is not None and cambio_relevante(producto.ganancia_porcentaje, payload.ganancia_porcentaje)
        factor_division_cambia = getattr(payload, 'factor_division', None) is not None and cambio_relevante(producto.factor_division, payload.factor_division)

        # Verdulero puede cambiar todo si el producto no está en ningún PedidoDiarioItem; si está asociado, solo puede cambiar la imagen
        if usuario.rol == 'verdulero':
            from pedido_diario.models import PedidoDiarioItem
            asociado = PedidoDiarioItem.objects.filter(producto=producto).exists()
            if asociado:
                if (
                    precio_compra_cambia
                    or ganancia_cambia
                    or factor_division_cambia
                    or (payload.nombre is not None and payload.nombre != producto.nombre)
                    or (payload.se_vende_en_unidad_medida is not None and payload.se_vende_en_unidad_medida != producto.se_vende_en_unidad_medida)
                    or (payload.se_compra_en_unidad_medida is not None and payload.se_compra_en_unidad_medida != producto.se_pide_en_unidad_medida)
                ):
                    raise HttpError(403, "El verdulero no está autorizado a cambiar precio, ganancia, factor, nombre ni unidades de un producto asociado a un pedido diario. Contacte con el comprador o el administrador.")
                # Solo puede cambiar la imagen
        
        campos_actualizados = False
        # Si es verdulero y el producto está asociado a un pedido diario, sólo se permite cambiar la imagen
        puede_editar_campos = not (usuario.rol == 'verdulero' and 'asociado' in locals() and asociado)

        if puede_editar_campos:
            if payload.nombre is not None and payload.nombre != producto.nombre:
                producto.nombre = payload.nombre
                campos_actualizados = True
            if payload.se_vende_en_unidad_medida is not None and payload.se_vende_en_unidad_medida != producto.se_vende_en_unidad_medida:
                producto.se_vende_en_unidad_medida = payload.se_vende_en_unidad_medida
                campos_actualizados = True
            if payload.se_compra_en_unidad_medida is not None and payload.se_compra_en_unidad_medida != producto.se_pide_en_unidad_medida:
                producto.se_pide_en_unidad_medida = payload.se_compra_en_unidad_medida
                campos_actualizados = True
            if getattr(payload, 'factor_division', None) is not None and factor_division_cambia:
                producto.factor_division = payload.factor_division
                campos_actualizados = True
            if payload.precio_compra is not None and precio_compra_cambia:
                producto.precio_compra = payload.precio_compra
                campos_actualizados = True
            if payload.ganancia_porcentaje is not None and ganancia_cambia:
                producto.ganancia_porcentaje = payload.ganancia_porcentaje
                campos_actualizados = True
        if imagen is not None:
            # Eliminar imagen anterior
            delete_image_file(producto.imagen)
            # Comprimir a ~50KB y guardar nueva imagen
            imagen_comprimida = compress_image(imagen, max_size_kb=50)
            producto.imagen = imagen_comprimida
            campos_actualizados = True
        if campos_actualizados:
            producto.save()
        if usuario.rol == 'verdulero':
            return _ocultar_datos_compra_respuesta(producto)
        return producto
    except Exception as e:
        raise HttpError(400, f"Error al actualizar el producto: {str(e)}")

@router.delete("/eliminar/{producto_id}", auth=AuthBearer())
def eliminar_producto(request, producto_id: int):
    try:
        from pedido.models import PedidoProducto
        from core.utils.auth import get_current_usuario
        usuario = get_current_usuario(request)
        producto = get_object_or_404(Producto, id=producto_id)
        
        # Validar que el producto no esté en ningún pedido (excepto admin)
        if usuario.rol != 'admin' and PedidoProducto.objects.filter(producto=producto).exists():
            raise HttpError(400, "No se puede eliminar un producto que está asociado a pedidos")
        
        # Eliminar imagen asociada
        delete_image_file(producto.imagen)
        producto.delete()
        return {"mensaje": "Producto eliminado correctamente"}
    except Exception as e:
        raise HttpError(400, f"Error al eliminar el producto: {str(e)}")

