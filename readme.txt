Système de routage en oignon distribué (SAE3.02)
Ce projet implémente un petit réseau anonyme avec :

un master (superviseur + BDD),

plusieurs routeurs virtuels,

plusieurs clients PyQt,

un routage en oignon avec chiffrement XOR symétrique par routeur.

Prérequis

Sur chaque machine (master, routeurs, clients) :

Python 3 (>= 3.10 recommandé)

Virtualenv (optionnel)

Bibliothèques Python :

mysql-connector-python

PyQt5

Sur la machine du master :

MariaDB/MySQL installé en local.

Installation typique :

text
python -m venv .venv
source .venv/bin/activate   # ou .venv\Scripts\activate sous Windows
pip install mysql-connector-python PyQt5
2. Base de données MariaDB
2.1 Création

text
CREATE DATABASE sae3 CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE sae3;

CREATE TABLE routeurs (
    id   INT AUTO_INCREMENT PRIMARY KEY,
    nom  VARCHAR(50) NOT NULL,
    ip   VARCHAR(50) NOT NULL,
    port INT NOT NULL,
    clef VARCHAR(255) NOT NULL
);

CREATE TABLE routeurs_dyn (
    id    INT AUTO_INCREMENT PRIMARY KEY,
    nom   VARCHAR(50) NOT NULL,
    ip    VARCHAR(50) NOT NULL,
    port  INT NOT NULL,
    clef  VARCHAR(255) NOT NULL,
    alive TINYINT(1) NOT NULL DEFAULT 0
);

CREATE TABLE clients_dyn (
    id   INT AUTO_INCREMENT PRIMARY KEY,
    nom  VARCHAR(50) NOT NULL,
    port INT NOT NULL
);
​

2.2 Utilisateur BDD

text
CREATE USER 'saeuser'@'localhost' IDENTIFIED BY 'unmotdepassefiable';
GRANT ALL PRIVILEGES ON sae3.* TO 'saeuser'@'localhost';
FLUSH PRIVILEGES;
​

Configuration des scripts

3.1 master.py

Rôle : serveur central + accès BDD + suivi des routeurs (alive) + réponses aux clients.

Configurer l’accès BDD :

text
DB_CFG = dict(
    user='saeuser',
    password='unmotdepassefiable',
    host='localhost',
    database='sae3'
)
Écoute réseau (toutes interfaces) :

text
s.bind(("", 5100))   # et non ("localhost", 5100)
Le master :

nettoie routeurs_dyn et clients_dyn au démarrage,

met à jour alive dans monitor_routers(),

renvoie seulement les routeurs avec alive=1 dans handle_ask_routers().

3.2 routeur.py

Rôle : routeur virtuel (déchiffre une couche, décide du prochain saut, ou livre le message final).​

Config BDD et master :

text
DB_CFG = dict(
    user='saeuser',
    password='unmotdepassefiable',
    host='localhost',
    database='sae3'
)

MASTER_ADDR = ("IP_DU_MASTER", 5100)  # ex: ("192.168.1.64", 5100)
Écoute sur toutes les interfaces :

text
s.bind(("", port))   # et non ("localhost", port)
Enregistrement au master :

text
register_router(name, port, key)
# envoie REGISTER_ROUTER|name|localhost|port|clef
# le master remplace l’IP par remote_ip réel
Dernier routeur (centre de l’oignon = "IP_DEST:PORT_DEST:message") :

text
dest_ip, port_str, msg = text.split(":", 2)
dest_port = int(port_str)
s.connect((dest_ip, dest_port))


3.3 client.py

Rôle : client graphique PyQt (enregistrement, ASK_ROUTERS, construction oignon, réception).​

Adresse du master :

text
MASTER_ADDR = ("IP_DU_MASTER", 5100)
Écoute sur toutes interfaces pour recevoir le message final :

text
def listen(self):
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("", self.local_port))   # IMPORTANT
    s.listen(5)
    ...
Centre de l’oignon :

text
inner = f"{dest_ip}:{dest_port}:{msg}".encode()
Champs à saisir dans le client :

IP destinataire : IP de la machine où tourne le client cible (ex: 192.168.1.18),

Port destinataire : port du client cible (ex: 5600),

Route : noms des routeurs, ex: R1,R2,

Message : texte libre.

Procédure de lancement

Exemple de scénario :

Master + BDD : 192.168.1.64

Routeur R1 : 192.168.1.21, port 5101

Routeur R2 : 192.168.1.22, port 5102

Client A : 192.168.1.64, port 5200

Client B : 192.168.1.18, port 5600

4.1 Master

Sur 192.168.1.64 :

text
python master.py
Afficher : "Master prêt sur 5100".

4.2 Routeurs

Sur 192.168.1.21 :

text
python routeur.py 5101 R1
Sur 192.168.1.22 :

text
python routeur.py 5102 R2
Afficher : "Routeur R? prêt sur ?".

4.3 Vérification BDD

Sur le master, dans MariaDB :

text
USE sae3;
SELECT id, nom, ip, port, alive FROM routeurs_dyn;
R1 et R2 doivent être présents avec alive=1.

4.4 Clients

Sur 192.168.1.64 :

text
python client.py 5200 CLIENT_A
Sur 192.168.1.18 :

text
python client.py 5600 CLIENT_B
Les deux doivent afficher "En attente de messages...".

Envoi d’un message

Exemple : CLIENT_A → CLIENT_B via R1,R2

Dans CLIENT_A :

Rafraîchir routeurs (bouton).

IP destinataire : 192.168.1.18

Port destinataire : 5600

Route : R1,R2

Message : salut

Cliquer "Envoyer".

Chemin :

CLIENT_A construit un oignon avec centre "192.168.1.18:5600:salut" et l’envoie à R1.

R1 déchiffre, trouve R2 et relaie.

R2 voit "0.0.0.0:0000", déchiffre le centre, se connecte à (192.168.1.18, 5600) et envoie "salut".

CLIENT_B affiche "Reçu: salut".

Points à adapter pour ton environnement

IP du master

Partout (clients, routeurs) : MASTER_ADDR = ("IP_DU_MASTER", 5100).

bind des sockets

Master : s.bind(("", 5100))

Routeurs : s.bind(("", port))

Clients (listen) : s.bind(("", self.local_port))

BDD

Adapter DB_CFG si login/mot de passe différents.

Vérifier la présence de la colonne alive dans routeurs_dyn.

Réseau

Toutes les machines sur le même sous-réseau (ex: 192.168.1.x).

Pas de Wi‑Fi invité isolé.

Pare‑feu : autoriser les ports 5100, 510x, 52xx/56xx.

Tests rapides

Depuis le master :

nc -vz IP_ROUTEUR PORT_ROUTEUR

nc -vz IP_CLIENT PORT_CLIENT
Les deux doivent réussir pour que le routage en oignon fonctionne.
