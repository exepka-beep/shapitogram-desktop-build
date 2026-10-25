"""Find RSA public keys (SPKI DER) inside a binary and print MTProto fingerprints.

MTProto fingerprint = SHA1(TL(n) || TL(e))[12:20] as little-endian int,
where TL(x) is an MTProto byte-string (length prefix + 4-byte padding).
"""
import hashlib
import sys

TARGET = 13660490438243734116
PAT = bytes.fromhex("30820122300d06092a864886f70d01010105000382010f003082010a0282010100")


def tl(value: bytes) -> bytes:
    if len(value) < 254:
        head = bytes([len(value)])
    else:
        head = b"\xfe" + len(value).to_bytes(3, "little")
    body = head + value
    return body + b"\x00" * ((4 - len(body) % 4) % 4)


def tlv(data: bytes, i: int):
    """Return (tag, value, next_index)."""
    tag = data[i]
    i += 1
    ln = data[i]
    i += 1
    if ln & 0x80:
        cnt = ln & 0x7F
        ln = int.from_bytes(data[i:i + cnt], "big")
        i += cnt
    return tag, data[i:i + ln], i + ln


def rsa_ints(der: bytes):
    """SPKI DER -> (n, e)."""
    tag, body, _ = tlv(der, 0)          # outer SEQUENCE
    assert tag == 0x30
    tag, alg, i = tlv(body, 0)          # AlgorithmIdentifier
    assert tag == 0x30
    tag, bits, i = tlv(body, i)         # BIT STRING
    assert tag == 0x03
    inner = bits[1:]                    # strip unused-bits byte
    tag, seq, _ = tlv(inner, 0)         # RSAPublicKey SEQUENCE
    assert tag == 0x30
    tag, n, j = tlv(seq, 0)
    assert tag == 0x02
    tag, e, _ = tlv(seq, j)
    assert tag == 0x02
    return n, e


def fingerprint(der: bytes) -> int:
    n, e = rsa_ints(der)
    d = hashlib.sha1(tl(n) + tl(e)).digest()
    return int.from_bytes(d[12:20], "little")


def main(path: str) -> None:
    data = open(path, "rb").read()
    found = {}
    start = 0
    while True:
        i = data.find(PAT, start)
        if i < 0:
            break
        der = data[i:i + 294]
        try:
            fp = fingerprint(der)
        except Exception as err:
            print("  parse error at %d: %s" % (i, err))
            start = i + 1
            continue
        found.setdefault(fp, (i, der))
        start = i + 1
    print("%s: %d bytes, %d unique keys" % (path, len(data), len(found)))
    for fp, (off, der) in found.items():
        mark = "  <== MATCH" if fp == TARGET else ""
        print("  offset=%d fp=%d 0x%016x%s" % (off, fp, fp, mark))
        if fp == TARGET:
            open("/tmp/granz-server-rsa.der", "wb").write(der)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        main(p)
