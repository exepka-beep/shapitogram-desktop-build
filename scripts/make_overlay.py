"""Собрать overlay ShapitoGram для десктопного клиента.

Берёт дерево XTree Gram (`E:\\xtreegram-build\\desktop` = форк
`owpengram/owpengram-desktop-client` @ d5a262f7ba с 93 незакоммиченными
локальными правками брендинга), перекрашивает его в ShapitoGram и
раскладывает в `desktop/files/` — зеркально путям внутри репозитория.

В CI эти файлы просто копируются поверх свежего клона owpengram
(см. `.github/workflows/build-desktop.yml`), ровно как в Android-конвейере.

Использование
-------------
    make_overlay.py                  # собрать overlay
    make_overlay.py --check          # только проверить готовый overlay

Отличия от Android
------------------
* Иконки НЕ перекрашиваются: у нас нет своего логотипа, а по решению
  заказчика нужен «логотип как у обычного телеграма». Поэтому файлы
  `Resources/OwpenGram/art/*` и `Resources/OwpenGram/icons/*` берутся из
  оригинальных каталогов `Resources/art/` и `Resources/icons/`, которые в
  форке остались нетронутыми (их XTree Gram не правил).
* `Telegram/build/prepare/prepare.py` НЕ берётся из рабочего дерева: там
  лежат локальные костыли под Git Bash на Windows (снос `BASH_FUNC_*`,
  `XTREE_KSTAGE`). В CI они не нужны и вредны. prepare.py обрабатывается
  отдельно — см. `fix_prepare.py`.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys

SRC = "E:/xtreegram-build/desktop"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "files"))

# Порядок важен: сначала самые длинные и специфичные, иначе `Xtreegram`
# съест начало `Xtreegram Desktop` и получится `ShapitoGram Desktop` с
# лишним хвостом.
RULES = [
    ("Xtreegram Desktop", "ShapitoGram Desktop"),
    ("XtreegramDesktop", "ShapitoGramDesktop"),
    ("Xtreegram Lite", "ShapitoGram Lite"),
    ("Xtreegram Link", "ShapitoGram Link"),
    ("com.xtreegram.Xtreegram", "com.shapitogram.ShapitoGram"),
    ("org.xtreegram.desktop", "org.shapitogram.desktop"),
    ("XTree Gram", "ShapitoGram"),
    ("XTREEGRAM", "SHAPITOGRAM"),
    ("Xtreegram", "ShapitoGram"),
    ("xtreegram", "shapitogram"),
    # адрес сервера XTree Gram -> наш
    ("2.27.200.203", "94.156.170.106"),
]

# Файлы, которые обрабатываются отдельно и в общий overlay не идут.
HANDLED_SEPARATELY = {
    "Telegram/build/prepare/prepare.py",
}

TEXT_SUFFIXES = (
    ".cpp", ".h", ".hpp", ".c", ".txt", ".strings", ".rc", ".plist",
    ".xml", ".desktop", ".service", ".ps1", ".sh", ".py", ".cmake",
    ".json", ".in", ".txt", ".qrc",
)


def git_modified(root):
    """Список изменённых/новых файлов относительно HEAD."""
    result = subprocess.run(
        ["git", "-C", root, "status", "--porcelain"],
        capture_output=True, text=True, check=True,
    )
    paths = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        status, _, path = line[:2], line[2], line[3:]
        path = path.strip().strip('"')
        if status.strip() == "??" and ".bak" in path:
            continue
        paths.append(path)
    return paths


def is_text(path):
    return path.lower().endswith(TEXT_SUFFIXES)


def apply_rules(text):
    for src, dst in RULES:
        text = text.replace(src, dst)
    return text


# Мастер-логотип Telegram 1024x1024 (круглый значок с самолётиком). В форке
# аналогом был `OwpenGram/icons/logo_1024.png`, из которого их
# `generate_icons.py` нарезал остальные размеры.
TELEGRAM_MASTER_LOGO = "Telegram/Resources/art/icon_round512@2x.png"

# Файлы `OwpenGram/icons/logo_*` в оригинальном tdesktop не существуют — это
# добавка форка. Большинство из них лишь исходники для `generate_icons.py`
# (в сборке не участвуют), но `logo_1024_qr_white.png` реально попадает в
# ресурсы как `:/gui/art/logo_qr_big.png` и рисуется в центре QR-кода
# (`intro/intro_qr.cpp:627`, на прозрачном фоне). Поэтому всем им выдаём
# телеграмный мастер-логотип.
ICON_OVERRIDES = {
    "Telegram/Resources/OwpenGram/icons/logo_1024.png": TELEGRAM_MASTER_LOGO,
    "Telegram/Resources/OwpenGram/icons/logo_1000_1000.png": TELEGRAM_MASTER_LOGO,
    "Telegram/Resources/OwpenGram/icons/logo_500_500.png": TELEGRAM_MASTER_LOGO,
    "Telegram/Resources/OwpenGram/icons/logo_debug_1024.png": TELEGRAM_MASTER_LOGO,
    "Telegram/Resources/OwpenGram/icons/logo_1024_qr.png": TELEGRAM_MASTER_LOGO,
    "Telegram/Resources/OwpenGram/icons/logo_1024_qr_big.png": TELEGRAM_MASTER_LOGO,
    "Telegram/Resources/OwpenGram/icons/logo_1024_qr_white.png": TELEGRAM_MASTER_LOGO,
}


def icon_source_for(rel):
    """Куда смотреть за оригинальной телеграмной иконкой.

    `Resources/OwpenGram/art/icon48_debug@2x.png` -> `Resources/art/icon48@2x.png`
    `Resources/OwpenGram/icons/plane_white.svg`   -> `Resources/icons/plane_white.svg`
    """
    if rel in ICON_OVERRIDES:
        return ICON_OVERRIDES[rel]
    if rel.startswith("Telegram/Resources/OwpenGram/art/"):
        name = os.path.basename(rel)
        # _debug-варианты в оригинале не существуют — берём обычный
        name = name.replace("_debug", "")
        return "Telegram/Resources/art/" + name
    if rel.startswith("Telegram/Resources/OwpenGram/icons/"):
        name = os.path.basename(rel)
        return "Telegram/Resources/icons/" + name
    return None


def build():
    if not os.path.isdir(SRC):
        print("FAIL: нет дерева %s" % SRC)
        return 1

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)

    modified = git_modified(SRC)
    written, icons, skipped, missing = [], [], [], []

    for rel in modified:
        if rel in HANDLED_SEPARATELY:
            skipped.append(rel)
            continue

        src_path = os.path.join(SRC, rel.replace("/", os.sep))
        if not os.path.isfile(src_path):
            missing.append(rel)
            continue

        dst_path = os.path.join(OUT, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)

        icon_src = icon_source_for(rel)
        if icon_src is not None and not is_text(rel):
            origin = os.path.join(SRC, icon_src.replace("/", os.sep))
            if not os.path.isfile(origin):
                missing.append("%s (нет оригинала %s)" % (rel, icon_src))
                continue
            shutil.copy2(origin, dst_path)
            icons.append((rel, icon_src))
            continue

        if is_text(rel):
            with open(src_path, "rb") as handle:
                raw = handle.read()
            text = raw.decode("utf-8", errors="surrogateescape")
            new = apply_rules(text)
            with open(dst_path, "wb") as handle:
                handle.write(new.encode("utf-8", errors="surrogateescape"))
            written.append(rel)
        else:
            shutil.copy2(src_path, dst_path)
            written.append(rel)

    print("перекрашено текстовых файлов : %d" % len(written))
    print("иконок из оригинального art  : %d" % len(icons))
    print("пропущено (обрабатываются отдельно): %s" % ", ".join(skipped) or "—")
    if missing:
        print("\nНЕ НАЙДЕНО (%d):" % len(missing))
        for rel in missing:
            print("   %s" % rel)

    # ключевые файлы, без которых overlay бессмысленен
    must = [
        "Telegram/SourceFiles/core/branding.h",
        "Telegram/SourceFiles/owpengram/owpengram_servers.cpp",
        "Telegram/CMakeLists.txt",
    ]
    bad = [rel for rel in must if not os.path.isfile(
        os.path.join(OUT, rel.replace("/", os.sep)))]
    if bad:
        print("\nFAIL: в overlay нет обязательных файлов: %s" % ", ".join(bad))
        return 1

    leftovers = check()
    if leftovers:
        print("\nFAIL: остатки старого бренда в overlay:")
        for rel, hits in leftovers:
            print("   %s: %s" % (rel, ", ".join(sorted(hits))))
        return 1

    print("\noverlay готов: %s" % OUT)
    return 0


def check():
    """Найти остатки XTree Gram в готовом overlay."""
    leftovers = []
    patterns = {
        "Xtreegram": re.compile(r"Xtreegram", re.I),
        "XTree Gram": re.compile(r"XTree\s*Gram", re.I),
        "2.27.200.203": re.compile(r"2\.27\.200\.203"),
        "org.xtreegram": re.compile(r"org\.xtreegram", re.I),
    }
    for root, _, names in os.walk(OUT):
        for name in names:
            path = os.path.join(root, name)
            if not is_text(path):
                continue
            with open(path, "rb") as handle:
                text = handle.read().decode("utf-8", errors="surrogateescape")
            hits = {label for label, rx in patterns.items() if rx.search(text)}
            if hits:
                leftovers.append((os.path.relpath(path, OUT).replace(os.sep, "/"),
                                  hits))
    return leftovers


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="только проверить готовый overlay")
    args = parser.parse_args()

    if args.check:
        if not os.path.isdir(OUT):
            print("FAIL: overlay не собран (%s)" % OUT)
            return 1
        leftovers = check()
        if leftovers:
            print("FAIL: остатки старого бренда:")
            for rel, hits in leftovers:
                print("   %s: %s" % (rel, ", ".join(sorted(hits))))
            return 1
        print("overlay чист.")
        return 0

    return build()


if __name__ == "__main__":
    sys.exit(main())
