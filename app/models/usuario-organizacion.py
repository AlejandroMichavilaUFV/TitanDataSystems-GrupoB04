from datetime import datetime

class UsuarioOrganizacion:
    def __init__(self, id, usuario_id, organizacion_id, rol, estado, fecha_union):
        self.id = id
        self.usuario_id = usuario_id
        self.organizacion_id = organizacion_id
        self.rol = rol
        self.estado = estado
        self.fecha_union = fecha_union  # datetime en ISO 8601 (string)

    def to_dict(self):
        return {
            "id": self.id,
            "usuario_id": self.usuario_id,
            "organizacion_id": self.organizacion_id,
            "rol": self.rol,
            "estado": self.estado,
            "fecha_union": self.fecha_union
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data["id"],
            usuario_id=data["usuario_id"],
            organizacion_id=data["organizacion_id"],
            rol=data["rol"],
            estado=data["estado"],
            fecha_union=data["fecha_union"]
        )
