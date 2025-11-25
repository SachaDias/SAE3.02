import mysql.connector

# À ADAPTER SELON TON ENVIRONNEMENT
DB_CFG = dict(user='saeuser', password='unmotdepassefiable', host='localhost', database='sae3')

# Exemple de configuration : 3 routeurs (tu peux modifier ici)
routeurs = [
    {'nom': 'R1', 'ip': 'localhost', 'port': 5101, 'clef': 'clef1'},
    {'nom': 'R2', 'ip': 'localhost', 'port': 5103, 'clef': 'clef2'},
    {'nom': 'R3', 'ip': 'localhost', 'port': 5105, 'clef': 'clef3'},
]

def reset_routeurs_table():
    conn = mysql.connector.connect(**DB_CFG)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM routeurs;")
    for r in routeurs:
        cursor.execute(
            "INSERT INTO routeurs (nom, ip, port, clef) VALUES (%s, %s, %s, %s)",
            (r['nom'], r['ip'], r['port'], r['clef'])
        )
    conn.commit()
    cursor.close()
    conn.close()
    print(f"Table routeurs mise à jour ({len(routeurs)} entrées).")

if __name__ == "__main__":
    reset_routeurs_table()
