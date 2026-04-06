from django.db import models
from decimal import Decimal, ROUND_HALF_UP


class PedidoDiario(models.Model):
	fecha = models.DateField(unique=True)
	estado = models.CharField(
		max_length=50,
		choices=[('en_proceso', 'En proceso'), ('completado', 'Completado')],
		default='en_proceso',
	)
	creado_por = models.ForeignKey(
		'usuarios.Usuario',
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
	)
	fecha_creacion = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = 'pedido_diarios'


class PedidoDiarioItem(models.Model):
	pedido_diario = models.ForeignKey(PedidoDiario, on_delete=models.CASCADE)
	producto = models.ForeignKey('producto.Producto', on_delete=models.CASCADE)
	estado_compra = models.CharField(
		max_length=50,
		choices=[('comprado', 'Comprado'), ('no_comprado', 'No Comprado')],
	)
	motivo_no_compra = models.CharField(max_length=255, null=True, blank=True)
	precio_compra = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Precio de compra del producto ese día")
	factor_division = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Factor de división usado ese día")
	ganancia_aplicada = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Porcentaje de ganancia aplicado ese día")
	class Meta:
		db_table = 'pedido_diario_items'
		unique_together = ('pedido_diario', 'producto',)


	
