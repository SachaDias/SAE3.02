import socket

ROUTERS = [("localhost", 5001), ("localhost", 5002), ("localhost", 5003)]
ROUTER_KEYS = [b'clef1', b'clef2', b'clef3']
ADDR_LEN = 21

def xor_layer(data, key):
    return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])

def build_onion(msg, routeurs, keys):
    l = msg.encode()
    for (addr, port), k in reversed(list(zip(routeurs, keys))):
        l = xor_layer((f"{addr}:{port}".ljust(ADDR_LEN).encode() + l), k)
    return l

def main():
    msg = input("Message à envoyer : ")
    payload = build_onion(msg, ROUTERS, ROUTER_KEYS)
    with socket.socket() as s:
        s.connect(ROUTERS[0])
        s.send(payload)

if __name__ == "__main__":
    main()
