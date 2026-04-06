"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from core.apis.usuarios_api import usuarios_api
from core.apis.productos_api import productos_api
from core.apis.pedido_api import pedidos_api
from core.apis.pedido_diario_api import pedido_diario_api
from core.apis.negocios_api import negocios_api
#from core.apis.compras_api import compras_api

urlpatterns = [
    #path('admin/', admin.site.urls),
    path('api/usuarios/', usuarios_api.urls),
    path('api/productos/', productos_api.urls),
    path('api/pedidos/', pedidos_api.urls),
    path('api/pedidos_diarios/', pedido_diario_api.urls),
    path('api/negocios/', negocios_api.urls),
    #path('api/compras/', compras_api.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
