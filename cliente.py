import socket
import json
import sys

# Forzar codificación UTF-8 en la consola para mostrar acentos y eñes correctamente
sys.stdout.reconfigure(encoding='utf-8')
sys.stdin.reconfigure(encoding='utf-8')

HOST = '127.0.0.1'
PUERTO = 5000

TAREAS = {
    '1': ('mayusculas', 'Texto a convertir a mayúsculas: '),
    '2': ('invertir', 'Texto a invertir: '),
    '3': ('contar_palabras', 'Texto: '),
    '4': ('factorial', 'Número: '),
    '5': ('primo', 'Número: '),
}

def pedir(sock, entrada, datos):
    """Envía una petición al servidor y devuelve su respuesta."""
    sock.sendall((json.dumps(datos) + '\n').encode('utf-8'))
    return json.loads(entrada.readline())

def menu_tareas(sock, entrada):
    """Menú que se muestra después de iniciar sesión."""
    while True:
        print("\n--- TAREAS DISPONIBLES ---")
        print("1. Convertir a mayúsculas")
        print("2. Invertir texto")
        print("3. Contar palabras")
        print("4. Factorial")
        print("5. Verificar número primo")
        print("6. Cerrar sesión")
        opcion = input("Seleccione una opción: ")

        if opcion == '6':
            break
        if opcion not in TAREAS:
            print("Opción no válida.")
            continue
        tipo, pregunta = TAREAS[opcion]
        dato = input(pregunta)
        respuesta = pedir(sock, entrada, {"accion": "tarea", "tipo": tipo, "dato": dato})
        if 'resultado' in respuesta:
            print(f"\n[+] Resultado: {respuesta['resultado']}")
            print(f"    (procesado por el worker {respuesta['worker']}, {respuesta['hilo']})")
        else:
            print("\n[-] Error:", respuesta.get('error'))

def menu():
    try:
        sock = socket.create_connection((HOST, PUERTO))
    except OSError:
        print("[-] No se pudo conectar al servidor. ¿Está corriendo servidor.py?")
        return

    with sock, sock.makefile('r', encoding='utf-8') as entrada:
        while True:
            print("\n--- SISTEMA DE GESTIÓN DE TAREAS ---")
            print("1. Registrar usuario")
            print("2. Iniciar sesión y enviar tareas")
            print("3. Salir")
            opcion = input("Seleccione una opción: ")

            if opcion == '1':
                usuario = input("Ingrese nombre de usuario: ")
                password = input("Ingrese contraseña: ")
                respuesta = pedir(sock, entrada, {"accion": "registro", "usuario": usuario, "contraseña": password})
                print("Respuesta del servidor:", respuesta)

            elif opcion == '2':
                usuario = input("Usuario: ")
                password = input("Contraseña: ")
                respuesta = pedir(sock, entrada, {"accion": "login", "usuario": usuario, "contraseña": password})
                if 'mensaje' in respuesta:
                    print("\n[+] Login correcto:", respuesta["mensaje"])
                    menu_tareas(sock, entrada)
                else:
                    print("\n[-] Error:", respuesta.get("error"))

            elif opcion == '3':
                break
            else:
                print("Opción no válida.")

if __name__ == '__main__':
    menu()
