from ninja.security import HttpBearer
from ninja.errors import HttpError
from .models import Usuario
from functools import wraps


class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        try:
            usuario = Usuario.objects.get(token=token)
            return usuario
        except Usuario.DoesNotExist:
            return None


def require_admin(view_func):
    """Decorador que requiere que el usuario autenticado sea admin"""
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        # Obtener el token del header Authorization
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            raise HttpError(401, "Token requerido")
        
        token = auth_header.replace('Bearer ', '')
        try:
            usuario = Usuario.objects.get(token=token)
            if usuario.rol != 'admin':
                raise HttpError(403, "Se requiere rol admin")
            request.usuario = usuario
            return view_func(request, *args, **kwargs)
        except Usuario.DoesNotExist:
            raise HttpError(401, "Token inválido")
    
    # Agregar información de permisos a la documentación
    original_doc = view_func.__doc__ or ""
    wrapped_view.__doc__ = f"{original_doc}\n\n🔒 **Permisos requeridos:** Admin"
    return wrapped_view


def require_verdulero(view_func):
    """Decorador que requiere que el usuario autenticado sea verdulero, comprador o admin"""
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        # Obtener el token del header Authorization
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            raise HttpError(401, "Token requerido")
        
        token = auth_header.replace('Bearer ', '')
        try:
            usuario = Usuario.objects.get(token=token)
            if usuario.rol not in ['verdulero', 'comprador', 'admin']:
                raise HttpError(403, "Se requiere rol verdulero, comprador o admin")
            request.usuario = usuario
            return view_func(request, *args, **kwargs)
        except Usuario.DoesNotExist:
            raise HttpError(401, "Token inválido")
    
    # Agregar información de permisos a la documentación
    original_doc = view_func.__doc__ or ""
    wrapped_view.__doc__ = f"{original_doc}\n\n🔒 **Permisos requeridos:** Verdulero, Comprador o Admin"
    return wrapped_view


def require_comprador(view_func):
    """Decorador que requiere que el usuario autenticado sea comprador o admin"""
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        # Obtener el token del header Authorization
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            raise HttpError(401, "Token requerido")
        
        token = auth_header.replace('Bearer ', '')
        try:
            usuario = Usuario.objects.get(token=token)
            if usuario.rol not in ['comprador', 'admin']:
                raise HttpError(403, "Se requiere rol comprador o admin")
            request.usuario = usuario
            return view_func(request, *args, **kwargs)
        except Usuario.DoesNotExist:
            raise HttpError(401, "Token inválido")
    
    # Agregar información de permisos a la documentación
    original_doc = view_func.__doc__ or ""
    wrapped_view.__doc__ = f"{original_doc}\n\n🔒 **Permisos requeridos:** Comprador o Admin"
    return wrapped_view


def require_superadmin(view_func):
    """Decorador que requiere que el usuario autenticado sea superadmin"""
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        # Obtener el token del header Authorization
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            raise HttpError(401, "Token requerido")
        
        token = auth_header.replace('Bearer ', '')
        try:
            usuario = Usuario.objects.get(token=token)
            if usuario.rol != 'superadmin':
                raise HttpError(403, "Se requiere rol superadmin")
            request.usuario = usuario
            return view_func(request, *args, **kwargs)
        except Usuario.DoesNotExist:
            raise HttpError(401, "Token inválido")
    
    # Agregar información de permisos a la documentación
    original_doc = view_func.__doc__ or ""
    wrapped_view.__doc__ = f"{original_doc}\n\n🔒 **Permisos requeridos:** Superadmin"
    return wrapped_view

