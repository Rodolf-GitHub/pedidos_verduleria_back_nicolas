
from ninja import NinjaAPI

productos_api = NinjaAPI(title="API Productos", urls_namespace="api_productos")
from producto.api import router as producto_router
productos_api.add_router("/", producto_router)
