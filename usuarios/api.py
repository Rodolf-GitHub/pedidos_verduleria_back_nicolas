from ninja import Router
from .schemas import UsuarioCreateSchema, UsuarioLoginSchema, TokenSchema, UsuarioSchema,UsuarioAsignarNegocioSchema,UsuarioQuitarNegocioSchema,UsuarioUpdateSchema, UsuarioCambiarContraseñaSchema
from .auth import AuthBearer, require_admin, require_verdulero, require_comprador
from .models import Usuario
from django.contrib.auth.hashers import make_password, check_password
import secrets
from core.utils.search_filter import search_filter
from ninja.pagination import paginate
from ninja.errors import HttpError

router = Router(tags=["Usuarios"])
@router.get("/listar", response=list[UsuarioSchema], auth=AuthBearer())
@require_admin
@paginate
@search_filter(['nombre', 'rol'])
def listar_usuarios(request, busqueda: str = None):
    usuarios = Usuario.objects.all()
    return usuarios

@router.get("/obtener/{usuario_id}", response=UsuarioSchema, auth=AuthBearer())
@require_admin
def obtener_usuario(request, usuario_id: int):
    try:
        usuario = Usuario.objects.get(id=usuario_id)
        return usuario
    except Usuario.DoesNotExist:
        return {"error": "Usuario no encontrado"}

@router.get("/me", response=UsuarioSchema, auth=AuthBearer())
def obtener_usuario_actual(request):
    return request.usuario

@router.post("/register", response=UsuarioSchema, auth=AuthBearer())
@require_admin
def register_usuario(request, payload: UsuarioCreateSchema):
    hashed_password = make_password(payload.contraseña)
    usuario = Usuario.objects.create(
        nombre=payload.nombre,
        contraseña_haseada=hashed_password,
        rol=payload.rol
    )
    return usuario

@router.post("/login", response=TokenSchema)
def login_usuario(request, payload: UsuarioLoginSchema):
    try:
        usuario = Usuario.objects.get(nombre=payload.nombre)
        if check_password(payload.contraseña, usuario.contraseña_haseada):
            token = secrets.token_hex(16)
            usuario.token = token
            usuario.save()
            return {"nombre": usuario.nombre, "rol": usuario.rol, "token": token}
        else:
            raise HttpError(400, "Credenciales inválidas")
    except Usuario.DoesNotExist:
        raise HttpError(400, "Credenciales inválidas")
    except Usuario.MultipleObjectsReturned:
        raise HttpError(500, "Error interno: múltiples usuarios con el mismo nombre")

@router.post("/asignar_negocio/{usuario_id}", response=UsuarioSchema, auth=AuthBearer())
@require_admin
def asignar_negocio_a_usuario(request, usuario_id: int, payload: UsuarioAsignarNegocioSchema):
    from .models import UsuarioNegocio
    from negocio.models import Negocio
    try:
        usuario = Usuario.objects.get(id=usuario_id)
        negocio = Negocio.objects.get(id=payload.negocio_id)
        UsuarioNegocio.objects.get_or_create(usuario=usuario, negocio=negocio)
        return usuario
    except Usuario.DoesNotExist:
        return {"error": "Usuario no encontrado"}
    except Negocio.DoesNotExist:
        return {"error": "Negocio no encontrado"}

@router.post("/quitar_negocio/{usuario_id}", response=UsuarioSchema, auth=AuthBearer())
@require_admin
def quitar_negocio_de_usuario(request, usuario_id: int, payload: UsuarioQuitarNegocioSchema):
    from .models import UsuarioNegocio
    from negocio.models import Negocio
    try:
        usuario = Usuario.objects.get(id=usuario_id)
        negocio = Negocio.objects.get(id=payload.negocio_id)
        relacion = UsuarioNegocio.objects.get(usuario=usuario, negocio=negocio)
        relacion.delete()
        return usuario
    except Usuario.DoesNotExist:
        return {"error": "Usuario no encontrado"}
    except Negocio.DoesNotExist:
        return {"error": "Negocio no encontrado"}
    except UsuarioNegocio.DoesNotExist:
        return {"error": "El usuario no está asignado a ese negocio"}

@router.put("/actualizar/{usuario_id}", response=UsuarioSchema, auth=AuthBearer())
@require_admin
def actualizar_usuario(request, usuario_id: int, payload: UsuarioUpdateSchema):
    try:
        usuario = Usuario.objects.get(id=usuario_id)
        usuario.nombre = payload.nombre
        usuario.contraseña_haseada = make_password(payload.contraseña)
        usuario.rol = payload.rol
        usuario.save()
        return usuario
    except Usuario.DoesNotExist:
        return {"error": "Usuario no encontrado"}

@router.put("/actualizar_contrasena_admin", response=UsuarioSchema, auth=AuthBearer())
@require_admin
def actualizar_contrasena_admin(request, payload: UsuarioCambiarContraseñaSchema):
    try:
        usuario = request.usuario
        usuario.contraseña_haseada = make_password(payload.nueva_contraseña)
        usuario.save()
        return usuario
    except Usuario.DoesNotExist:
        return {"error": "Usuario no encontrado"}

@router.delete("/eliminar/{usuario_id}", auth=AuthBearer())
@require_admin
def eliminar_usuario(request, usuario_id: int):
    try:
        usuario = Usuario.objects.get(id=usuario_id)
        usuario.delete()
        return {"mensaje": "Usuario eliminado"}
    except Usuario.DoesNotExist:
        return {"error": "Usuario no encontrado"}