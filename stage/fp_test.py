import base64, hashlib, re, subprocess, sys, os

def tl(value):
    if len(value) < 254:
        head = bytes([len(value)])
    else:
        head = b"\xfe" + len(value).to_bytes(3, "little")
    body = head + value
    return body + b"\x00" * ((4 - len(body) % 4) % 4)

def der_ints(der):
    assert der[0] == 0x30, "not seq"
    i = 2 if der[1] < 0x80 else 2 + (der[1] & 0x7F)
    out = []
    while i < len(der) and len(out) < 2:
        assert der[i] == 0x02, "expected int at %d got %02x" % (i, der[i])
        i += 1
        ln = der[i]; i += 1
        if ln & 0x80:
            cnt = ln & 0x7F
            ln = int.from_bytes(der[i:i+cnt], "big"); i += cnt
        out.append(der[i:i+ln]); i += ln
    return out[0], out[1]

def fp_from_der(der):
    n, e = der_ints(der)
    d = hashlib.sha1(tl(n) + tl(e)).digest()
    return int.from_bytes(d[12:20], "little")

p = sys.argv[1]
der = subprocess.run(["openssl", "rsa", "-pubin", "-in", p, "-outform", "DER"],
                     capture_output=True).stdout
print("der len", len(der), der[:16].hex())
print("fp =", fp_from_der(der))
