import socket
import sys
import json
import math
import threading
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding='utf-8')

# Uso: python worker.py <puerto> [hilos]    (ej: python worker.py 6001 4)
HOST = '127.0.0.1'
PUERTO = int(sys.argv[1]) if len(sys.argv) > 1 else 6001
HILOS = int(sys.argv[2]) if len(sys.argv) > 2 else 4

def ejecutar(tipo, dato):
    """Tareas que puede resolver el worker."""
    if tipo == 'mayusculas':
        return str(dato).upper()
    if tipo == 'invertir':
        return str(dato)[::-1]
    if tipo == 'contar_palabras':
        return len(str(dato).split())
    if tipo == 'factorial':
        n = int(dato)
        if not 0 <= n <= 2000:
            raise ValueError("El número debe estar entre 0 y 2000")
        return str(math.factorial(n))
    if tipo == 'primo':
        n = int(dato)
        return n > 1 and all(n % i for i in range(2, math.isqrt(n) + 1))
    raise ValueError(f"Tarea desconocida: {tipo}")

def atender(conn):
    """Se ejecuta en un hilo del pool: recibe una tarea y devuelve el resultado."""
    with conn:
        try:
            tarea = json.loads(conn.makefile('r', encoding='utf-8').readline())
            hilo = threading.current_thread().name
            tipo = tarea.get('tipo')
            dato = tarea.get('dato')
            print(f"[+] [{hilo}] Tarea recibida: '{tipo}' con dato '{dato}'")
            try:
                res = ejecutar(tipo, dato)
                respuesta = {"resultado": res}
                print(f"[✓] [{hilo}] Resultado enviado: {res}")
            except (ValueError, TypeError) as e:
                err = "Dato inválido para esa tarea" if "invalid literal" in str(e) else str(e)
                respuesta = {"error": err}
                print(f"[-] [{hilo}] Error en tarea: {err}")
            respuesta["worker"] = PUERTO
            respuesta["hilo"] = hilo
            conn.sendall((json.dumps(respuesta) + '\n').encode('utf-8'))
        except (OSError, json.JSONDecodeError):
            pass

def main():
    worker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    worker.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        worker.bind((HOST, PUERTO))
    except OSError as e:
        print(f"[!] No se pudo usar el puerto {PUERTO}: {e}")
        return
    worker.listen()
    print(f"[*] Worker escuchando en {HOST}:{PUERTO} con pool de {HILOS} hilos")

    # Pool de hilos: si todos están ocupados, las tareas esperan en cola
    with ThreadPoolExecutor(max_workers=HILOS, thread_name_prefix=f"w{PUERTO}-hilo") as pool:
        try:
            while True:
                conn, _ = worker.accept()
                pool.submit(atender, conn)
        except KeyboardInterrupt:
            print("\n[*] Worker detenido")

if __name__ == '__main__':
    main()
