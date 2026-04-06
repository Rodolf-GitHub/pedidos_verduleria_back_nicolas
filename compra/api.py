from ninja import Router
from compra.schemas import CompraSchema, CompraCreateSchema, CompraUpdateSchema, AgregarProductoCompraSchema, EliminarProductoCompraSchema, ActualizarProductoCompraSchema, CompraProductoSchema
from compra.models import Compra, CompraProducto
from ninja.pagination import paginate
from core.utils.auth import get_current_usuario
from usuarios.auth import AuthBearer, require_verdulero, require_comprador
from django.shortcuts import get_object_or_404
from core.utils.search_filter import search_filter
from django.utils import timezone
from datetime import timedelta
from ninja.errors import HttpError

router = Router(tags=["Compras"])
@router.get("/listar_compras", response=list[CompraSchema], auth=AuthBearer())
@paginate
@search_filter(['negocio__nombre', 'fecha_creacion', 'estado'])
def listar_compras(request):
    usuario = get_current_usuario(request)
    if usuario.rol == 'admin':
        compras = Compra.objects.all()
    elif usuario.rol == 'verdulero':
        compras = Compra.objects.filter(negocio__in=usuario.negocios.all(), estado='completado')
    else:
        compras = Compra.objects.filter(creado_por=usuario)
    return compras

@router.get("/obtener/{compra_id}", response=CompraSchema, auth=AuthBearer())
def obtener_compra(request, compra_id: int):
    compra = get_object_or_404(Compra, id=compra_id)
    return compra

@router.get("/obtener_pedido_asociado/{pedido_id}", response=CompraSchema, auth=AuthBearer())
def obtener_compra_asociada(request, pedido_id: int):
    compra = get_object_or_404(Compra, en_respuesta_a_pedido_id=pedido_id)
    return compra

@router.post("/crear", response=CompraSchema, auth=AuthBearer())
@require_comprador
def crear_compra(request, payload: CompraCreateSchema):
    from pedido.models import Pedido
    usuario = get_current_usuario(request)
    
    # Obtener el pedido
    pedido = get_object_or_404(Pedido, id=payload.en_respuesta_a_pedido_id)
    
    # Validar que no exista compra sin completar en el mismo negocio
    compra_sin_completar = Compra.objects.filter(
        negocio=pedido.negocio,
        estado='en_proceso'
    ).exists()
    if compra_sin_completar:
        raise HttpError(400, "Ya existe una compra sin completar para este negocio")
    
    # Validar que no exista compra para este pedido
    compra_existente = Compra.objects.filter(en_respuesta_a_pedido=pedido).exists()
    if compra_existente:
        raise HttpError(400, "Ya existe una compra para este pedido")
    
    # Crear la compra SIN copiar productos
    compra = Compra(
        creado_por=usuario,
        negocio=pedido.negocio,
        en_respuesta_a_pedido=pedido,
        estado='en_proceso'
    )
    compra.save()
    
    return compra

@router.post("/agregar_producto/{compra_id}", response=CompraProductoSchema, auth=AuthBearer())
@require_comprador
def agregar_producto_a_compra(request, compra_id: int, payload: AgregarProductoCompraSchema):
    from pedido.models import PedidoProducto
    compra = get_object_or_404(Compra, id=compra_id)
    usuario = get_current_usuario(request)
    
    # Validar que sea el propietario o admin
    if usuario.rol != 'admin' and compra.creado_por != usuario:
        raise HttpError(403, "No tienes permisos para modificar esta compra")
    
    # Validar que la compra no esté completada
    if compra.estado == 'completado':
        raise HttpError(400, "No se puede agregar productos a una compra completada")
    
    # Validar que no exista una compra posterior en el mismo negocio (excepto admin)
    if usuario.rol != 'admin':
        compra_posterior = Compra.objects.filter(
            negocio=compra.negocio,
            fecha_creacion__gt=compra.fecha_creacion
        ).exists()
        if compra_posterior:
            raise HttpError(400, "No se puede modificar una compra si existe una compra posterior en el mismo negocio")
    
    # Obtener pedido_producto si se proporciona
    pedido_producto = None
    producto_id = payload.producto_id
    if payload.pedido_producto_id:
        pedido_producto = get_object_or_404(PedidoProducto, id=payload.pedido_producto_id)
        if pedido_producto.pedido_id != compra.en_respuesta_a_pedido_id:
            return {"error": "El producto del pedido no pertenece a este pedido"}
        producto_id = pedido_producto.producto_id

    # Validar que el producto exista
    from producto.models import Producto
    if not Producto.objects.filter(id=producto_id).exists():
        return {"error": "Producto inválido"}
    
    compra_producto, created = CompraProducto.objects.get_or_create(
        compra=compra,
        producto_id=producto_id,
        pedido_producto=pedido_producto,
        defaults={
            'cantidad': payload.cantidad or 1.0,  # Usar 1.0 como valor por defecto si viene None
            'unidad_medida': payload.unidad_medida,
            'precio_de_compra': payload.precio_de_compra,
            'ganancia_deseada': payload.ganancia_deseada,
            'estado_compra': payload.estado_compra,
            'motivo_no_compra': payload.motivo_no_compra
        }
    )
    if not created:
        compra_producto.cantidad = (compra_producto.cantidad or 0) + (payload.cantidad or 1.0)  # Usar 1.0 como valor por defecto si viene None
        compra_producto.unidad_medida = payload.unidad_medida
        compra_producto.precio_de_compra = payload.precio_de_compra
        compra_producto.ganancia_deseada = payload.ganancia_deseada
        compra_producto.estado_compra = payload.estado_compra
        compra_producto.motivo_no_compra = payload.motivo_no_compra
        compra_producto.save()
    return compra_producto

@router.put("/actualizar_producto/{compra_id}", response=CompraProductoSchema, auth=AuthBearer())
@require_comprador
def actualizar_producto_de_compra(request, compra_id: int, payload: ActualizarProductoCompraSchema):
    compra = get_object_or_404(Compra, id=compra_id)
    usuario = get_current_usuario(request)
    
    # Validar que sea el propietario o admin
    if usuario.rol != 'admin' and compra.creado_por != usuario:
        raise HttpError(403, "No tienes permisos para modificar esta compra")
    
    # Validar que la compra no esté completada
    if compra.estado == 'completado':
        raise HttpError(400, "No se puede actualizar productos de una compra completada")
    
    # Validar que no exista una compra posterior en el mismo negocio (excepto admin)
    if usuario.rol != 'admin':
        compra_posterior = Compra.objects.filter(
            negocio=compra.negocio,
            fecha_creacion__gt=compra.fecha_creacion
        ).exists()
        if compra_posterior:
            raise HttpError(400, "No se puede modificar una compra si existe una compra posterior en el mismo negocio")
    
    try:
        compra_producto = CompraProducto.objects.get(compra=compra, producto_id=payload.producto_id)
        if payload.cantidad is not None:
            compra_producto.cantidad = payload.cantidad
        if payload.unidad_medida is not None:
            compra_producto.unidad_medida = payload.unidad_medida
        if payload.precio_de_compra is not None:
            compra_producto.precio_de_compra = payload.precio_de_compra
        if payload.ganancia_deseada is not None:
            compra_producto.ganancia_deseada = payload.ganancia_deseada
        if payload.estado_compra is not None:
            compra_producto.estado_compra = payload.estado_compra
        if payload.motivo_no_compra is not None:
            compra_producto.motivo_no_compra = payload.motivo_no_compra
        compra_producto.save()
        return compra_producto
    except CompraProducto.DoesNotExist:
        raise HttpError(404, "El producto no está en la compra")

@router.put("/cambiar_estado/{compra_id}", response=CompraSchema, auth=AuthBearer())
@require_comprador
def cambiar_estado_compra(request, compra_id: int, payload: CompraUpdateSchema):
    from pedido.models import PedidoProducto
    compra = get_object_or_404(Compra, id=compra_id)
    usuario = get_current_usuario(request)
    # Validar que no haya pasado más de un día (excepto admin)
    if usuario.rol != 'admin':
        tiempo_transcurrido = timezone.now() - compra.fecha_creacion
        if tiempo_transcurrido > timedelta(days=1):
            raise HttpError(403, "No se puede modificar una compra después de un día")
    
    if payload.estado == 'completado':
        # Validar que todos los productos del pedido tengan un CompraProducto
        productos_pedido = PedidoProducto.objects.filter(pedido=compra.en_respuesta_a_pedido)
        for prod_pedido in productos_pedido:
            compra_prod = CompraProducto.objects.filter(
                compra=compra,
                producto=prod_pedido.producto
            ).first()
            
            if not compra_prod:
                raise HttpError(400, f"Producto {prod_pedido.producto.nombre} no tiene justificación (comprado o rechazado)")
            
            if compra_prod.estado_compra == 'no_comprado' and not compra_prod.motivo_no_compra:
                raise HttpError(400, f"Producto {prod_pedido.producto.nombre} marcado como no comprado pero sin motivo")
    
    if payload.estado is not None:
        compra.estado = payload.estado
    compra.save()
    return compra

@router.delete("/eliminar_producto/{compra_id}", auth=AuthBearer())
@require_comprador
def eliminar_producto_de_compra(request, compra_id: int, payload: EliminarProductoCompraSchema):
    compra = get_object_or_404(Compra, id=compra_id)
    usuario = get_current_usuario(request)
    
    # Validar que sea el propietario o admin
    if usuario.rol != 'admin' and compra.creado_por != usuario:
        raise HttpError(403, "No tienes permisos para modificar esta compra")
    
    # Validar que no exista una compra posterior en el mismo negocio (excepto admin)
    if usuario.rol != 'admin':
        compra_posterior = Compra.objects.filter(
            negocio=compra.negocio,
            fecha_creacion__gt=compra.fecha_creacion
        ).exists()
        if compra_posterior:
            raise HttpError(400, "No se puede modificar una compra si existe una compra posterior en el mismo negocio")
    
    try:
        compra_producto = CompraProducto.objects.get(compra=compra, producto_id=payload.producto_id)
        compra_producto.delete()
        return {"message": "Producto eliminado de la compra"}
    except CompraProducto.DoesNotExist:
        return {"error": "El producto no está en la compra"}

@router.delete("/eliminar/{compra_id}", auth=AuthBearer())
@require_comprador
def eliminar_compra(request, compra_id: int):
    compra = get_object_or_404(Compra, id=compra_id)
    usuario = get_current_usuario(request)
    
    # Validar que sea el propietario o admin
    if usuario.rol != 'admin' and compra.creado_por != usuario:
        raise HttpError(403, "No tienes permisos para eliminar esta compra")
    
    # Validar que no exista una compra posterior en el mismo negocio (excepto admin)
    if usuario.rol != 'admin':
        compra_posterior = Compra.objects.filter(
            negocio=compra.negocio,
            fecha_creacion__gt=compra.fecha_creacion
        ).exists()
        if compra_posterior:
            raise HttpError(400, "No se puede eliminar una compra si existe una compra posterior en el mismo negocio")
    
    compra.delete()
    return {"message": "Compra eliminada"}