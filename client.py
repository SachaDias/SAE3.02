route_keys = [key_r1, key_r2, key_r3]  # clés reçues du master
route_addrs = [addr_r1, addr_r2, addr_r3]
message = b"Message secret"
dest_addr = b"ADDR_CLIENTB"

layer = message
for key, addr in reversed(list(zip(route_keys, route_addrs))):
    layer = encrypt_layer(addr + layer, key)

