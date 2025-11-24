import socket
import threading
import pickle

ROUTERS = [("localhost", 5001), ("localhost", 5002), ("localhost", 5003)]
ROUTER_KEYS = [b'clef1', b'clef2', b'clef3']

def client_handler(conn):
    conn.send(pickle.dumps({"route": ROUTERS, "keys": ROUTER_KEYS}))
    conn.close()

def master_server():
    s = socket.socket()
    s.bind(("localhost", 5000))
    s.listen()
    print("Master prêt sur 5000")
    while True:
        conn, _ = s.accept()
        threading.Thread(target=client_handler, args=(conn,)).start()

if __name__ == "__main__":
    master_server()
