import socket
import sys
import json
import sqlite3
import threading
from werkzeug.security import generate_password_hash, check_password_hash

sys.stdout.reconfigure(encoding='utf-8')

# Configuración del servidor (mismo puerto 5000 de la PFO 2)
HOST = '127.0.0.1'
PUERTO = 5000
DB_NAME = 'usuarios.db'

# Workers disponibles (cada uno corre con: python worker.py <puerto>)
WORKERS = [('127.0.0.1', 6001), ('127.0.0.1', 6002), ('127.0.0.1', 6003)]
turno = 0                      # contador para repartir en Round Robin
turno_lock = threading.Lock()

def init_db():
    """Inicializa base de datos SQLite y crea tabla de usuarios si no existe (igual que PFO 2)."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT UNIQUE NOT NULL,
                contrasena TEXT NOT NULL
            )
        ''')
        conn.commit()

def enviar(conn, datos):
    """Envía un diccionario como JSON terminado en salto de línea."""
    conn.sendall((json.dumps(datos) + '\n').encode('utf-8'))

# 1. Registro de Usuarios
def registro(datos):
    if 'usuario' not in datos or 'contraseña' not in datos:
        return {"error": "Faltan datos requeridos (usuario y contraseña)"}

    # Hashear la contraseña (nunca guardar en texto plano)
    contrasena_hash = generate_password_hash(datos['contraseña'])
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO usuarios (usuario, contrasena) VALUES (?, ?)',
                           (datos['usuario'], contrasena_hash))
            conn.commit()
        return {"mensaje": f"Usuario '{datos['usuario']}' registrado exitosamente"}
    except sqlite3.IntegrityError:
        return {"error": "El nombre de usuario ya está registrado"}

# 2. Inicio de Sesión
def login(datos):
    if 'usuario' not in datos or 'contraseña' not in datos:
        return {"error": "Faltan credenciales"}

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT contrasena FROM usuarios WHERE usuario = ?', (datos['usuario'],))
        fila = cursor.fetchone()

    if fila and check_password_hash(fila[0], datos['contraseña']):
        return {"mensaje": "Inicio de sesión exitoso"}
    return {"error": "Credenciales inválidas"}

# 3. Gestión de Tareas: se distribuyen a los workers
def enviar_a_worker(tarea):
    """Reparte la tarea entre los workers (Round Robin). Si uno está caído, prueba con el siguiente."""
    global turno
    with turno_lock:
        inicio = turno
        turno += 1

    for i in range(len(WORKERS)):
        direccion = WORKERS[(inicio + i) % len(WORKERS)]
        try:
            with socket.create_connection(direccion, timeout=3) as w:
                w.settimeout(30)
                enviar(w, tarea)
                respuesta = w.makefile('r', encoding='utf-8').readline()
            print(f"[*] Tarea '{tarea.get('tipo')}' enviada al worker {direccion[1]}")
            return json.loads(respuesta)
        except (OSError, json.JSONDecodeError):
            print(f"[!] Worker {direccion[1]} no disponible, probando otro")
    return {"error": "No hay workers disponibles"}

def atender_cliente(conn, addr):
    """Un hilo por cliente. La sesión (usuario autenticado) vive mientras dure la conexión."""
    print(f"[+] Cliente conectado: {addr}")
    usuario_actual = None
    try:
        with conn, conn.makefile('r', encoding='utf-8') as entrada:
            for linea in entrada:
                try:
                    datos = json.loads(linea)
                except json.JSONDecodeError:
                    enviar(conn, {"error": "Mensaje inválido"})
                    continue

                accion = datos.get('accion')
                if accion == 'registro':
                    respuesta = registro(datos)
                elif accion == 'login':
                    respuesta = login(datos)
                    if 'mensaje' in respuesta:
                        usuario_actual = datos['usuario']
                elif accion == 'tarea':
                    if usuario_actual is None:
                        respuesta = {"error": "Debe iniciar sesión primero"}
                    else:
                        respuesta = enviar_a_worker({"tipo": datos.get('tipo'), "dato": datos.get('dato')})
                else:
                    respuesta = {"error": "Acción desconocida"}
                enviar(conn, respuesta)
    except OSError:
        pass
    print(f"[-] Cliente desconectado: {addr}")

def main():
    init_db()
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        servidor.bind((HOST, PUERTO))
    except OSError as e:
        print(f"[!] No se pudo usar el puerto {PUERTO}: {e}")
        return
    servidor.listen()
    print(f"[*] Servidor escuchando en {HOST}:{PUERTO}")
    try:
        while True:
            conn, addr = servidor.accept()
            threading.Thread(target=atender_cliente, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("\n[*] Servidor detenido")

if __name__ == '__main__':
    main()
