"""Scan binaries for base64 RSA keys/certs and match MTProto fingerprint."""
import base64
import hashlib
import re
import subprocess
import sys
import tempfile
import os

TARGET = 13660490438243734116
RX = re.compile(rb"MII[A-Za-z0-9+/=]{60,}")


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


def spki_ints(der):
    tag, body, _ = tlv(der, 0)
    assert tag == 0x30
    tag, alg, i = tlv(body, 0)
    tag, bits, i = tlv(body, i)
    assert tag == 0x03
    tag, seq, _ = tlv(bits[1:], 0)
    tag, n, j = tlv(seq, 0)
    tag, e, _ = tlv(seq, j)
    return n, e


def fp_of_spki(der):
    n, e = spki_ints(der)
    d = hashlib.sha1(tl(n) + tl(e)).digest()
    return int.from_bytes(d[12:20], "little")


def cert_pubkey(der):
    """Extract SubjectPublicKeyInfo from a DER certificate via openssl."""
    with tempfile.NamedTemporaryFile(suffix=".der", delete=False) as f:
        f.write(der)
        path = f.name
    try:
        out = subprocess.run(["openssl", "x509", "-inform", "DER", "-in", path,
                              "-pubkey", "-noout", "-outform", "DER"],
                             capture_output=True).stdout
        return out or None
    finally:
        os.unlink(path)


def main(paths):
    hits = 0
    for path in paths:
        data = open(path, "rb").read()
        seen = set()
        for m in RX.finditer(data):
            raw = m.group(0)
            # trim padding noise: try longest valid base64 decode
            txt = raw.rstrip(b"=").decode("ascii", "ignore")
            for cut in range(0, 4):
                chunk = txt[:len(txt) - cut] if cut else txt
                chunk += "=" * ((4 - len(chunk) % 4) % 4)
                try:
                    der = base64.b64decode(chunk, validate=True)
                except Exception:
                    continue
                if len(der) < 100 or chunk in seen:
                    continue
                seen.add(chunk)
                fp = None
                try:
                    fp = fp_of_spki(der)
                except Exception:
                    pub = cert_pubkey(der)
                    if pub:
                        try:
                            fp = fp_of_spki(pub)
                        except Exception:
                            fp = None
                if fp is not None:
                    hits += 1
                    mark = "  <== MATCH" if fp == TARGET else ""
                    print("%s: len=%d fp=%d 0x%016x%s" % (path, len(der), fp, fp, mark))
                    if fp == TARGET:
                        spki = der
                        try:
                            spki_ints(der)
                        except Exception:
                            spki = cert_pubkey(der)
                        open("/tmp/granz-server-rsa.der", "wb").write(spki)
                        print("   saved -> /tmp/granz-server-rsa.der")
                break
    print("total parsed:", hits)


if __name__ == "__main__":
    main(sys.argv[1:])
