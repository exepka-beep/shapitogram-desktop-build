"""Проверить собранный ShapitoGram.exe на следы XTree Gram и наш бренд.

Зачем отдельный скрипт, а не grep в воркфлоу
-------------------------------------------
Строки в PE лежат в двух видах: узкие (ASCII/UTF-8) в коде и в некоторых
ресурсах и широкие (UTF-16LE) в ресурсах Windows и в литералах с `_q`/`u""`.
`grep -F` видит только узкие. Поэтому ищем обе кодировки.

Проверяем:
  * НЕ должно быть — `Xtreegram`, `XTree Gram`, `2.27.200.203`;
  * должно быть — `ShapitoGram` и наш адрес сервера;
  * `OwpenGram` — только справка: это имя каталога ресурсов
    (`Resources/OwpenGram/...`) в путях внутри бинарника, пользователю оно не
    показывается, а ломать из-за него сборку смысла нет.

Использование
-------------
    scan_exe.py app.exe --absent Xtreegram --present ShapitoGram --present 1.2.3.4
"""

import argparse
import sys


def variants(needle):
    """Узкое и широкое представления строки."""
    data = needle.encode("utf-8")
    return {
        "utf-8": data,
        "utf-16le": needle.encode("utf-16-le"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe")
    parser.add_argument("--absent", action="append", default=[],
                        help="строки, которых быть не должно")
    parser.add_argument("--present", action="append", default=[],
                        help="строки, которые обязаны быть")
    parser.add_argument("--info", action="append", default=[],
                        help="строки только для справки")
    args = parser.parse_args()

    try:
        with open(args.exe, "rb") as handle:
            blob = handle.read()
    except OSError as error:
        print("FAIL: не могу прочитать %s: %s" % (args.exe, error))
        return 1

    print("%s (%.1f МБ)" % (args.exe, len(blob) / 1024.0 / 1024.0))
    failures = []

    if args.absent:
        print("\n--- не должно быть ---")
    for needle in args.absent:
        hits = []
        for label, raw in variants(needle).items():
            count = blob.count(raw)
            if count:
                hits.append("%s x%d" % (label, count))
        if hits:
            print("  НАЙДЕНО  %-24s %s" % (needle, ", ".join(hits)))
            failures.append(needle)
        else:
            print("  чисто    %-24s" % needle)

    if args.present:
        print("\n--- должно быть ---")
    for needle in args.present:
        hits = []
        for label, raw in variants(needle).items():
            count = blob.count(raw)
            if count:
                hits.append("%s x%d" % (label, count))
        if hits:
            print("  есть     %-24s %s" % (needle, ", ".join(hits)))
        else:
            print("  НЕТ      %-24s" % needle)
            failures.append(needle)

    for needle in args.info:
        total = sum(blob.count(raw) for raw in variants(needle).values())
        print("\n  справка  %-24s вхождений: %d" % (needle, total))

    if failures:
        print("\nFAIL: %s" % ", ".join(failures))
        return 1
    print("\nexe прошёл проверку.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
