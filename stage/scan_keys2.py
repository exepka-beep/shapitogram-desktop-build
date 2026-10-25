"""Scan a binary for RSA public keys in PKCS#1 *and* SPKI DER form, print MTProto fingerprints."""
import hashlib
import sys

TARGET = 13660490438243734116
PKCS1 = bytes.fromhex("3082010a0282010100")
SPKI = bytes.fromhex("30820122300d06092a864886f70d01010105000382010f003082010a0282010100")


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


def ints_pkcs1(der):
    tag, body, _ = tlv(der, 0)
    assert tag == 0x30
    tag, n, j = tlv(body, 0)
    assert tag == 0x02
    tag, e, _ = tlv(body, j)
    assert tag == 0x02
    return n, e


def ints_spki(der):
    tag, body, _ = tlv(der, 0)
    tag, _alg, i = tlv(body, 0)
    tag, bits, i = tlv(body, i)
    assert tag == 0x03
    return ints_pkcs1(bits[1:])


def fp(n, e):
    d = hashlib.sha1(tl(n) + tl(e)).digest()
    return int.from_bytes(d[12:20], "little")


def scan(path):
    data = open(path, "rb").read()
    results = {}

    def walk(pat, size, parser, label):
        start = 0
        while True:
            i = data.find(pat, start)
            if i < 0:
                return
            der = data[i:i + size]
            try:
                n, e = parser(der)
                f = fp(n, e)
                results.setdefault(f, (label, i, der))
            except Exception:
                pass
            start = i + 1

    walk(PKCS1, 270, ints_pkcs1, "pkcs1")
    walk(SPKI, 294, ints_spki, "spki")
    print("%s: %d keys (pkcs1+spki)" % (path, len(results)))
    for f, (label, off, der) in sorted(results.items()):
        mark = "  <== MATCH" if f == TARGET else ""
        print("  %-5s off=%-9d fp=%-20d 0x%016x%s" % (label, off, f, f, mark))
        if f == TARGET:
            open("/tmp/granz-key.der", "wb").write(der)
            print("    saved /tmp/granz-key.der")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        scan(p)
