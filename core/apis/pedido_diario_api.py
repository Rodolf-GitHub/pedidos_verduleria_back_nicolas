from ninja import NinjaAPI

pedido_diario_api = NinjaAPI(title="API Pedido Diario", urls_namespace="api_pedido_diario")
from pedido_diario.api import router as pedido_diario_router

pedido_diario_api.add_router("/", pedido_diario_router)
