
from ninja import NinjaAPI

negocios_api = NinjaAPI(title="API Negocios", urls_namespace="api_negocios")
from negocio.api import router as negocio_router
negocios_api.add_router("/", negocio_router)