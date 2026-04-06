from django.db import models

# Create your models here.
class Usuario(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    contraseña_haseada = models.CharField(max_length=100)
    rol = models.CharField(max_length=50)#admin,verdulero,comprador
    token = models.CharField(max_length=200, blank=True, null=True)

    @property
    def negocios(self):
        """Devuelve los negocios asociados al usuario."""
        from negocio.models import Negocio
        return Negocio.objects.filter(usuarionegocio__usuario=self)

    class Meta:
        db_table = 'usuarios'

class UsuarioNegocio(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='usuario_negocios')
    negocio = models.ForeignKey('negocio.Negocio', on_delete=models.CASCADE)

    class Meta:
        db_table = 'usuario_negocio'