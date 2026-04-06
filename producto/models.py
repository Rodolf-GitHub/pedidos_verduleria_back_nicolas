from django.db import models

# Create your models here.
class Producto(models.Model):
    nombre = models.CharField(max_length=100,unique=True)
    se_vende_en_unidad_medida = models.CharField(max_length=50,default="cajas",null=True, blank=True) # kg, unidades, litros, etc.
    se_pide_en_unidad_medida = models.CharField(max_length=50,default="kg",null=True, blank=True)
    precio_compra = models.DecimalField(max_digits=10, decimal_places=2, default=100.00,null=True, blank=True)
    factor_division = models.DecimalField(max_digits=10, decimal_places=2, default=1.00,null=True, blank=True) # Para convertir unidad de pedido a unidad de venta
    ganancia_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=40.00,null=True, blank=True)
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True)
    ultima_actualizacion = models.DateTimeField(auto_now=True,null=True, blank=True)
    class Meta:
        db_table = 'productos'
