"""Clone the ShapitoGram iOS pipeline into ios-granz and rebrand it for GranzGram.

Rules (ordered):
  ShapitoGram -> GranzGram
  SHAPITOGRAM -> GRANZGRAM
  shapitogram -> granzgram
  then fix the host: granzgram.xyz -> granzgram.duckdns.org
  and the seed IP: 94.156.170.106 -> 31.77.10.62
"""
import os
import pathlib
import shutil

SRC = pathlib.Path(r"C:\Users\rgali\WorkBuddy AI\2026-09-20-16-06-24\shapitogram\ios")
DST = pathlib.Path(r"C:\Users\rgali\WorkBuddy AI\2026-09-20-16-06-24\shapitogram\ios-granz")

TEXT_EXT = {".py", ".sh", ".yml", ".yaml", ".md", ".patch", ".pem", ".json"}
SKIP_DIRS = {"__pycache__", ".git"}

REPL = [
    ("ShapitoGram", "GranzGram"),
    ("SHAPITOGRAM", "GRANZGRAM"),
    ("shapitogram", "granzgram"),
    ("granzgram.xyz", "granzgram.duckdns.org"),
    ("94.156.170.106", "31.77.10.62"),
]


def main():
    if DST.exists():
        shutil.rmtree(DST)
    for root, dirs, files in os.walk(SRC):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        rel = os.path.relpath(root, SRC)
        target_dir = DST if rel == "." else DST / rel
        target_dir.mkdir(parents=True, exist_ok=True)
        for name in files:
            src_file = pathlib.Path(root) / name
            new_name = name
            for a, b in REPL:
                new_name = new_name.replace(a, b)
            dst_file = target_dir / new_name
            if src_file.suffix.lower() in TEXT_EXT or src_file.name.startswith("."):
                try:
                    text = src_file.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    shutil.copy2(src_file, dst_file)
                    continue
                for a, b in REPL:
                    text = text.replace(a, b)
                dst_file.write_text(text, encoding="utf-8")
            else:
                shutil.copy2(src_file, dst_file)
    print("cloned to", DST)
    for p in sorted(DST.rglob("*")):
        if p.is_file():
            print("  ", p.relative_to(DST))


if __name__ == "__main__":
    main()
