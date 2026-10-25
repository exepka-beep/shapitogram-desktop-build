import hashlib, subprocess, os, sys

def fp_of(path):
    txt = open(path, "r", errors="replace").read()
    if "PRIVATE" in txt:
        der = subprocess.run(["openssl", "rsa", "-in", path, "-pubout", "-outform", "DER"],
                             capture_output=True).stdout
    else:
        der = subprocess.run(["openssl", "rsa", "-pubin", "-in", path, "-outform", "DER"],
                             capture_output=True).stdout
    if not der:
        return None, 0
    return int.from_bytes(hashlib.sha256(der).digest()[-8:], "little"), len(der)

target = 13660490438243734116
for p in sys.argv[1:]:
    if not os.path.exists(p):
        continue
    fp, ln = fp_of(p)
    mark = "  <== MATCH" if fp == target else ""
    print("%-60s fp=%s len=%s%s" % (p, fp, ln, mark))
