#!/usr/bin/env python3
"""Удалить .workbuddy-ai из публичного репозитория сборки.

Файлы памяти проекта (.workbuddy-ai/memory/*.md) уехали в публичный
exepka-beep/shapitogram-desktop-build вместе с пайплайном: build_manifest()
обходит весь каталог desktop/ и не исключал эту папку. Там адреса серверов,
SSH-порты и пароли.

push_to_github.py строит дерево поверх base_tree, поэтому просто убрать файлы
из манифеста мало — их надо удалить явной записью с sha=null.

Скрипт делает один коммит, который вычищает весь префикс .workbuddy-ai.
"""

from __future__ import annotations

import json
import pathlib
import urllib.error
import urllib.request

OWNER = "exepka-beep"
REPO = "shapitogram-desktop-build"
BRANCH = "main"
PREFIX = ".workbuddy-ai"
API = "https://api.github.com"

TOKEN = (pathlib.Path(__file__).resolve().parent / ".gh_token").read_text(
    encoding="utf-8").strip()


def api(path: str, method: str = "GET", payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(API + path, data=data, method=method)
    req.add_header("Authorization", "token " + TOKEN)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "shapitogram-cleanup")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:400]}")


def main() -> int:
    ref = api(f"/repos/{OWNER}/{REPO}/git/ref/heads/{BRANCH}")
    head = ref["object"]["sha"]
    commit = api(f"/repos/{OWNER}/{REPO}/git/commits/{head}")
    base_tree = commit["tree"]["sha"]

    tree = api(f"/repos/{OWNER}/{REPO}/git/trees/{base_tree}?recursive=1")
    blobs = [e["path"] for e in tree["tree"]
             if e["type"] == "blob" and e["path"].startswith(PREFIX)]
    if not blobs:
        print("нечего удалять: в дереве нет", PREFIX)
        return 0

    print("удаляю файлов:", len(blobs))
    for p in blobs:
        print("  -", p)

    entries = [{"path": p, "mode": "100644", "type": "blob", "sha": None} for p in blobs]
    new_tree = api(f"/repos/{OWNER}/{REPO}/git/trees", "POST",
                   {"base_tree": base_tree, "tree": entries})
    new_commit = api(f"/repos/{OWNER}/{REPO}/git/commits", "POST", {
        "message": "Убрать .workbuddy-ai: файлы памяти не должны попадать в публичный репозиторий",
        "tree": new_tree["sha"],
        "parents": [head],
    })
    api(f"/repos/{OWNER}/{REPO}/git/refs/heads/{BRANCH}", "PATCH",
        {"sha": new_commit["sha"], "force": False})

    print("коммит:", new_commit["sha"][:12])

    check = api(f"/repos/{OWNER}/{REPO}/git/trees/{new_commit['sha']}?recursive=1")
    left = [e["path"] for e in check["tree"] if e["path"].startswith(PREFIX)]
    print("осталось под префиксом:", left if left else "ничего")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
