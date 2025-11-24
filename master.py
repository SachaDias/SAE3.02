import socket
import threading

def distribute_keys(routeurs, master_socket):
    for r in routeurs:
        key = generate_key()
        master_socket.sendto(key, r['address'])

