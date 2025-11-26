import socket
import threading
import mysql.connector

DB_CFG = dict(
    user='saeuser',
    password='unmotdepassefiable',
    host='localhost',
    database='sae3'
)

def db_execute(query, params=(), fetch=False):
    conn = mysql.connector.connect(**DB_CFG)
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall() if fetch else None
    conn.commit()
    cursor.close()
    conn.close()
    return rows

def handle_register_router(parts):
    # REGISTER_ROUTER|NOM|IP|PORT|CLEF
    if len(parts) != 5:
        return "ERR|REGISTER_ROUTER_FORMAT"
    nom, ip, port_str, clef = parts[1], parts[2], parts[3], parts[4]
    try:
        port = int(port_str)
    except ValueError:
        return "ERR|BAD_PORT"
    db_execute(
        "INSERT INTO routeurs_dyn (nom, ip, port, clef) VALUES (%s,%s,%s,%s)",
        (nom, ip, port, clef)
    )
    return "OK|ROUTER_REGISTERED"

def handle_register_client(parts):
    # REGISTER_CLIENT|NOM|PORT
    if len(parts) != 3:
        return "ERR|REGISTER_CLIENT_FORMAT"
    nom, port_str = parts[1], parts[2]
    try:
        port = int(port_str)
    except ValueError:
        return "ERR|BAD_PORT"
    db_execute(
        "INSERT INTO clients_dyn (nom, port) VALUES (%s,%s)",
        (nom, port)
    )
    return "OK|CLIENT_REGISTERED"

def handle_ask_routers():
    rows = db_execute(
        "SELECT nom, ip, port, clef FROM routeurs_dyn ORDER BY id",
        fetch=True
    )
    lines = ["ROUTERS"]
    for nom, ip, port, clef in rows:
        lines.append(f"{nom};{ip};{port};{clef}")
    lines.append("END")
    return "\n".join(lines)

def handle_ask_clients():
    rows = db_execute(
        "SELECT nom, port FROM clients_dyn ORDER BY id",
        fetch=True
    )
    lines = ["CLIENTS"]
    for nom, port in rows:
        lines.append(f"{nom};{port}")
    lines.append("END")
    return "\n".join(lines)

def client_handler(conn, addr):
    try:
        data = conn.recv(4096)
        if not data:
            conn.close()
            return
        text = data.decode(errors="replace").strip()
        parts = text.split("|")
        cmd = parts[0]

        if cmd == "REGISTER_ROUTER":
            resp = handle_register_router(parts)
        elif cmd == "REGISTER_CLIENT":
            resp = handle_register_client(parts)
        elif cmd == "ASK_ROUTERS":
            resp = handle_ask_routers()
        elif cmd == "ASK_CLIENTS":
            resp = handle_ask_clients()
        else:
            resp = "ERR|UNKNOWN_CMD"

        conn.sendall(resp.encode())
    except Exception as e:
        try:
            conn.sendall(f"ERR|EXCEPTION|{e}".encode())
        except Exception:
            pass
    finally:
        conn.close()

def main():
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("localhost", 5100))
    s.listen(5)
    print("Master prêt sur 5100")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=client_handler, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()
