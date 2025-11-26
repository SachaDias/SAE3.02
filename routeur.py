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
ADDR_LEN = 21  # "ip:port" longueur fixe

def xor_layer(data, key_str):
    key = key_str.encode() if isinstance(key_str, str) else key_str
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

def get_key_for_me(port):
    conn = mysql.connector.connect(**DB_CFG)
    cur = conn.cursor()
    cur.execute("SELECT clef FROM routeurs WHERE port=%s", (port,))
    res = cur.fetchone()
    cur.close()
    conn.close()
    return res[0] if res else None

def register_router(name, port, clef):
    msg = f"REGISTER_ROUTER|{name}|localhost|{port}|{clef}"
    try:
        with socket.socket() as s:
            s.connect(MASTER_ADDR)
            s.sendall(msg.encode())
            resp = s.recv(4096).decode(errors="replace")
        print(f"[{name}] Master: {resp}")
    except Exception as e:
        print(f"[{name}] Erreur enregistrement master: {e}")

def handle_conn(conn, key, name, my_port):
    data = conn.recv(4096)
    if not data:
        conn.close()
        return

    print(f"\n[{name}:{my_port}] reçu {len(data)} octets")
    dec = xor_layer(data, key)

    addr_bytes, payload = dec[:ADDR_LEN], dec[ADDR_LEN:]
    addr_str = addr_bytes.decode(errors="replace").strip()
    print(f"Adresse suivante: '{addr_str}'")

    if addr_str == "0.0.0.0:0000":
        # dernier routeur
        try:
            text = payload.decode(errors="replace")
            port_str, msg = text.split(":", 1)
            dest_port = int(port_str)
            with socket.socket() as s:
                s.connect(("localhost", dest_port))
                s.sendall(msg.encode())
            print(f">>> MESSAGE FINAL livré à {dest_port} : {msg}")
        except Exception as e:
            print("Erreur au dernier routeur:", e)
    else:
        try:
            ip, port_str = addr_str.split(":", 1)
            next_port = int(port_str)
            with socket.socket() as ns:
                ns.connect((ip, next_port))
                ns.sendall(payload)
            print(f"Relais vers {ip}:{next_port}")
        except Exception as e:
            print("Erreur adresse suivante:", e)

    conn.close()

def main(port, name):
    key = get_key_for_me(port)
    if not key:
        print(f"Aucune clef pour le port {port} dans la table routeurs")
        return

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
            args=(conn, key, name, port),
            daemon=True
        ).start()

if __name__ == "__main__":
    port = int(sys.argv[1])
    name = sys.argv[2] if len(sys.argv) > 2 else f"R_{port}"
    main(port, name)
