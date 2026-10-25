import hashlib, subprocess, sys

TARGET = 13660490438243734116

def tl(v):
    if len(v) < 254:
        head = bytes([len(v)])
    else:
        head = b"\xfe" + len(v).to_bytes(3, "little")
    body = head + v
    return body + b"\x00" * ((4 - len(body) % 4) % 4)

def tlv(d, i):
    tag = d[i]; i += 1
    ln = d[i]; i += 1
    if ln & 0x80:
        c = ln & 0x7F
        ln = int.from_bytes(d[i:i + c], "big"); i += c
    return tag, d[i:i + ln], i + ln

def ints(der):
    tag, body, _ = tlv(der, 0)
    assert tag == 0x30
    tag, first, i = tlv(body, 0)
    if tag == 0x30:                      # SPKI: alg then BIT STRING
        tag, bits, i = tlv(body, i)
        assert tag == 0x03
        return ints(bits[1:])
    assert tag == 0x02                   # PKCS#1: INTEGER n, INTEGER e
    tag, e, _ = tlv(body, i)
    assert tag == 0x02
    return first, e

p = sys.argv[1]
der = subprocess.run(["openssl", "rsa", "-pubin", "-in", p, "-outform", "DER"],
                     capture_output=True).stdout
n, e = ints(der)
fp = int.from_bytes(hashlib.sha1(tl(n) + tl(e)).digest()[12:20], "little")
print("der:", len(der), "n bits:", int.from_bytes(n, "big").bit_length(),
      "e:", int.from_bytes(e, "big"))
print("fingerprint:", fp, hex(fp))
print("MATCH" if fp == TARGET else "MISMATCH (server reports %d)" % TARGET)
