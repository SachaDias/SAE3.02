import sys
import socket
import threading
import pickle
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QTextEdit

from mysql.connector import connect

DB_CFG = dict(user='saeuser', password='unmotdepassefiable', host='localhost', database='sae3')

def get_routeurs_and_keys():
    conn = connect(**DB_CFG)
    cursor = conn.cursor()
    cursor.execute("SELECT ip, port, clef FROM routeurs ORDER BY id")
    data = cursor.fetchall()
    conn.close()
    return [ (ip, int(port)) for ip, port, _ in data ], [ clef for _, _, clef in data ]

class MasterGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SAE3.02 - Master")
        self.layout = QVBoxLayout(self)
        self.label = QLabel("Connexions enregistrées :")
        self.layout.addWidget(self.label)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.layout.addWidget(self.log)
        self.run_server()

    def log_conn(self, text):
        self.log.append(text)

    def client_handler(self, conn, addr):
        self.log_conn(f"👤 Connexion client depuis {addr}")
        routers, keys = get_routeurs_and_keys()
        conn.send(pickle.dumps({"route": routers, "keys": keys}))
        conn.close()

    def run_server(self):
        def server_thread():
            s = socket.socket()
            s.bind(("localhost", 5100))
            s.listen()
            self.log_conn("Master serveur prêt sur port 5100")
            while True:
                conn, addr = s.accept()
                threading.Thread(target=self.client_handler, args=(conn, addr)).start()
        threading.Thread(target=server_thread, daemon=True).start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MasterGUI()
    window.show()
    sys.exit(app.exec_())
