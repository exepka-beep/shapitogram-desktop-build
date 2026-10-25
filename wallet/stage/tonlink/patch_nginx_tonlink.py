import io, sys

BLOCK = """    # ShapitoTON wallet API: привязка аккаунта по номеру+коду и поиск
    # аккаунта-владельца NFT (тот же бот, что раздаёт коды, 127.0.0.1:2800).
    location /tonlink/ {
        proxy_pass http://127.0.0.1:2800;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 20s;
    }

"""

TARGETS = [
    ("/etc/nginx/sites-available/shapitogram.conf", "    # SPA-фолбэк веб-клиента.\n"),
    ("/etc/nginx/sites-available/ton.shapitogram.xyz.conf", "    location / {\n        try_files $uri $uri/ /index.html;\n    }\n"),
]

for path, anchor in TARGETS:
    with io.open(path, encoding="utf-8") as f:
        text = f.read()
    if "/tonlink/" in text:
        print("skip (already patched):", path)
        continue
    if text.count(anchor) != 1:
        sys.exit("anchor not unique in %s: %r (%d)" % (path, anchor, text.count(anchor)))
    text = text.replace(anchor, BLOCK + anchor, 1)
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print("patched:", path)
