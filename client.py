import socket
import pickle

def get_route_from_master():
    with socket.socket() as s:
        s.connect(("localhost", 5100))
        data = s.recv(4096)
        info = pickle.loads(data)
        return info["route"], info["keys"]

ADDR_LEN = 21

def xor_layer(data, key):
    return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])

def build_onion(msg, routeurs, keys):
    l = msg.encode()
    for (addr, port), k in reversed(list(zip(routeurs, keys))):
        l = xor_layer((f"{addr}:{port}".ljust(ADDR_LEN).encode() + l), k)
    return l

def main():
    routeurs, keys = get_route_from_master()
    msg = input("Message à envoyer : ")
    payload = build_onion(msg, routeurs, keys)
    with socket.socket() as s:
        s.connect(routeurs[0])
        s.send(payload)

if __name__ == "__main__":
    main()
