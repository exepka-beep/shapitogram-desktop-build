"""Вшить публичный RSA-ключ сервера ShapitoGram в десктопный клиент.

Зачем
-----
Сервер работает с `TELESRV_RSA_IDENTITY_MODE=generated`: ключевая пара
создаётся при первом старте и лежит в `server_state`. Заранее её знать нельзя,
поэтому ключ в клиент всегда подтягивается с работающего сервера:

    GET https://<домен>/owpengram/server-info
    {"rsa_public_key_pem": "...", "dc_id": 2, "name": "ShapitoGram", ...}

В desktop-клиенте ключ встроен в `kOfficialRsaPublicKey`
(`Telegram/SourceFiles/owpengram/owpengram_servers.cpp`) — это compile-time
константа, рантаймом она не переопределяется (в отличие от имени и логотипа).
Поэтому в CI её надо подменить перед сборкой, иначе рукопожатие провалится и
клиент повиснет на запуске.

Использование
-------------
    set_server_key.py --source <owpengram_servers.cpp> --pem <server-rsa-public.pem>
    set_server_key.py --source <owpengram_servers.cpp> --check --pem <...>

Код возврата ненулевой на любой ошибке: собрать клиент с чужим ключом хуже,
чем не собрать вовсе.
"""

import argparse
import os
import re
import sys

BEGIN = "-----BEGIN RSA PUBLIC KEY-----"
END = "-----END RSA PUBLIC KEY-----"

# Блок в C++ выглядит так (каждая строка PEM заканчивается \n\, последняя "_q;):
#
#     const auto kOfficialRsaPublicKey = u"\
#     -----BEGIN RSA PUBLIC KEY-----\n\
#     MIIBCgKCAQEA...\n\
#     -----END RSA PUBLIC KEY-----"_q;
BLOCK = re.compile(
    r'const auto kOfficialRsaPublicKey = u"\\\n'
    r"-----BEGIN [A-Z0-9 ]*PUBLIC KEY-----\\n\\\n"
    r"(?:[A-Za-z0-9+/=]+\\n\\\n)+"
    r'-----END [A-Z0-9 ]*PUBLIC KEY-----"_q;'
)


def read_pem(path):
    with open(path, "rb") as handle:
        raw = handle.read().decode("utf-8", errors="replace")
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if not lines or lines[0] != BEGIN or lines[-1] != END:
        raise ValueError(
            "не похоже на PEM публичного ключа: первая строка %r, последняя %r"
            % (lines[0] if lines else None, lines[-1] if lines else None)
        )
    body = "".join(lines[1:-1])
    if not body:
        raise ValueError("пустое тело ключа")
    return lines, body


def cpp_block(pem_lines):
    out = ['const auto kOfficialRsaPublicKey = u"\\']
    for line in pem_lines[:-1]:
        out.append("%s\\n\\" % line)
    out.append('%s"_q;' % pem_lines[-1])
    return "\n".join(out)


def body_of(cpp_text):
    """Тело ключа из C++-блока — без `\\n\\` и переводов строк.

    Сравнивать `body in text` напрямую нельзя: в C++ ключ разбит на строки по
    64 символа, между ними `\\n\\`, поэтому слитая строка тела в файле
    подстрокой не встречается. Первая версия скрипта на этом и спотыкалась.
    """
    match = re.search(
        r"-----BEGIN [A-Z0-9 ]*PUBLIC KEY-----\\n\\\n(.*?)-----END",
        cpp_text, re.S,
    )
    if not match:
        return None
    return match.group(1).replace("\\n\\\n", "").replace("\n", "")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="owpengram_servers.cpp")
    parser.add_argument("--pem", required=True, help="файл с публичным ключом")
    parser.add_argument("--check", action="store_true",
                        help="только проверить, что ключ уже вшит")
    args = parser.parse_args()

    if not os.path.isfile(args.source):
        print("FAIL: нет файла %s" % args.source)
        return 1
    try:
        pem_lines, body = read_pem(args.pem)
    except Exception as error:
        print("FAIL: %s: %s" % (type(error).__name__, error))
        return 1

    with open(args.source, "rb") as handle:
        text = handle.read().decode("utf-8", errors="surrogateescape")

    match = BLOCK.search(text)
    if not match:
        print("FAIL: в %s не нашёл блок kOfficialRsaPublicKey" % args.source)
        return 1

    current = match.group(0)
    if body_of(current) == body:
        print("ключ уже вшит (тело %d символов, %s...)" % (len(body), body[:24]))
        return 0

    if args.check:
        print("FAIL: в файле другой ключ — сборка ушла бы с чужим")
        return 1

    text = text[:match.start()] + cpp_block(pem_lines) + text[match.end():]
    with open(args.source, "wb") as handle:
        handle.write(text.encode("utf-8", errors="surrogateescape"))

    # Самопроверка: перечитываем файл и убеждаемся, что ключ на месте.
    with open(args.source, "rb") as handle:
        check = handle.read().decode("utf-8", errors="surrogateescape")
    again = BLOCK.search(check)
    if not again:
        print("FAIL: после подстановки блок kOfficialRsaPublicKey не читается")
        return 1
    if body_of(again.group(0)) != body:
        print("FAIL: тело ключа в файле не совпало с ожидаемым")
        return 1
    if again.group(0) != cpp_block(pem_lines):
        print("FAIL: блок в файле отличается от сгенерированного")
        return 1

    print("ключ вшит: тело %d символов, %s..." % (len(body), body[:24]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
