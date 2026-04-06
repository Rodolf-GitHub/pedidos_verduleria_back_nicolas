from ninja import Router
from .schemas import PedidoProductoSchema, PedidoCreateSchema, PedidoSchema, PedidoSimpleSchema, AgregarProductoPedidoSchema, EliminarProductoPedidoSchema, ActualizarProductoPedidoSchema, PedidoUpdateSchema, PedidoActualizarFechaSchema
from .models import Pedido, PedidoProducto
from core.utils.auth import get_current_usuario
from usuarios.auth import AuthBearer, require_comprador,require_verdulero,require_admin
from django.shortcuts import get_object_or_404
from ninja.errors import HttpError
from typing import List
from ninja.pagination import paginate
from core.utils.search_filter import search_filter
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q, Count

router = Router(tags=["Pedidos"])

@router.get("/listar", response=List[PedidoSimpleSchema], auth=AuthBearer())
@paginate
@search_filter(['negocio__nombre', 'fecha_creacion', 'estado'])
def listar_pedidos(request):
    usuario = get_current_usuario(request)
    if usuario.rol == 'admin':
        # Admin: todos los pedidos
        pedidos = Pedido.objects.annotate(
            cantidad_productos=Count('pedidoproducto')
        ).order_by('-fecha_creacion')
    elif usuario.rol == 'comprador':
        # Comprador: sus propios pedidos + pedidos completados de sus negocios
        pedidos = Pedido.objects.filter(
            Q(creado_por=usuario) | Q(negocio__in=usuario.negocios.all(), estado='completado')
        ).annotate(
            cantidad_productos=Count('pedidoproducto')
        ).order_by('-fecha_creacion')
    else:
        # Verdulero: sus propios pedidos + pedidos completados de sus negocios
        pedidos = Pedido.objects.filter(
            Q(creado_por=usuario) | Q(negocio__in=usuario.negocios.all(), estado='completado')
        ).annotate(
            cantidad_productos=Count('pedidoproducto')
        ).order_by('-fecha_creacion')
    return pedidos

@router.get("/listar_pedidos_completados", response=List[PedidoSchema], auth=AuthBearer(), operation_id="pedido_api_listar_pedidos_completados")
@require_comprador
@paginate
@search_filter(['negocio__nombre', 'fecha_creacion'])
def listar_pedidos(request):
    usuario = get_current_usuario(request)
    if usuario.rol == 'admin':
        pedidos = Pedido.objects.filter(estado='completado').order_by('-fecha_creacion')
    else:
        pedidos = Pedido.objects.filter(
            estado='completado'
        ).filter(
            negocio__in=usuario.negocios.all()
        ).order_by('-fecha_creacion')
    return pedidos

@router.get("/listar_pedidos_completados_sin_compra_asociada", response=List[PedidoSchema], auth=AuthBearer())
@require_comprador
@paginate
@search_filter(['negocio__nombre', 'fecha_creacion'])
def listar_pedidos_completados_sin_compra(request):
    from compra.models import Compra
    usuario = get_current_usuario(request)
    
    # Obtener IDs de pedidos que ya tienen compra asociada
    pedidos_con_compra = Compra.objects.values_list('en_respuesta_a_pedido_id', flat=True).distinct()
    
    if usuario.rol == 'admin':
        pedidos = Pedido.objects.filter(
            estado='completado'
        ).exclude(
            id__in=pedidos_con_compra
        ).order_by('-fecha_creacion')
    else:
        pedidos = Pedido.objects.filter(
            estado='completado',
            negocio__in=usuario.negocios.all()
        ).exclude(
            id__in=pedidos_con_compra
        ).order_by('-fecha_creacion')
    return pedidos

@router.get("/obtener/{pedido_id}", response=PedidoSchema, auth=AuthBearer())
def obtener_pedido(request, pedido_id: int):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    return pedido

@router.get("/mis_pedidos", response=List[PedidoSchema], auth=AuthBearer())
@require_verdulero
@paginate
@search_filter(['negocio__nombre', 'fecha_creacion'])
def listar_mis_pedidos(request):
    usuario = get_current_usuario(request)
    pedidos = Pedido.objects.filter(creado_por=usuario).order_by('-fecha_creacion')
    return pedidos



@router.post("/crear", response=PedidoSchema, auth=AuthBearer())
@require_verdulero
def crear_pedido(request, payload: PedidoCreateSchema):
    usuario = get_current_usuario(request)
    # Eliminar pedidos con más de 100 días de antigüedad (de cualquier negocio)
    corte = timezone.now() - timedelta(days=100)
    Pedido.objects.filter(fecha_creacion__lt=corte).delete()
    
    # Validar que no exista otro pedido sin completar en el mismo negocio
    pedido_sin_completar = Pedido.objects.filter(
        negocio_id=payload.negocio_id,
        estado='en_proceso'
    ).exists()
    if pedido_sin_completar:
        raise HttpError(400, "Ya existe un pedido sin completar para este negocio")
    
    pedido = Pedido(creado_por=usuario, negocio_id=payload.negocio_id, estado='en_proceso')
    pedido.save()
    return pedido

@router.post("/agregar_producto/{pedido_id}", response=PedidoProductoSchema, auth=AuthBearer())
@require_verdulero
def agregar_producto_a_pedido(request, pedido_id: int, payload: AgregarProductoPedidoSchema):
    usuario = get_current_usuario(request)
    pedido = get_object_or_404(Pedido, id=pedido_id)
    
    # Validar que sea el propietario o admin
    if usuario.rol != 'admin' and pedido.creado_por != usuario:
        raise HttpError(403, "No tienes permisos para modificar este pedido")
    
    # Validar que el pedido no esté completado
    if pedido.estado == 'completado':
        raise HttpError(400, "No se puede agregar productos a un pedido completado")
    
    # Validar que no tenga compra asociada
    from compra.models import Compra
    if Compra.objects.filter(en_respuesta_a_pedido=pedido).exists():
        raise HttpError(400, "No se puede modificar un pedido con compra asociada")
    
    # Validar que el producto no exista ya en el pedido
    if PedidoProducto.objects.filter(pedido=pedido, producto_id=payload.producto_id).exists():
        raise HttpError(400, "Este producto ya está en el pedido")
    
    # Usar la unidad de medida solicitada en el payload; si no viene, usar la del producto
    unidad_medida = payload.unidad_medida
    if unidad_medida is None:
        from producto.models import Producto
        prod = get_object_or_404(Producto, id=payload.producto_id)
        unidad_medida = prod.se_pide_en_unidad_medida

    pedido_producto = PedidoProducto.objects.create(
        pedido=pedido,
        producto_id=payload.producto_id,
        cantidad=payload.cantidad,
        unidad_medida=unidad_medida,
    )
    return pedido_producto

@router.delete("/eliminar_producto/{pedido_id}", auth=AuthBearer())
@require_verdulero
def eliminar_producto_de_pedido(request, pedido_id: int, payload: EliminarProductoPedidoSchema):
    usuario = get_current_usuario(request)
    pedido = get_object_or_404(Pedido, id=pedido_id)
    
    # Validar que sea el propietario o admin
    if usuario.rol != 'admin' and pedido.creado_por != usuario:
        raise HttpError(403, "No tienes permisos para modificar este pedido")
    
    # Validar que el pedido no esté completado
    if pedido.estado == 'completado':
        raise HttpError(400, "No se puede eliminar productos de un pedido completado")
    
    # Validar que no tenga compra asociada
    from compra.models import Compra
    if Compra.objects.filter(en_respuesta_a_pedido=pedido).exists():
        raise HttpError(400, "No se puede modificar un pedido con compra asociada")
    
    pedido_producto = get_object_or_404(PedidoProducto, pedido=pedido, producto_id=payload.producto_id)
    pedido_producto.delete()
    return {"message": "Producto eliminado del pedido"}

@router.put("/actualizar_producto/{pedido_id}", response=PedidoProductoSchema, auth=AuthBearer())
@require_verdulero
def actualizar_producto_en_pedido(request, pedido_id: int, payload: ActualizarProductoPedidoSchema):
    usuario = get_current_usuario(request)
    pedido = get_object_or_404(Pedido, id=pedido_id)
    
    # Validar que sea el propietario o admin
    if usuario.rol != 'admin' and pedido.creado_por != usuario:
        raise HttpError(403, "No tienes permisos para modificar este pedido")
    
    # Validar que el pedido no esté completado
    if pedido.estado == 'completado':
        raise HttpError(400, "No se puede actualizar productos de un pedido completado")
    
    # Validar que no tenga compra asociada
    from compra.models import Compra
    if Compra.objects.filter(en_respuesta_a_pedido=pedido).exists():
        raise HttpError(400, "No se puede modificar un pedido con compra asociada")
    
    pedido_producto = get_object_or_404(PedidoProducto, pedido=pedido, producto_id=payload.producto_id)
    if payload.cantidad is not None:
        pedido_producto.cantidad = payload.cantidad
    if payload.unidad_medida is not None:
        pedido_producto.unidad_medida = payload.unidad_medida
    pedido_producto.save()
    return pedido_producto

@router.put("/cambiar_estado/{pedido_id}", response=PedidoSchema, auth=AuthBearer())
@require_verdulero
def cambiar_estado_pedido(request, pedido_id: int, payload: PedidoUpdateSchema):
    usuario = get_current_usuario(request)
    pedido = get_object_or_404(Pedido, id=pedido_id)
    
    # Validar que sea el propietario o admin
    if usuario.rol != 'admin' and pedido.creado_por != usuario:
        raise HttpError(403, "No tienes permisos para modificar este pedido")
    
    # Validar que no tenga compra asociada
    from compra.models import Compra
    if Compra.objects.filter(en_respuesta_a_pedido=pedido).exists():
        raise HttpError(400, "No se puede modificar un pedido con compra asociada")
    
    # Validar que no se reabra un pedido con pedido diario completado
    if payload.estado == 'en_proceso' and pedido.estado == 'completado':
        from pedido_diario.models import PedidoDiario
        fecha_obj = timezone.localtime(pedido.fecha_creacion).date()
        pedido_diario = PedidoDiario.objects.filter(fecha=fecha_obj).first()
        if pedido_diario and pedido_diario.estado == 'completado':
            raise HttpError(400, "No se puede reabrir un pedido con pedido diario completado")
    
    # Validar que tenga productos para ser completado
    if payload.estado == 'completado':
        if not PedidoProducto.objects.filter(pedido=pedido).exists():
            raise HttpError(400, "El pedido debe tener al menos un producto para ser completado")
    
    if payload.estado is not None:
        pedido.estado = payload.estado
    pedido.save()
    return pedido

@router.delete("/eliminar/{pedido_id}", auth=AuthBearer())
@require_verdulero
def eliminar_pedido(request, pedido_id: int):
    usuario = get_current_usuario(request)
    pedido = get_object_or_404(Pedido, id=pedido_id)
    
    # Validar que sea el propietario, comprador o admin
    if usuario.rol not in ['admin', 'comprador'] and pedido.creado_por != usuario:
        raise HttpError(403, "No tienes permisos para eliminar este pedido")
    
    # Validar que el pedido esté abierto (en_proceso)
    if pedido.estado != 'en_proceso':
        raise HttpError(400, "Solo se pueden eliminar pedidos en estado abierto")
    
    # Validar que no tenga compra asociada
    from compra.models import Compra
    if Compra.objects.filter(en_respuesta_a_pedido=pedido).exists():
        raise HttpError(400, "No se puede eliminar un pedido con compra asociada")
    
    pedido.delete()
    return {"message": "Pedido eliminado correctamente"}

@router.put("/cambiar_fecha/{pedido_id}", response=PedidoSchema, auth=AuthBearer())
@require_verdulero
def cambiar_fecha_pedido(request, pedido_id: int, payload: PedidoActualizarFechaSchema):
    usuario = get_current_usuario(request)
    pedido = get_object_or_404(Pedido, id=pedido_id)
    
    # Validar que sea el propietario o admin
    if usuario.rol != 'admin' and pedido.creado_por != usuario:
        raise HttpError(403, "No tienes permisos para modificar este pedido")

    if pedido.estado != 'en_proceso':
        raise HttpError(400, "Solo se puede cambiar la fecha de pedidos abiertos")
    
    pedido.fecha_creacion = payload.fecha_creacion
    pedido.save()
    return pedido