from ninja import Router
from .schemas import NegocioSchema, NegocioCreateSchema, NegocioUpdateSchema
from .models import Negocio
from ninja.errors import HttpError
from ninja.pagination import paginate
from django.shortcuts import get_object_or_404
from core.utils.search_filter import search_filter
from usuarios.auth import AuthBearer, require_admin

router = Router(tags=["Negocios"])
@router.get("/listar", response=list[NegocioSchema], auth=AuthBearer())
@paginate
@search_filter(['nombre', 'direccion'])
def listar_negocios(request):
    usuario = request.auth
    if usuario.rol == 'admin':
        negocios = Negocio.objects.all()
    else:
        negocios = usuario.negocios
    return negocios

@router.post("/crear", response=NegocioSchema, auth=AuthBearer())
@require_admin
def crear_negocio(request, payload: NegocioCreateSchema):
    try:
        # Restricción: no permitir crear más de 10 negocios
        total_negocios = Negocio.objects.count()
        if total_negocios >= 10:
            raise HttpError(400, "Límite de negocios alcanzado (10). No se puede crear un nuevo negocio.")
        negocio = Negocio(
            nombre=payload.nombre,
            direccion=payload.direccion
        )
        negocio.save()
        return negocio
    except Exception as e:
        raise HttpError(400, f"Error al crear el negocio: {str(e)}")

@router.put("/actualizar/{negocio_id}", response=NegocioSchema, auth=AuthBearer())
@require_admin
def actualizar_negocio(request, negocio_id: int, payload: NegocioUpdateSchema):
    try:
        negocio = get_object_or_404(Negocio, id=negocio_id)
        if payload.nombre is not None:
            negocio.nombre = payload.nombre
        if payload.direccion is not None:
            negocio.direccion = payload.direccion
        negocio.save()
        return negocio
    except Exception as e:
        raise HttpError(400, f"Error al actualizar el negocio: {str(e)}")

@router.delete("/eliminar/{negocio_id}", auth=AuthBearer())
@require_admin
def eliminar_negocio(request, negocio_id: int):
    try:
        negocio = get_object_or_404(Negocio, id=negocio_id)
        negocio.delete()
        return {"mensaje": "Negocio eliminado correctamente"}
    except Exception as e:
        raise HttpError(400, f"Error al eliminar el negocio: {str(e)}")
