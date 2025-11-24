import socket
import threading
import sys
import mysql.connector

DB_CFG = dict(user='saeuser', password='unmotdepassefiable', host='localhost', database='sae3')

def get_key_for_me(port):
    conn = mysql.connector.connect(**DB_CFG)
    cursor = conn.cursor()
    cursor.execute("SELECT clef FROM routeurs WHERE port=%s", (port,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else None

def xor_layer(data, key):
    return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])

def handle_conn(conn, key, next_addr, next_port, name):
    data = conn.recv(4096)
    print(f"\n--- Routeur {name} sur port {port} ---")
    print(f"Reçu (chiffré) : {data.hex()[:64]}...")
    dec = xor_layer(data, key)
    addr_info, payload = dec[:21], dec[21:]
    print(f"Déchiffré -> Adresse suivante : {addr_info.decode(errors='replace').strip()}")
    print(f"Déchiffré -> Début du payload : {payload[:40].decode(errors='replace')}...")
    if next_addr == '' and next_port == 0:
        print(f"\n>>> MESSAGE FINAL arrivé à {name} : {payload.decode(errors='replace')}\n")
    else:
        with socket.socket() as ns:
            ns.connect((next_addr, next_port))
            ns.send(payload)
    conn.close()

def main(port, next_addr, next_port, name):
    key = get_key_for_me(port)
    if not key:
        print(f"Aucune clef trouvée pour le port {port}")
        return
    s = socket.socket()
    s.bind(("localhost", port))
    s.listen()
    print(f"Routeur {name} prêt sur {port}")
    while True:
        conn, _ = s.accept()
        threading.Thread(target=handle_conn, args=(conn, key, next_addr, next_port, name)).start()

if __name__ == "__main__":
    port = int(sys.argv[1])
    next_addr = sys.argv[2]
    next_port = int(sys.argv[3])
    name = sys.argv[4] if len(sys.argv) > 4 else f"R_{port}"
    main(port, next_addr, next_port, name)
