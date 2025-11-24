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

def handle_conn(conn, key, next_addr, next_port):
    data = conn.recv(4096)
    dec = xor_layer(data, key)
    dest, payload = dec[:21], dec[21:]
    if next_addr == '' and next_port == 0:
        print("Message reçu:", payload.decode())
    else:
        with socket.socket() as ns:
            ns.connect((next_addr, next_port))
            ns.send(payload)
    conn.close()

def main(port, next_addr, next_port):
    key = get_key_for_me(port)
    if not key:
        print(f"Aucune clef trouvée pour le port {port}")
        return
    s = socket.socket()
    s.bind(("localhost", port))
    s.listen()
    print(f"Routeur sur {port}")
    while True:
        conn, _ = s.accept()
        threading.Thread(target=handle_conn, args=(conn, key, next_addr, next_port)).start()

if __name__ == "__main__":
    port = int(sys.argv[1])
    next_addr = sys.argv[2]
    next_port = int(sys.argv[3])
    main(port, next_addr, next_port)
