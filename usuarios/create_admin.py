import os
import sys
import getpass
import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.contrib.auth.hashers import make_password  # noqa: E402
from usuarios.models import Usuario  # noqa: E402


def _prompt_non_empty(label: str) -> str:
    while True:
        value = input(label).strip()
        if value:
            return value
        print("Este campo es obligatorio.")


def _prompt_password() -> str:
    while True:
        password = getpass.getpass("Password: ")
        if not password:
            print("Este campo es obligatorio.")
            continue
        password2 = getpass.getpass("Password (again): ")
        if password != password2:
            print("Los passwords no coinciden. Intenta nuevamente.")
            continue
        return password


def create_admin():
    nombre = _prompt_non_empty("Nombre de usuario: ")
    if Usuario.objects.filter(nombre=nombre).exists():
        print(f"El usuario '{nombre}' ya existe.")
        return

    password = _prompt_password()
    Usuario.objects.create(
        nombre=nombre,
        contraseña_haseada=make_password(password),
        rol="admin",
    )
    print(f"Admin '{nombre}' creado correctamente.")


if __name__ == "__main__":
    create_admin()
