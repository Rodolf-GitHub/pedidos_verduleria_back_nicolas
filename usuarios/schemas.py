from typing import Literal,Optional
from ninja import Schema,ModelSchema
from .models import Usuario
from negocio.schemas import NegocioSchema

class UsuarioSchema(ModelSchema):
    negocios: list[NegocioSchema] = []
    class Meta:
        model = Usuario
        exclude = ['contraseña_haseada','token']
    
    @staticmethod
    def resolve_negocios(usuario: Usuario):
        from .models import UsuarioNegocio
        negocios = UsuarioNegocio.objects.filter(usuario=usuario).select_related('negocio')
        return [NegocioSchema.from_orm(un.negocio) for un in negocios]
        

class UsuarioCreateSchema(Schema):
    nombre: str
    contraseña: str
    rol: Literal['admin', 'verdulero', 'comprador']

class UsuarioLoginSchema(Schema):
    nombre: str
    contraseña: str

class TokenSchema(Schema):
    nombre: str
    rol : Literal['admin', 'verdulero', 'comprador']
    token: str
    

class UsuarioUpdateSchema(Schema):
    nombre: Optional[str] = None
    contraseña: Optional[str] = None
    rol: Optional[Literal['admin', 'verdulero', 'comprador']] = None

class UsuarioAsignarNegocioSchema(Schema):
    negocio_id: int

class UsuarioQuitarNegocioSchema(Schema):
    negocio_id: int

class UsuarioCambiarContraseñaSchema(Schema):
    nueva_contraseña: str