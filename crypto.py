import msgpack
import rijndael
import base64
import os

def new_key():
    return base64.b64encode(os.urandom(24))

def clean_udid(s):
    return "".join(chr(ord(c) - 10) for c in s[6::4][:int(s[:4], 16)]).replace("-", "").encode("ascii")

def decrypt_cbc(s, iv, key):
    p = b"".join(rijndael.decrypt(key, bytes(s[i:i+len(iv)])) for i in range(0, len(s), len(iv)))
    return bytes((iv+s)[i] ^ p[i] for i in range(len(p)))

def encrypt_cbc(s, iv, key):
    if len(s) % 32:
        s += b"\x00" * (32 - (len(s) % 32))
    out = [iv]
    for i in range(0, len(s), 32):
        blk = bytes(s[i+j] ^ out[-1][j] for j in range(32))
        out.append(rijndael.encrypt(key, blk))
    return b"".join(out[1:])

def unpack_from_network(data, udid):
    iv = clean_udid(udid)
    reply = base64.b64decode(data)

    crypted_payload = reply[:-32]
    key = reply[-32:]

    plain = decrypt_cbc(crypted_payload, iv, key).rstrip(b"\x00")
    payload = msgpack.unpackb(base64.b64decode(plain), encoding="utf8")
    return payload

def pack_for_network(data, udid, key=None):
    iv = clean_udid(udid)

    if key is None:
        key = new_key()

    payload_mp = base64.b64encode(msgpack.packb(data))
    crypted_payload = base64.b64encode(encrypt_cbc(payload_mp, iv, key) + key)

    return crypted_payload
