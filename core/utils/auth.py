from __future__ import annotations

from ninja.errors import HttpError

from usuarios.models import Usuario


def get_current_usuario(request) -> Usuario:
    """Obtiene el usuario actual desde el token Bearer."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HttpError(401, "Token requerido")

    token = auth_header.replace("Bearer ", "")
    try:
        return Usuario.objects.get(token=token)
    except Usuario.DoesNotExist:
        raise HttpError(401, "Token inválido")
