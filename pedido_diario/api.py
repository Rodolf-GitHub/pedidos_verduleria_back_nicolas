from datetime import date, datetime, timedelta

from django.db.models import Sum
from django.utils import timezone
from ninja import Router
from ninja.errors import HttpError

from core.utils.auth import get_current_usuario
from pedido.models import Pedido, PedidoProducto
from producto.models import Producto
from producto.schemas import ProductoSchema
from usuarios.auth import AuthBearer, require_comprador, require_verdulero
from .models import PedidoDiario, PedidoDiarioItem
from .schemas import (
    PedidoDiarioSchema,
    PedidoDiarioProductoSchema,
    PedidoDiarioUnidadSchema,
    PedidoDiarioCantidadNegocioSchema,
    PedidoDiarioTotalPorUnidadSchema,
    PedidoDiarioEstadoUpdateSchema,
    PedidoDiarioUpdateSchema,
    PedidosSinCompletarSchema
)


router = Router(tags=["Pedidos diarios"])


@router.get("/por_fecha", response=PedidoDiarioSchema, auth=AuthBearer())
@require_comprador
def obtener_pedido_diario_por_fecha(request, fecha: str):
    try:
        fecha_obj = date.fromisoformat(fecha)
    except ValueError as exc:
        raise HttpError(400, "Fecha invalida. Usa YYYY-MM-DD") from exc

    usuario = get_current_usuario(request)

    pedidos = Pedido.objects.filter(
        fecha_creacion__date=fecha_obj,
        estado="completado",
    )
    if usuario.rol != "admin":
        pedidos = pedidos.filter(negocio__in=usuario.negocios.all())

    agregados = (
        PedidoProducto.objects.filter(pedido__in=pedidos)
        .values("producto_id", "pedido__negocio_id", "pedido__negocio__nombre", "unidad_medida")
        .annotate(cantidad_total=Sum("cantidad"))
        .order_by("producto_id")
    )

    producto_ids = {row["producto_id"] for row in agregados}
    productos = Producto.objects.filter(id__in=producto_ids).order_by("-ultima_actualizacion")

    estado_items = PedidoDiarioItem.objects.filter(pedido_diario__fecha=fecha_obj)
    estado_map = {item.producto_id: item for item in estado_items.select_related("producto")}

    pedido_diario = PedidoDiario.objects.filter(fecha=fecha_obj).first()

    # Si existe un pedido_diario muy antiguo (>100 días), eliminarlo y tratarlo como inexistente
    if pedido_diario:
        hoy = timezone.localtime(timezone.now()).date()
        edad = (hoy - pedido_diario.fecha).days
        if edad > 100:
            pedido_diario.delete()
            pedido_diario = None

    # Agrupar por producto: cantidades por negocio y totales por unidad
    detalle_por_producto = {}
    totales_por_producto = {}
    for row in agregados:
        pid = row["producto_id"]
        detalle_por_producto.setdefault(pid, []).append(
            PedidoDiarioCantidadNegocioSchema(
                negocio_id=row["pedido__negocio_id"],
                negocio_nombre=row.get("pedido__negocio__nombre", ""),
                cantidad=float(row["cantidad_total"] or 0),
                unidad_medida=row.get("unidad_medida"),
            )
        )
        unidad_clave = row.get("unidad_medida")
        totales_por_producto.setdefault(pid, {}).setdefault(unidad_clave, 0.0)
        totales_por_producto[pid][unidad_clave] += float(row["cantidad_total"] or 0)

    items = []
    for producto in productos:
        producto_id = producto.id
        estado_item = estado_map.get(producto_id)
        detalles = detalle_por_producto.get(producto_id, [])
        totales_unidad = [
            PedidoDiarioTotalPorUnidadSchema(unidad_medida=unidad, cantidad_total=qty)
            for unidad, qty in totales_por_producto.get(producto_id, {}).items()
        ]
        items.append(PedidoDiarioProductoSchema(
            producto=ProductoSchema.from_orm(producto),
            cantidades_por_negocio=detalles,
            total=PedidoDiarioUnidadSchema(
                unidad_pedido=getattr(producto, "se_pide_en_unidad_medida", None),
                totales_por_unidad=totales_unidad,
                estado_compra=estado_item.estado_compra if estado_item else None,
                motivo_no_compra=estado_item.motivo_no_compra if estado_item else None,
                precio_compra=float(estado_item.precio_compra) if estado_item and hasattr(estado_item, 'precio_compra') and estado_item.precio_compra is not None else None,
                factor_division=float(estado_item.factor_division) if estado_item and hasattr(estado_item, 'factor_division') and estado_item.factor_division is not None else None,
                ganancia_aplicada=float(estado_item.ganancia_aplicada) if estado_item and hasattr(estado_item, 'ganancia_aplicada') and estado_item.ganancia_aplicada is not None else None,
            )
        ))

    def calcular_precio_venta(precio_compra, factor_division, ganancia):
        if ganancia is None:
            return None
        try:
            compra = float(precio_compra) if precio_compra is not None else 0.0
            factor = float(factor_division) if factor_division not in (None, 0) else 1.0
            precio = (compra / factor) * (1 + float(ganancia) / 100)
            decena = int(precio // 10) * 10
            if precio > decena + 9:
                decena += 10
            return float(decena + 9)
        except Exception:
            return None

    for item in items:
        factor_division_valor = item.total.factor_division if item.total.factor_division is not None else item.producto.factor_division
        ganancia_valor = item.total.ganancia_aplicada if item.total.ganancia_aplicada is not None else item.producto.ganancia_porcentaje
        precio_compra_valor = item.total.precio_compra if item.total.precio_compra is not None else item.producto.precio_compra

        item.producto.factor_division = factor_division_valor
        item.producto.ganancia_porcentaje = ganancia_valor
        item.producto.precio_venta = calcular_precio_venta(
            precio_compra_valor,
            factor_division_valor,
            ganancia_valor,
        )

    return PedidoDiarioSchema(
        fecha=fecha_obj.isoformat(),
        estado=pedido_diario.estado if pedido_diario else None,
        items=items,
    )


@router.put("/marcar", auth=AuthBearer())
@require_comprador
def marcar_pedido_diario(request, fecha: str, payload: PedidoDiarioEstadoUpdateSchema):
    try:
        fecha_obj = date.fromisoformat(fecha)
    except ValueError as exc:
        raise HttpError(400, "Fecha invalida. Usa YYYY-MM-DD") from exc

    usuario = get_current_usuario(request)

    pedido_diario, _ = PedidoDiario.objects.get_or_create(
        fecha=fecha_obj,
        defaults={"creado_por": usuario},
    )

    # Validar que el pedido diario no esté completado
    if pedido_diario.estado == "completado":
        raise HttpError(400, "No se pueden modificar items de un pedido diario completado")

    defaults = {"estado_compra": payload.estado_compra}
    if payload.motivo_no_compra is not None:
        defaults["motivo_no_compra"] = payload.motivo_no_compra

    item, _ = PedidoDiarioItem.objects.get_or_create(
        pedido_diario=pedido_diario,
        producto_id=payload.producto_id,
        defaults=defaults,
    )

    item.estado_compra = payload.estado_compra
    if payload.motivo_no_compra is not None:
        item.motivo_no_compra = payload.motivo_no_compra

    # Guardar valores de producto ese día en el item, solo si la diferencia es relevante (>= 0.01)
    def cambio_relevante(actual, nuevo):
        try:
            if actual is None:
                return True
            return abs(float(actual) - float(nuevo)) >= 0.01
        except Exception:
            return True

    producto = item.producto
    if payload.precio_compra is not None and cambio_relevante(producto.precio_compra, payload.precio_compra):
        item.precio_compra = payload.precio_compra
    else:
        item.precio_compra = producto.precio_compra
    if payload.factor_division is not None and cambio_relevante(producto.factor_division, payload.factor_division):
        item.factor_division = payload.factor_division
    else:
        item.factor_division = producto.factor_division
    if payload.ganancia_aplicada is not None and cambio_relevante(producto.ganancia_porcentaje, payload.ganancia_aplicada):
        item.ganancia_aplicada = payload.ganancia_aplicada
    else:
        item.ganancia_aplicada = producto.ganancia_porcentaje
    item.save()

    # Si vienen datos de producto, actualizarlos
    if any([
        payload.precio_compra is not None,
        payload.factor_division is not None,
        payload.ganancia_aplicada is not None
    ]):
        cambios = False
        if payload.precio_compra is not None and cambio_relevante(producto.precio_compra, payload.precio_compra):
            producto.precio_compra = payload.precio_compra
            cambios = True
        if payload.factor_division is not None and cambio_relevante(producto.factor_division, payload.factor_division):
            producto.factor_division = payload.factor_division
            cambios = True
        if payload.ganancia_aplicada is not None and cambio_relevante(producto.ganancia_porcentaje, payload.ganancia_aplicada):
            producto.ganancia_porcentaje = payload.ganancia_aplicada
            cambios = True
        if cambios:
            producto.save()

    return {"message": "Estado actualizado"}


@router.delete("/desmarcar", auth=AuthBearer())
@require_comprador
def desmarcar_pedido_diario(request, fecha: str, payload: PedidoDiarioEstadoUpdateSchema):
    try:
        fecha_obj = date.fromisoformat(fecha)
    except ValueError as exc:
        raise HttpError(400, "Fecha invalida. Usa YYYY-MM-DD") from exc

    pedido_diario = PedidoDiario.objects.filter(fecha=fecha_obj).first()
    if not pedido_diario:
        return {"message": "Nada para desmarcar"}

    # Validar que el pedido diario no esté completado
    if pedido_diario.estado == "completado":
        raise HttpError(400, "No se pueden modificar items de un pedido diario completado")

    eliminado, _ = PedidoDiarioItem.objects.filter(
        pedido_diario=pedido_diario,
        producto_id=payload.producto_id,
    ).delete()

    if eliminado == 0:
        return {"message": "Nada para desmarcar"}

    return {"message": "Estado eliminado"}


@router.put("/cambiar_estado", auth=AuthBearer())
@require_comprador
def cambiar_estado_pedido_diario(request, fecha: str, payload: PedidoDiarioUpdateSchema):
    try:
        fecha_obj = date.fromisoformat(fecha)
    except ValueError as exc:
        raise HttpError(400, "Fecha invalida. Usa YYYY-MM-DD") from exc

    usuario = get_current_usuario(request)

    pedido_diario, _ = PedidoDiario.objects.get_or_create(
        fecha=fecha_obj,
        defaults={"creado_por": usuario},
    )

    if payload.estado == "completado":
        pedidos = Pedido.objects.filter(
            fecha_creacion__date=fecha_obj,
            estado="completado",
        )
        if usuario.rol != "admin":
            pedidos = pedidos.filter(negocio__in=usuario.negocios.all())

        agregados = (
            PedidoProducto.objects.filter(pedido__in=pedidos)
            .values("producto_id")
            .distinct()
        )

        if not agregados:
            raise HttpError(400, "No hay productos para completar")

        requerido = {row["producto_id"] for row in agregados}
        marcados = set(
            PedidoDiarioItem.objects.filter(pedido_diario=pedido_diario)
            .values_list("producto_id", flat=True)
        )

        faltantes = requerido - marcados
        if faltantes:
            raise HttpError(400, "Faltan productos por marcar como comprados/no comprados")

    pedido_diario.estado = payload.estado
    pedido_diario.save()

    return {"message": "Estado actualizado"}


@router.get("/por_pedido/{pedido_id}", response=PedidoDiarioSchema, auth=AuthBearer())
@require_verdulero
def obtener_pedido_diario_por_pedido(request, pedido_id: int):
    usuario = get_current_usuario(request)
    ocultar_datos_compra = usuario.rol == "verdulero"

    pedido = Pedido.objects.filter(id=pedido_id).first()
    if not pedido:
        raise HttpError(404, "Pedido no encontrado")

    if usuario.rol not in ["admin", "comprador"] and pedido.negocio not in usuario.negocios.all():
        raise HttpError(403, "No tienes permiso para ver este pedido")

    # Verificar si existe pedido diario para la fecha y si está completado
    fecha_obj = timezone.localtime(pedido.fecha_creacion).date()
    pedido_diario = PedidoDiario.objects.filter(fecha=fecha_obj).first()
    
    # Debe existir un pedido diario Y debe estar completado
    if not pedido_diario:
        raise HttpError(400, "No hay pedido diario para esta fecha")
    if pedido_diario.estado != 'completado':
        raise HttpError(400, "El pedido diario no está completado")

    agregados = (
        PedidoProducto.objects.filter(pedido=pedido)
        .values("producto_id", "pedido__negocio_id", "pedido__negocio__nombre", "unidad_medida")
        .annotate(cantidad_total=Sum("cantidad"))
        .order_by("producto_id")
    )

    producto_ids = {row["producto_id"] for row in agregados}
    productos = Producto.objects.filter(id__in=producto_ids).order_by("-ultima_actualizacion")

    fecha_obj = timezone.localtime(pedido.fecha_creacion).date()
    estado_items = PedidoDiarioItem.objects.filter(pedido_diario__fecha=fecha_obj)
    estado_map = {item.producto_id: item for item in estado_items.select_related("producto")}

    detalle_por_producto = {}
    totales_por_producto = {}
    for row in agregados:
        pid = row["producto_id"]
        detalle_por_producto.setdefault(pid, []).append(
            PedidoDiarioCantidadNegocioSchema(
                negocio_id=row["pedido__negocio_id"],
                negocio_nombre=row.get("pedido__negocio__nombre", ""),
                cantidad=float(row["cantidad_total"] or 0),
                unidad_medida=row.get("unidad_medida"),
            )
        )
        unidad_clave = row.get("unidad_medida")
        totales_por_producto.setdefault(pid, {}).setdefault(unidad_clave, 0.0)
        totales_por_producto[pid][unidad_clave] += float(row["cantidad_total"] or 0)

    items = []
    for producto in productos:
        producto_id = producto.id
        estado_item = estado_map.get(producto_id)
        detalles = detalle_por_producto.get(producto_id, [])
        totales_unidad = [
            PedidoDiarioTotalPorUnidadSchema(unidad_medida=unidad, cantidad_total=qty)
            for unidad, qty in totales_por_producto.get(producto_id, {}).items()
        ]
        items.append(PedidoDiarioProductoSchema(
            producto=ProductoSchema.from_orm(producto),
            cantidades_por_negocio=detalles,
            total=PedidoDiarioUnidadSchema(
                unidad_pedido=getattr(producto, "se_pide_en_unidad_medida", None),
                totales_por_unidad=totales_unidad,
                estado_compra=estado_item.estado_compra if estado_item else None,
                motivo_no_compra=estado_item.motivo_no_compra if estado_item else None,
                precio_compra=float(estado_item.precio_compra) if estado_item and estado_item.precio_compra is not None else (float(producto.precio_compra) if producto and producto.precio_compra is not None else None),
                factor_division=float(estado_item.factor_division) if estado_item and estado_item.factor_division is not None else (float(producto.factor_division) if producto and producto.factor_division is not None else None),
                ganancia_aplicada=float(estado_item.ganancia_aplicada) if estado_item and estado_item.ganancia_aplicada is not None else (float(producto.ganancia_porcentaje) if producto and producto.ganancia_porcentaje is not None else None),
            )
        ))

    pedido_diario = PedidoDiario.objects.filter(fecha=fecha_obj).first()

    def calcular_precio_venta(precio_compra, factor_division, ganancia):
        if ganancia is None:
            return None
        try:
            compra = float(precio_compra) if precio_compra is not None else 0.0
            factor = float(factor_division) if factor_division not in (None, 0) else 1.0
            precio = (compra / factor) * (1 + float(ganancia) / 100)
            decena = int(precio // 10) * 10
            if precio > decena + 9:
                decena += 10
            return float(decena + 9)
        except Exception:
            return None

    for item in items:
        item.producto.factor_division = item.total.factor_division
        item.producto.ganancia_porcentaje = item.total.ganancia_aplicada
        item.producto.precio_venta = calcular_precio_venta(
            item.total.precio_compra,
            item.total.factor_division,
            item.total.ganancia_aplicada,
        )
        if ocultar_datos_compra:
            item.producto.precio_compra_unitario = None
            item.producto.precio_compra = None
            item.producto.ganancia_porcentaje = None
            item.total.precio_compra = None
            item.total.ganancia_aplicada = None

    return PedidoDiarioSchema(
        fecha=fecha_obj.isoformat(),
        estado=pedido_diario.estado if pedido_diario else None,
        items=items,
    )


@router.get("/sin_completar", response=list[PedidosSinCompletarSchema], auth=AuthBearer())
@require_comprador
def obtener_pedidos_diarios_sin_completar(request):
    """Devuelve la lista de fechas que tienen pedidos (compras) y cuyo pedido diario
    no existe o no está marcado como 'completado'."""
    usuario = get_current_usuario(request)

    pedidos = Pedido.objects.filter(estado="completado")
    if usuario.rol != "admin":
        pedidos = pedidos.filter(negocio__in=usuario.negocios.all())

    # Obtener fechas únicas donde hay pedidos completados
    fechas = pedidos.values_list("fecha_creacion__date", flat=True).distinct()

    ahora = timezone.localtime(timezone.now())
    hoy = ahora.date()
    ayer = hoy - timedelta(days=1)

    resultado = []
    for fecha in fechas:
        pedido_diario = PedidoDiario.objects.filter(fecha=fecha).first()
        if pedido_diario and pedido_diario.estado == "completado":
            continue

        # Calcular urgencia según la regla:
        # - si es hoy -> 'sin_urgencia'
        # - si es ayer: tomar las 12:00 de esa fecha; si han pasado <6h -> 'a_tiempo', else 'pendiente'
        # - si es antier o más antiguo -> 'critico'
        if fecha == hoy:
            urgencia = "sin_urgencia"
        elif fecha == ayer:
            # tomar referencia como la medianoche de hoy (00:00 de hoy)
            today_midnight = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
            diferencia = ahora - today_midnight
            if diferencia <= timedelta(hours=6):
                urgencia = "a_tiempo"
            else:
                urgencia = "pendiente"
        else:
            urgencia = "critico"

        resultado.append(PedidosSinCompletarSchema(fecha=fecha.isoformat(), urgencia=urgencia))

    # Ordenar por fecha descendente (más reciente primero)
    resultado.sort(key=lambda x: x.fecha, reverse=True)

    return resultado
