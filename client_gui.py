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
    if isinstance(key_str, bytes):
        key = key_str
    else:
        key = key_str.encode()
    return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])

class ClientGUI(QWidget):
    def __init__(self, local_port, local_name):
        super().__init__()
        self.local_port = local_port
        self.local_name = local_name
        self.routers_dispos = []  # (nom, ip, port, clef)

        self.setWindowTitle(f"{local_name} (port {local_port})")
        self.resize(550, 450)
        layout = QVBoxLayout()

        self.info_label = QLabel(f"Client {local_name} sur port {local_port}")
        layout.addWidget(self.info_label)

        self.history = QTextEdit()
        self.history.setReadOnly(True)
        layout.addWidget(self.history)

        self.route_line = QLineEdit()
        self.route_line.setPlaceholderText("Route (noms séparés par des virgules, ex: R1,R2,R3)")
        layout.addWidget(self.route_line)

        self.refresh_btn = QPushButton("Rafraîchir routeurs depuis master")
        layout.addWidget(self.refresh_btn)

        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("Port destinataire final (ex: 5300)")
        layout.addWidget(self.target_input)

        self.msg_input = QLineEdit()
        self.msg_input.setPlaceholderText("Votre message")
        layout.addWidget(self.msg_input)

        self.send_btn = QPushButton("Envoyer")
        layout.addWidget(self.send_btn)

        self.setLayout(layout)

        self.refresh_btn.clicked.connect(self.ask_routers)
        self.send_btn.clicked.connect(self.send_message)

        # Enregistrement au master
        self.register_client()

        # Thread d'écoute
        threading.Thread(target=self.listen, daemon=True).start()

    def register_client(self):
        msg = f"REGISTER_CLIENT|{self.local_name}|{self.local_port}"
        try:
            with socket.socket() as s:
                s.connect(MASTER_ADDR)
                s.sendall(msg.encode())
                resp = s.recv(4096).decode(errors="replace")
            self.history.append(f"Enregistrement master : {resp}")
        except Exception as e:
            self.history.append(f"Erreur d'enregistrement au master : {e}")

    def listen(self):
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('localhost', self.local_port))
        s.listen(5)
        self.history.append("En attente de messages…")
        while True:
            conn, _ = s.accept()
            data = conn.recv(1024)
            if data:
                try:
                    msg = data.decode()
                except Exception:
                    msg = str(data)
                self.history.append(f"🟢 Reçu: {msg}")
            conn.close()

    def ask_routers(self):
        try:
            with socket.socket() as s:
                s.connect(MASTER_ADDR)
                s.sendall("ASK_ROUTERS".encode())
                data = s.recv(4096).decode(errors="replace")
            lines = data.splitlines()
            self.routers_dispos = []
            if lines and lines[0] == "ROUTERS":
                for line in lines[1:]:
                    if line == "END":
                        break
                    nom, ip, port_str, clef = line.split(";")
                    port = int(port_str)
                    self.routers_dispos.append((nom, ip, port, clef))
            self.history.append("Routeurs disponibles :")
            for r in self.routers_dispos:
                self.history.append(f"{r[0]} @ {r[1]}:{r[2]} clé={r[3]}")
        except Exception as e:
            self.history.append(f"Erreur ASK_ROUTERS : {e}")

    def build_onion(self, dest_port, msg, route_names):
        # route_names : ["R1","R3","R2"] par exemple
        route = []
        for name in route_names:
            name = name.strip()
            found = None
            for (nom, ip, port, clef) in self.routers_dispos:
                if nom == name:
                    found = (ip, port, clef)
                    break
            if not found:
                raise ValueError(f"Routeur {name} introuvable dans la liste des routeurs disponibles")
            route.append(found)

        # Centre : "PORT_CLIENT_DEST:message"
        inner = f"{dest_port}:{msg}".encode()

        # Adresse spéciale pour fin de chaîne
        final_addr = "0.0.0.0:0000".ljust(ADDR_LEN).encode()

        layer = inner
        # On construit l'oignon de l'intérieur vers l'extérieur
        # Pour le dernier routeur de la route, l'adresse suivante est 0.0.0.0:0000
        for idx, (ip, port, clef) in enumerate(reversed(route)):
            if idx == 0:
                addr_bytes = final_addr
            else:
                # Adresse du routeur précédemment dans la route (en sens normal)
                # Mais plus simple : pour chaque couche, on encode l'adresse
                # du "next hop" qui est dans route dans le sens avant reverse.
                # Comme on travaille en reverse, on prend la route dans le bon sens avant.
                # Pour rester simple : on reconstruit l'adresse suivante à partir de route normal.
                pass

        # Version plus simple : on parcourt la route dans l'ordre normal,
        # en construisant layer à l'envers, avec "ip:port" du prochain.
        layer = inner
        for i in reversed(range(len(route))):
            if i == len(route) - 1:
                next_ip, next_port = "0.0.0.0", 0
            else:
                next_ip, next_port, _ = route[i + 1]
            ip, port, clef = route[i]
            if next_port == 0:
                addr_str = "0.0.0.0:0000"
            else:
                addr_str = f"{next_ip}:{next_port}"
            addr_bytes = addr_str.ljust(ADDR_LEN).encode()
            layer = xor_layer(addr_bytes + layer, clef)

        # On renvoie le paquet et la route complète
        return layer, route

    def send_message(self):
        dest_port = self.target_input.text().strip()
        msg = self.msg_input.text()
        route_spec = self.route_line.text().strip()

        if not dest_port or not msg or not route_spec:
            self.history.append("Veuillez remplir destinataire, message et route.")
            return

        try:
            int(dest_port)
        except ValueError:
            self.history.append("Port destinataire doit être un entier.")
            return

        route_names = route_spec.split(",")
        try:
            payload, route = self.build_onion(dest_port, msg, route_names)
        except Exception as e:
            self.history.append(f"Erreur construction oignon : {e}")
            return

        # Premier routeur de la route choisie (route dans l'ordre normal)
        first_ip, first_port, _ = route[0]
        try:
            with socket.socket() as s:
                s.connect((first_ip, first_port))
                s.sendall(payload)
            self.history.append(f"🔵 Envoyé via route {route_spec} vers port {dest_port} : {msg}")
            self.msg_input.clear()
        except Exception as e:
            self.history.append(f"Erreur d'envoi au premier routeur : {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Ex: python client_gui.py 5200 CLIENT_A
    local_port = int(sys.argv[1])
    local_name = sys.argv[2] if len(sys.argv) > 2 else "CLIENT_X"
    window = ClientGUI(local_port, local_name)
    window.show()
    sys.exit(app.exec_())
