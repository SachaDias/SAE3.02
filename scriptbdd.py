import tkinter as tk
from tkinter import simpledialog, messagebox
import mysql.connector

DB_CFG = dict(user='saeuser', password='unmotdepassefiable', host='localhost', database='sae3')

def reset_routeurs_table(routeurs):
    conn = mysql.connector.connect(**DB_CFG)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM routeurs;")
    for r in routeurs:
        cursor.execute(
            "INSERT INTO routeurs (nom, ip, port, clef) VALUES (%s, %s, %s, %s)",
            (r['nom'], 'localhost', r['port'], r['clef'])
        )
    conn.commit()
    cursor.close()
    conn.close()

def ask_routeurs():
    nb = simpledialog.askinteger("Nombre", "Nombre de routeurs ?", minvalue=1, maxvalue=10)
    if not nb:
        return
    routeurs = []
    for i in range(nb):
        nom = simpledialog.askstring("Routeur", f"Nom du routeur {i+1} :")
        port = simpledialog.askinteger("Port", f"Port pour {nom} :", minvalue=1024, maxvalue=65535)
        clef = simpledialog.askstring("Clé", f"Clé pour {nom} :")
        if nom and port and clef:
            routeurs.append({'nom': nom, 'port': port, 'clef': clef})
        else:
            messagebox.showerror("Erreur", "Tous les champs sont obligatoires.")
            return
    reset_routeurs_table(routeurs)
    messagebox.showinfo("Succès", f"{len(routeurs)} routeurs insérés dans la BDD.")

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # fenêtre principale cachée, on utilise que les dialogs
    ask_routeurs()
    root.quit()
