from usuarios import crear_usuario, leer_usuarios, actualizar_usuario, borrar_usuario

def mostrar_menu():
    while True:
        print("\nMenú de Usuarios")
        print("1. Crear Usuario")
        print("2. Leer Usuarios")
        print("3. Actualizar Usuario")
        print("4. Borrar Usuario")
        print("5. Salir")
        opcion = input("Seleccione una opción: ")

        if opcion == '1':
            crear_usuario()
        elif opcion == '2':
            leer_usuarios()
        elif opcion == '3':
            actualizar_usuario()
        elif opcion == '4':
            borrar_usuario()
        elif opcion == '5':
            break
        else:
            print("Opción inválida. Intente de nuevo.")

if __name__ == "__main__":
    mostrar_menu()
