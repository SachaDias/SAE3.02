import socket
import threading
import sys

def xor_layer(data, key):
    return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])

def handle_conn(conn, key, next_addr, next_port):
    data = conn.recv(4096)
    dec = xor_layer(data, key)
    dest, payload = dec[:21], dec[21:]  # 21 octets pour adresse
    if next_addr == '' and next_port == 0:
        print("Message reçu:", payload.decode())
    else:
        with socket.socket() as ns:
            ns.connect((next_addr, next_port))
            ns.send(payload)
    conn.close()

def main(port, key, next_addr, next_port):
    s = socket.socket()
    s.bind(("localhost", port))
    s.listen()
    print(f"Routeur sur {port}")
    while True:
        conn, _ = s.accept()
        threading.Thread(target=handle_conn, args=(conn, key, next_addr, next_port)).start()

if __name__ == "__main__":
    port = int(sys.argv[1])
    key = sys.argv[2].encode()
    next_addr = sys.argv[3]
    next_port = int(sys.argv[4])
    main(port, key, next_addr, next_port)
