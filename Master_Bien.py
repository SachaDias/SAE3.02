import socket
import threading
import time
import mysql.connector

DB_CFG = dict(
    user='saeuser',
    password='unmotdepassefiable',
    host='localhost',
    database='sae3'
)

def db_execute(query, params=(), fetch=False):
    conn = mysql.connector.connect(**DB_CFG)
    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall() if fetch else None
    conn.commit()
    cur.close()
    conn.close()
    return rows

def handle_register_router(parts, remote_ip):
    # REGISTER_ROUTER|NOM|IP_DONNEE|PORT|CLEF
    if len(parts) != 5:
        return "ERR|REGISTER_ROUTER_FORMAT"
    nom, _ip_ignored, port_str, clef = parts[1], parts[2], parts[3], parts[4]
    try:
        port = int(port_str)
    except ValueError:
        return "ERR|BAD_PORT"

    # On utilise l'IP réelle de la connexion (remote_ip)
    db_execute(
        "INSERT INTO routeurs_dyn (nom, ip, port, clef, alive) VALUES (%s,%s,%s,%s,%s)",
        (nom, remote_ip, port, clef, 0)
    )
    return "OK|ROUTER_REGISTERED"

def handle_register_client(parts, remote_ip):
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
    # On lit les routeurs dynamiques vivants
    rows = db_execute(
        "SELECT nom, ip, port, clef FROM routeurs_dyn WHERE alive=1 ORDER BY id",
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

def ping_router(ip, port, timeout=1.0):
    try:
        with socket.socket() as s:
            s.settimeout(timeout)
            s.connect((ip, port))
        return True
    except OSError:
        return False

def monitor_routers():
    """Thread qui surveille les routeurs_dyn et met à jour alive."""
    while True:
        try:
            rows = db_execute(
                "SELECT id, ip, port FROM routeurs_dyn",
                fetch=True
            )
            for rid, ip, port in rows:
                ok = ping_router(ip, int(port))
                db_execute(
                    "UPDATE routeurs_dyn SET alive=%s WHERE id=%s",
                    (1 if ok else 0, rid)
                )
        except Exception as e:
            print("Erreur monitor_routers:", e)
        time.sleep(5)

def client_handler(conn, addr):
    remote_ip, _remote_port = addr
    try:
        data = conn.recv(4096)
        if not data:
            return
        text = data.decode(errors="replace").strip()
        parts = text.split("|")
        cmd = parts[0]

        if cmd == "REGISTER_ROUTER":
            resp = handle_register_router(parts, remote_ip)
        elif cmd == "REGISTER_CLIENT":
            resp = handle_register_client(parts, remote_ip)
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
    # Thread de surveillance des routeurs
    t = threading.Thread(target=monitor_routers, daemon=True)
    t.start()

    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Pour plusieurs machines, remplace "localhost" par l'IP du master ou ''
    s.bind(("localhost", 5100))
    s.listen(5)
    print("Master prêt sur 5100")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=client_handler, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()
