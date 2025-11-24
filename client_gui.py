import sys
import socket
import pickle
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit

ADDR_LEN = 21

def xor_layer(data, key):
    return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])

def get_route_from_master():
    with socket.socket() as s:
        s.connect(("localhost", 5100))
        data = s.recv(4096)
        info = pickle.loads(data)
        return info["route"], info["keys"]

def build_onion(msg, routeurs, keys):
    l = msg.encode()
    for (addr, port), k in reversed(list(zip(routeurs, keys))):
        l = xor_layer((f"{addr}:{port}".ljust(ADDR_LEN).encode() + l), k)
    return l

class ClientGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SAE3.02 - Client")
        self.layout = QVBoxLayout(self)
        self.info = QLabel("Saisis ton message à envoyer :")
        self.layout.addWidget(self.info)
        self.input = QLineEdit()
        self.layout.addWidget(self.input)
        self.button = QPushButton("Envoyer")
        self.layout.addWidget(self.button)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.layout.addWidget(self.log)
        self.button.clicked.connect(self.send_message)

    def send_message(self):
        msg = self.input.text()
        routeurs, keys = get_route_from_master()
        payload = build_onion(msg, routeurs, keys)
        self.log.append(f"Message (bytes) envoyé au premier routeur : {payload.hex()[:64]}...")
        try:
            with socket.socket() as s:
                s.connect(routeurs[0])
                s.send(payload)
            self.log.append("✅ Message envoyé !")
        except Exception as e:
            self.log.append(f"Erreur : {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ClientGUI()
    window.show()
    sys.exit(app.exec_())
