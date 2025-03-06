import json
import os
import uuid

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'usuarios.json')


class Usuario:
    def __init__(self, id, nombre, usuario, descripcion, imagen, email):
        self.id = id
        self.nombre = nombre
        self.usuario = usuario
        self.descripcion = descripcion
        self.imagen = imagen
        self.email = email

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "usuario": self.usuario,
            "descripcion": self.descripcion,
            "imagen": self.imagen,
            "email": self.email
        }

def cargar_datos():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w') as file:
            json.dump([], file, indent=4)  # Crea el archivo vacío si no existe
    with open(DATA_FILE, 'r') as file:
        try:
            return [Usuario(**usuario) for usuario in json.load(file)]
        except json.JSONDecodeError:
            return []

def guardar_datos(usuarios):
    with open(DATA_FILE, 'w') as file:
        json.dump([usuario.to_dict() for usuario in usuarios], file, indent=4)

def registrar_usuario_google(profile):
    usuarios = cargar_datos()
    email = profile.get('email')
    
    usuario_existente = next((u for u in usuarios if u.email == email), None)

    if usuario_existente:
        usuario_existente.nombre = profile.get('name')
        usuario_existente.usuario = profile.get('given_name')
        usuario_existente.descripcion = "Usuario registrado con Google"
        usuario_existente.imagen = profile.get('picture')
    else:
        nuevo_usuario = Usuario(
            id=str(uuid.uuid4()),
            nombre=profile.get('name'),
            usuario=profile.get('given_name'),
            descripcion="Usuario registrado con Google",
            imagen=profile.get('picture'),
            email=email
        )
        usuarios.append(nuevo_usuario)

    guardar_datos(usuarios)
