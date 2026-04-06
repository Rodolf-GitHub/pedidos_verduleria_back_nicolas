from django.db import models

# Create your models here.
class Compra(models.Model):
    creado_por = models.ForeignKey('usuarios.Usuario', on_delete=models.CASCADE)
    negocio = models.ForeignKey('negocio.Negocio', on_delete=models.CASCADE)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    en_respuesta_a_pedido = models.ForeignKey('pedido.Pedido', on_delete=models.CASCADE)
    estado = models.CharField(max_length=50)  #en_proceso, completado

    class Meta:
        db_table = 'compras'

class CompraProducto(models.Model):
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE)
    producto = models.ForeignKey('producto.Producto', on_delete=models.CASCADE)
    pedido_producto = models.ForeignKey('pedido.PedidoProducto', on_delete=models.SET_NULL, null=True, blank=True)  # Vinculación opcional al producto del pedido
    unidad_medida = models.CharField(max_length=50,null=True, blank=True,default="kg")  # kg, unidades, litros, etc.
    cantidad = models.DecimalField(max_digits=10, decimal_places=2,null=True, blank=True,default=1.0)
    estado_compra = models.CharField(max_length=50, choices=[('comprado', 'Comprado'), ('no_comprado', 'No Comprado')], default='comprado')  # comprado, no_comprado
    motivo_no_compra = models.CharField(max_length=255, null=True, blank=True)  # Motivo si no se compró
    precio_de_compra = models.DecimalField(max_digits=10, decimal_places=2)
    ganancia_deseada = models.DecimalField(max_digits=5, decimal_places=2,null=True, blank=True,default=40.0)  # porcentaje de ganancia deseada

    class Meta:
        db_table = 'compra_productos'