import os
import sys
import django

# Asegura que el directorio raíz esté en sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from pedido_diario.models import PedidoDiarioItem
from django.db.models import Count

dupes = (
    PedidoDiarioItem.objects
    .values('pedido_diario', 'producto')
    .annotate(count=Count('id'))
    .filter(count__gt=1)
)

for d in dupes:
    items = PedidoDiarioItem.objects.filter(
        pedido_diario=d['pedido_diario'],
        producto=d['producto']
    ).order_by('id')
    items.exclude(id=items.first().id).delete()

print("Duplicados eliminados.")