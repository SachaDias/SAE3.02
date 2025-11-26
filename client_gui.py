import sys
import socket
import threading
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton, QLabel

# Paramétrage du circuit
ROUTE = [('localhost', 5101), ('localhost', 5102), ('localhost', 5103)]
ROUTE_KEYS = [b'cle1', b'cle2', b'cle3']
# On préfixera le message réel par le port destinataire clair en début de texte

def xor_layer(data, key):
    return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])

def build_onion(dest_port, msg):
    layer = f"{dest_port}:{msg}".encode()  # Ajoute le destinataire
    for key in reversed(ROUTE_KEYS):
        layer = xor_layer(layer, key)
    return layer

class ClientGUI(QWidget):
    def __init__(self, local_port, entree_routeur):
        super().__init__()
        self.local_port = local_port
        self.entree_routeur = entree_routeur

        self.setWindowTitle(f"Client (port {local_port})")
        self.resize(400, 300)
        layout = QVBoxLayout()

        self.history = QTextEdit()
        self.history.setReadOnly(True)
        layout.addWidget(self.history)

        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("Port destinataire (ex: 5300)")
        layout.addWidget(self.target_input)

        self.msg_input = QLineEdit()
        self.msg_input.setPlaceholderText("Votre message")
        layout.addWidget(self.msg_input)

        self.send_btn = QPushButton("Envoyer")
        layout.addWidget(self.send_btn)

        self.setLayout(layout)
        self.send_btn.clicked.connect(self.send_message)

        threading.Thread(target=self.listen, daemon=True).start()

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
                except:
                    msg = str(data)
                self.history.append(f"🟢 Reçu: {msg}")
            conn.close()

    def send_message(self):
        dest_port = self.target_input.text()
        msg = self.msg_input.text()
        if not dest_port or not msg:
            return
        payload = build_onion(dest_port, msg)
        try:
            with socket.socket() as s:
                s.connect(self.entree_routeur)
                s.sendall(payload)
            self.history.append(f"🔵 Envoyé à {dest_port} : {msg}")
            self.msg_input.clear()
        except Exception as e:
            self.history.append(f"Erreur d'envoi : {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Ex : python client_gui.py 5200
    local_port = int(sys.argv[1])
    entree = ('localhost', 5101)
    window = ClientGUI(local_port, entree)
    window.show()
    sys.exit(app.exec_())
