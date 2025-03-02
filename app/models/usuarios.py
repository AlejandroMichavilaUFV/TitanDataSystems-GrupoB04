import json
import os
import uuid

DATA_FILE = 'usuarios.json'

class Usuario:
    def __init__(self, id, nombre, usuario, descripcion, imagen):
        self.id = id
        self.nombre = nombre
        self.usuario = usuario
        self.descripcion = descripcion
        self.imagen = imagen

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "usuario": self.usuario,
            "descripcion": self.descripcion,
            "imagen": self.imagen
        }

def cargar_datos():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as file:
            try:
                return [Usuario(**usuario) for usuario in json.load(file)]
            except json.JSONDecodeError:
                return []
    return []

def guardar_datos(usuarios):
    with open(DATA_FILE, 'w') as file:
        json.dump([usuario.to_dict() for usuario in usuarios], file, indent=4)

def crear_usuario():
    usuarios = cargar_datos()
    id = str(uuid.uuid4())  # Generar un ID único aleatorio
    nombre = input("Ingrese el nombre del usuario: ")
    usuario = input("Ingrese el nombre de usuario: ")
    descripcion = input("Ingrese la descripción del usuario: ")
    imagen = input("Ingrese el nombre del archivo de imagen: ")
    usuario_obj = Usuario(id, nombre, usuario, descripcion, imagen)
    usuarios.append(usuario_obj)
    guardar_datos(usuarios)
    print("Usuario creado exitosamente.")

def leer_usuarios():
    usuarios = cargar_datos()
    if usuarios:
        for i, usuario in enumerate(usuarios, start=1):
            print(f"{i}. ID: {usuario.id}, Nombre: {usuario.nombre}, Usuario: {usuario.usuario}, Descripción: {usuario.descripcion}, Imagen: {usuario.imagen}")
    else:
        print("No hay usuarios registrados.")

def actualizar_usuario():
    usuarios = cargar_datos()
    leer_usuarios()
    indice = int(input("Ingrese el número del usuario a actualizar: ")) - 1
    if 0 <= indice < len(usuarios):
        id = usuarios[indice].id  # Mantener el mismo ID
        nombre = input("Ingrese el nuevo nombre del usuario: ")
        usuario = input("Ingrese el nuevo nombre de usuario: ")
        descripcion = input("Ingrese la nueva descripción del usuario: ")
        imagen = input("Ingrese el nuevo nombre del archivo de imagen: ")
        usuarios[indice] = Usuario(id, nombre, usuario, descripcion, imagen)
        guardar_datos(usuarios)
        print("Usuario actualizado exitosamente.")
    else:
        print("Índice inválido.")

def borrar_usuario():
    usuarios = cargar_datos()
    leer_usuarios()
    indice = int(input("Ingrese el número del usuario a borrar: ")) - 1
    if 0 <= indice < len(usuarios):
        usuarios.pop(indice)
        guardar_datos(usuarios)
        print("Usuario borrado exitosamente.")
    else:
        print("Índice inválido.")