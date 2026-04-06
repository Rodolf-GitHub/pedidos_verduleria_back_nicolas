from ninja import Schema,ModelSchema
from .models import Negocio
from typing import Optional

class NegocioSchema(ModelSchema):
    class Meta:
        model = Negocio
        fields = '__all__'

class NegocioCreateSchema(Schema):
    nombre: str
    direccion: Optional[str] = None

class NegocioUpdateSchema(Schema):
    nombre: Optional[str] = None
    direccion: Optional[str] = None
    