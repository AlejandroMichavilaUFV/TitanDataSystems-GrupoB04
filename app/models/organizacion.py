import uuid

class Organizacion:
    def __init__(self, id, nombre, usuario_creador_id, politicas, imagen, descripcion):
        self.id = id
        self.nombre = nombre
        self.usuario_creador_id = usuario_creador_id
        self.politicas = politicas
        self.imagen = imagen
        self.descripcion = descripcion

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "usuario_creador_id": self.usuario_creador_id,
            "politicas": self.politicas,
            "imagen": self.imagen,
            "descripcion": self.descripcion
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data["id"],
            nombre=data["nombre"],
            usuario_creador_id=data["usuario_creador_id"],
            politicas=data["politicas"],
            imagen=data["imagen"],
            descripcion=data["descripcion"]
        )
