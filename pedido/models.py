from django.db import models
from django.utils import timezone

# Create your models here.
class Pedido(models.Model):
    creado_por = models.ForeignKey('usuarios.Usuario', on_delete=models.CASCADE)
    negocio = models.ForeignKey('negocio.Negocio', on_delete=models.CASCADE)
    fecha_creacion = models.DateTimeField(default=timezone.now)  # Modificable
    estado = models.CharField(max_length=50)   # en_proceso, completado

    class Meta:
        db_table = 'pedidos'

class PedidoProducto(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    producto = models.ForeignKey('producto.Producto', on_delete=models.CASCADE)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    unidad_medida = models.CharField(max_length=20, default='cajas')  # kg, unidad, etc.

    class Meta:
        db_table = 'pedido_productos'
