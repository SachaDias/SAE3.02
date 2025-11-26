import socket
import threading
import sys
import mysql.connector

DB_CFG = dict(
    user='saeuser',
    password='unmotdepassefiable',
    host='localhost',
    database='sae3'
)

MASTER_ADDR = ("localhost", 5100)

def get_key_for_me(port):
    conn = mysql.connector.connect(**DB_CFG)
    cursor = conn.cursor()
    cursor.execute("SELECT clef FROM routeurs WHERE port=%s", (port,))
    res = cursor.fetchone()
    cursor.close()
    conn.close()
    return res[0] if res else None  # clef stockée en texte

def xor_layer(data, key):
    key_b = key.encode()  # on convertit la clef texte en bytes
    return bytes([b ^ key_b[i % len(key_b)] for i, b in enumerate(data)])

def register_router(name, port, clef):
    msg = f"REGISTER_ROUTER|{name}|localhost|{port}|{clef}"
    try:
        with socket.socket() as s:
            s.connect(MASTER_ADDR)
            s.sendall(msg.encode())
            resp = s.recv(4096).decode(errors="replace")
            print(f"[{name}] Enregistrement master: {resp}")
    except Exception as e:
        print(f"[{name}] ERREUR enregistrement master: {e}")

def handle_conn(conn, key, next_addr, next_port, name, my_port):
    data = conn.recv(4096)
    if not data:
        conn.close()
        return

    print(f"\n--- Routeur {name} sur port {my_port} ---")
    print(f"Reçu (chiffré) : {data.hex()[:64]}...")

    dec = xor_layer(data, key)

    if next_port != 0:
        print(f"Déchiffré -> on relaie vers {next_addr}:{next_port}")
        with socket.socket() as ns:
            ns.connect((next_addr, next_port))
            ns.sendall(dec)
    else:
        # Dernier routeur : on attend "PORT_DEST:MESSAGE"
        try:
            text = dec.decode(errors='replace')
            print(f"Données décodées au dernier routeur : {text}")
            port_str, msg = text.split(":", 1)
            dest_port = int(port_str)
            with socket.socket() as s:
                s.connect(("localhost", dest_port))
                s.sendall(msg.encode())
            print(f">>> MESSAGE FINAL livré à {dest_port}")
        except Exception as e:
            print("Erreur de décodage au dernier routeur :", e)
            print("Données brutes :", dec)

    conn.close()

def main(port, next_addr, next_port, name):
    key = get_key_for_me(port)
    if not key:
        print(f"Aucune clef trouvée pour le port {port} dans la table routeurs")
        return

    # Enregistrement dynamique au master
    register_router(name, port, key)

    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("localhost", port))
    s.listen()
    print(f"Routeur {name} prêt sur {port}")

    while True:
        conn, _ = s.accept()
        threading.Thread(
            target=handle_conn,
            args=(conn, key, next_addr, next_port, name, port),
            daemon=True
        ).start()

if __name__ == "__main__":
    port = int(sys.argv[1])
    next_addr = sys.argv[2]
    next_port = int(sys.argv[3])
    name = sys.argv[4] if len(sys.argv) > 4 else f"R_{port}"
    main(port, next_addr, next_port, name)
