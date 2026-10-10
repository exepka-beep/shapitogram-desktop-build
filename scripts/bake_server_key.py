"""Скачать `/owpengram/server-info` и вынуть из него публичный RSA-ключ.

Отдельный шаг от `set_server_key.py`, потому что у них разные причины падать:
здесь сеть и формат ответа, там — разбор C++ и подстановка. Смешивать их в
одном скрипте значит терять, что именно сломалось.

Сервер отдаёт:

    {"dc_id": 2, "name": "ShapitoGram", "has_icon": false,
     "rsa_public_key_pem": "-----BEGIN RSA PUBLIC KEY-----\\n...",
     "description": "..."}

Использование
-------------
    bake_server_key.py --url https://example.com/owpengram/server-info --out key.pem
"""

import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.request

BEGIN = "-----BEGIN RSA PUBLIC KEY-----"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="адрес /owpengram/server-info")
    parser.add_argument("--out", required=True, help="куда положить PEM")
    parser.add_argument("--insecure", action="store_true",
                        help="не проверять сертификат (только для отладки)")
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()

    context = ssl._create_unverified_context() if args.insecure else None
    try:
        with urllib.request.urlopen(args.url, timeout=args.timeout,
                                    context=context) as response:
            if response.status != 200:
                print("FAIL: сервер ответил HTTP %s" % response.status)
                return 1
            raw = response.read()
    except urllib.error.HTTPError as error:
        print("FAIL: HTTP %s на %s" % (error.code, args.url))
        return 1
    except Exception as error:
        print("FAIL: %s: %s" % (type(error).__name__, error))
        return 1

    try:
        info = json.loads(raw.decode("utf-8"))
    except Exception as error:
        print("FAIL: ответ не JSON: %s" % error)
        return 1

    pem = info.get("rsa_public_key_pem") or ""
    if BEGIN not in pem:
        print("FAIL: в ответе нет rsa_public_key_pem")
        return 1
    if "-----END RSA PUBLIC KEY-----" not in pem:
        print("FAIL: PEM обрезан — нет END-строки")
        return 1

    lines = [line for line in pem.strip().splitlines() if line.strip()]
    if len(lines) < 3:
        print("FAIL: в PEM всего %d строк" % len(lines))
        return 1

    with open(args.out, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(pem if pem.endswith("\n") else pem + "\n")

    print("сервер      : %s" % info.get("name"))
    print("dc_id       : %s" % info.get("dc_id"))
    print("описание    : %s" % (info.get("description") or "—"))
    print("строк в PEM : %d" % len(lines))
    print("записан в   : %s" % os.path.abspath(args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
