from django.db import models

# Create your models here.
class Negocio(models.Model):
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=200, blank=True,null=True)
    
