
from ninja import NinjaAPI

compras_api = NinjaAPI(title="API Compras", urls_namespace="api_compras")
from compra.api import router as compra_router
compras_api.add_router("/", compra_router)
