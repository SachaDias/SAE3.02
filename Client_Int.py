import sys
import socket
import threading
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTextEdit,
    QLineEdit, QPushButton, QLabel
)

MASTER_ADDR = ("localhost", 5100)
ADDR_LEN = 21  # "ip:port" sur 21 octets

def xor_layer(data, key_str):
    key = key_str.encode() if isinstance(key_str, str) else key_str
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

class ClientGUI(QWidget):
    def __init__(self, local_port, local_name):
        super().__init__()
        self.local_port = local_port
        self.local_name = local_name
        self.routers_dispos = []  # (nom, ip, port, clef)

        self.setWindowTitle(f"{local_name} (port {local_port})")
        self.resize(550, 480)

        layout = QVBoxLayout()
        self.info_label = QLabel(f"Client {local_name} sur port {local_port}")
        self.history = QTextEdit()
        self.history.setReadOnly(True)

        # Route des routeurs
        self.route_line = QLineEdit()
        self.route_line.setPlaceholderText("Route (R1,R2,R3)")

        self.refresh_btn = QPushButton("Rafraîchir routeurs")

        # Nouveau: IP destination
        self.dest_ip_input = QLineEdit()
        self.dest_ip_input.setPlaceholderText("IP destinataire (ex: 192.168.1.20)")

        # Port destination
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("Port destinataire (ex: 5300)")

        self.msg_input = QLineEdit()
        self.msg_input.setPlaceholderText("Votre message")
        self.send_btn = QPushButton("Envoyer")

        for w in [
            self.info_label, self.history, self.route_line,
            self.refresh_btn, self.dest_ip_input, self.target_input,
            self.msg_input, self.send_btn
        ]:
            layout.addWidget(w)
        self.setLayout(layout)

        self.refresh_btn.clicked.connect(self.ask_routers)
        self.send_btn.clicked.connect(self.send_message)

        self.register_client()
        threading.Thread(target=self.listen, daemon=True).start()

    def register_client(self):
        msg = f"REGISTER_CLIENT|{self.local_name}|{self.local_port}"
        try:
            with socket.socket() as s:
                s.connect(MASTER_ADDR)
                s.sendall(msg.encode())
                resp = s.recv(4096).decode(errors="replace")
            self.history.append(f"Master: {resp}")
        except Exception as e:
            self.history.append(f"Erreur enregistrement master : {e}")

    def listen(self):
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Pour plusieurs machines, tu peux remplacer 'localhost' par '' ou l'IP locale
        s.bind(('localhost', self.local_port))
        s.listen(5)
        self.history.append("En attente de messages...")
        while True:
            conn, _ = s.accept()
            data = conn.recv(1024)
            if data:
                try:
                    msg = data.decode()
                except Exception:
                    msg = str(data)
                self.history.append(f"Reçu: {msg}")
            conn.close()

    def ask_routers(self):
        try:
            with socket.socket() as s:
                s.connect(MASTER_ADDR)
                s.sendall(b"ASK_ROUTERS")
                data = s.recv(4096).decode(errors="replace")
            lines = data.splitlines()
            self.routers_dispos = []
            if lines and lines[0] == "ROUTERS":
                for line in lines[1:]:
                    if line == "END":
                        break
                    nom, ip, port_str, clef = line.split(";")
                    clef = clef.strip()
                    if clef.startswith("b'") and clef.endswith("'"):
                        clef = clef[2:-1]
                    self.routers_dispos.append((nom, ip, int(port_str), clef))
            self.history.append("Routeurs :")
            for r in self.routers_dispos:
                self.history.append(f"{r[0]} @ {r[1]}:{r[2]} clé={r[3]}")
        except Exception as e:
            self.history.append(f"Erreur ASK_ROUTERS : {e}")

    def build_onion(self, dest_ip, dest_port, msg, route_names):
        route = []
        for name in route_names:
            name = name.strip()
            ok = None
            for (nom, ip, port, clef) in self.routers_dispos:
                if nom == name:
                    ok = (ip, port, clef)
                    break
            if not ok:
                raise ValueError(f"Routeur {name} introuvable")
            route.append(ok)

        # Centre : "IP_DEST:PORT_DEST:message"
        inner = f"{dest_ip}:{dest_port}:{msg}".encode()
        layer = inner
        for i in reversed(range(len(route))):
            ip, port, clef = route[i]
            if i == len(route) - 1:
                addr_str = "0.0.0.0:0000"
            else:
                next_ip, next_port, _ = route[i + 1]
                addr_str = f"{next_ip}:{next_port}"
            addr_bytes = addr_str.ljust(ADDR_LEN).encode()
            layer = xor_layer(addr_bytes + layer, clef)
        return layer, route

    def send_message(self):
        dest_ip = self.dest_ip_input.text().strip()
        dest_port = self.target_input.text().strip()
        msg = self.msg_input.text()
        route_spec = self.route_line.text().strip()

        if not dest_ip or not dest_port or not msg or not route_spec:
            self.history.append("Remplir IP, port, message et route.")
            return
        try:
            int(dest_port)
        except ValueError:
            self.history.append("Port destinataire = entier.")
            return

        try:
            payload, route = self.build_onion(dest_ip, dest_port, msg, route_spec.split(","))
        except Exception as e:
            self.history.append(f"Erreur oignon : {e}")
            return

        first_ip, first_port, _ = route[0]
        try:
            with socket.socket() as s:
                s.connect((first_ip, first_port))
                s.sendall(payload)
            self.history.append(f"Envoyé via {route_spec} vers {dest_ip}:{dest_port} : {msg}")
            self.msg_input.clear()
        except Exception as e:
            self.history.append(f"Erreur envoi premier routeur : {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    local_port = int(sys.argv[1])
    local_name = sys.argv[2] if len(sys.argv) > 2 else "CLIENT_X"
    w = ClientGUI(local_port, local_name)
    w.show()
    sys.exit(app.exec_())
