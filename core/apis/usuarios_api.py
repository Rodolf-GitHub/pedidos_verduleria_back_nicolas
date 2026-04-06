
from ninja import NinjaAPI

usuarios_api = NinjaAPI(title="API Usuarios", urls_namespace="api_usuarios")
from usuarios.api import router as usuario_router
usuarios_api.add_router("/", usuario_router)