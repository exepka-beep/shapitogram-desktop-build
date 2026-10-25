#!/usr/bin/env python3
"""Переписать .env TypoGram: свежие секреты, новый IP/бренд, панель наружу.

Исходник — скопированный с ShapitoGram .env. Скрипт идемпотентен: при повторном
запуске генерирует новые секреты только если попросить --rotate.
"""
from __future__ import annotations

import pathlib
import re
import secrets
import sys

ENV = pathlib.Path("/root/gramsrv/deploy/docker/.env")
CREDS = pathlib.Path("/root/typogram-credentials.txt")
IP = "177.3.222.2"


def rnd(n: int = 28) -> str:
    return secrets.token_urlsafe(48).replace("-", "").replace("_", "")[:n]


def main() -> int:
    text = ENV.read_text(encoding="utf-8")
    rotate = "--rotate" in sys.argv

    existing = dict(
        re.findall(r"^([A-Z0-9_]+)=(.*)$", text, re.M)
    )

    def pick(key: str, gen, current_ok: bool = False) -> str:
        old = existing.get(key, "")
        if old and not rotate and current_ok:
            return old
        return gen()

    pw = pick("POSTGRES_PASSWORD", lambda: rnd(28))
    redis_pw = pick("TELESRV_REDIS_PASSWORD", lambda: rnd(28))
    api_token = pick("TELESRV_ADMIN_API_TOKEN", lambda: rnd(32))
    session_key = pick("TELESRV_ADMIN_SESSION_KEY", lambda: rnd(40))
    admin_pw = pick("TELESRV_ADMIN_UI_PASSWORD", lambda: rnd(16))
    turn_secret = pick("TELESRV_TURN_SECRET", lambda: rnd(32))
    otp_secret = pick("TELESRV_OTP_WEBHOOK_SECRET", lambda: secrets.token_hex(24))
    dev_code = existing.get("TELESRV_DEV_AUTH_CODE") or str(secrets.randbelow(90000000) + 10000000)

    values = {
        "COMPOSE_PROJECT_NAME": "typogram-main",
        "TELESRV_SERVER_BUILD_TARGET": "server",
        "POSTGRES_PASSWORD": pw,
        "TELESRV_POSTGRES_DSN": f"postgres://telesrv:{pw}@127.0.0.1:15432/telesrv_main?sslmode=disable",
        "TELESRV_REDIS_PASSWORD": redis_pw,
        "TELESRV_ADMIN_API_TOKEN": api_token,
        "TELESRV_ADMIN_SESSION_KEY": session_key,
        "TELESRV_ADMIN_UI_PASSWORD": admin_pw,
        "TELESRV_ADMIN_UI_USERS": f"owner:{admin_pw}:*",
        "TELESRV_TURN_SECRET": turn_secret,
        "TELESRV_OTP_WEBHOOK_SECRET": otp_secret,
        "TELESRV_DEV_AUTH_CODE": dev_code,
        "TELESRV_ADVERTISE_IP": IP,
        "TELESRV_SFU_ADVERTISE_IP": IP,
        "TELESRV_TURN_ADVERTISE_IP": IP,
        "TELESRV_LIVESTREAM_RTMP_URL": f"rtmp://{IP}:2400",
        "TELESRV_PUBLIC_BASE_URL": f"http://{IP}",
        "TELESRV_PUBLIC_WEB_BASE_URL": f"http://{IP}",
        "TELESRV_PUBLIC_APP_SCHEME": "typogram",
        "TELESRV_WEBSOCKET_ALLOWED_ORIGINS": "",
        "TELESRV_OWPENGRAM_SERVER_NAME": "TypoGram",
        "TELESRV_OWPENGRAM_SERVER_DESCRIPTION": "Self-hosted TypoGram server.",
        "TELESRV_OWPENGRAM_SERVER_ICON": "",
        "TELESRV_CUSTOM_FRAGMENT_ENABLE": "false",
        "TELESRV_CUSTOM_FRAGMENT_PUBLIC_BASE_URL": f"http://{IP}",
        "TELESRV_ADMIN_BIND_IP": "0.0.0.0",
        "TELESRV_ADMIN_LISTEN_HOST": "0.0.0.0",
        "TELESRV_ADMIN_UI_TOKEN": "",
        "TELESRV_AUTOJOIN_CHANNEL_IDS": "",
        "TELESRV_VERIFICATION_ALLOW_USER_TARGETS": "true",
    }

    for key, value in values.items():
        if re.search(rf"^{re.escape(key)}=.*$", text, re.M):
            text = re.sub(rf"^{re.escape(key)}=.*$", f"{key}={value}", text, count=1, flags=re.M)
        else:
            if not text.endswith("\n"):
                text += "\n"
            text += f"{key}={value}\n"

    ENV.write_text(text, encoding="utf-8")

    CREDS.write_text(
        "TypoGram credentials\n"
        f"admin panel : http://{IP}:2600\n"
        f"login       : owner\n"
        f"password    : {admin_pw}\n"
        f"engine api  : http://127.0.0.1:2599 (Bearer {api_token})\n"
        f"postgres    : telesrv / {pw} (127.0.0.1:15432)\n"
        f"redis       : {redis_pw} (127.0.0.1:16379)\n"
        f"otp webhook : {otp_secret}\n"
        f"dev code    : {dev_code}\n",
        encoding="utf-8",
    )
    CREDS.chmod(0o600)

    print("env written")
    print("admin login: owner /", admin_pw)
    print("creds file :", CREDS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
