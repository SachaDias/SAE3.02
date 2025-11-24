import socket
import threading
import pickle
import mysql.connector

DB_CFG = dict(user='root', password='tonmotdepasse', host='localhost', database='sae3')

def get_routeurs_and_keys():
    conn = mysql.connector.connect(**DB_CFG)
    cursor = conn.cursor()
    cursor.execute("SELECT ip, port, clef FROM routeurs ORDER BY id")
    data = cursor.fetchall()
    conn.close()
    return [ (ip, int(port)) for ip, port, _ in data ], [ clef for _, _, clef in data ]

def client_handler(conn):
    routers, keys = get_routeurs_and_keys()
    conn.send(pickle.dumps({"route": routers, "keys": keys}))
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
