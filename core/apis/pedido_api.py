
from ninja import NinjaAPI

pedidos_api = NinjaAPI(title="API Pedidos", urls_namespace="api_pedidos")
from pedido.api import router as pedido_router
pedidos_api.add_router("/", pedido_router)