# ShapitoGram — заметки проекта

Форк tdesktop/Telegram со своим сервером (`gramsrv`/`telesrv`), бренд **ShapitoGram**,
сервер `shapitogram.xyz` / `94.156.170.106`, порт MTProto **2398**.

## Карта репозитория (родитель воркспейса `shapitogram/`)

| Каталог | Что |
|---|---|
| `desktop/` | ПК-клиент: overlay поверх owpengram-desktop-client + конвейер GitHub Actions |
| `android/`, `ios/` | конвейеры сборки APK / IPA |
| `store-bot/` | **@shapitogrambot** — бот авторизации и магазин (Node 22 + grammY + Postgres) |
| `register-bot/` | бот регистрации (Python) |
| `bots/` | шаблоны ботов (shop/premium/getmyid) |
| `tools/vps.py` | SSH/SFTP к серверу через jump host |

## Доступ к серверу

```bash
export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'
P="C:/Users/rgali/AppData/Local/Programs/Python/Python310/Python.exe"
"$P" tools/vps.py run "<команда>" 120
"$P" tools/vps.py put "<локальный>" "//root/<путь>"    # двойной слэш обязателен
```

Порт 22 у провайдера Рафа режется → идём цепочкой `2.27.200.203:2222` → `94.156.170.106:22`.
Мы там **root**. Compose-проекты: `shapitogram-main` (сервер+админка+postgres+redis),
`shapito-store` (бот).

## Конвенции деплоя (проверено)

- 🔴 `docker restart` **НЕ** перечитывает `.env` — только `docker compose up -d --force-recreate`.
- `compose.yaml` перечисляет env явным списком; бот использует `env_file: .env`.
- Файлы править CRLF-безопасно; на сервере перед перезаписью — бэкап в `/root/backups/`.
- Пересборка бота: `cd /root/shapito-store && docker compose build && docker compose up -d --force-recreate`.
- Проверка живости бота: `curl -s http://127.0.0.1:2800/healthz` → `{"ok":true}`.

## Бот @shapitogrambot (store-bot)

- Работает через **обычный Telegram** (`api.telegram.org`), не через Bot API своего сервера.
  Свой сервер обслуживают `register-bot` и `shapito-botproxy` (расширитель Bot API на :2597).
- Хост-каталог `/root/shapito-store`, контейнер `shapitogram-store`, БД `grammystore`
  в кластере `shapitogram-main-postgres-1` (127.0.0.1:15432).
- Владелец: Раф, Telegram id **803482266** (`@memoswag`), из `OWNER_IDS`.
- **Обязательная подписка** (force-subscribe) реализована в коде: `subscribed()` +
  `subscriptionGate()` в `src/bot.js`, конфиг `REQUIRED_CHANNEL` / `REQUIRED_CHANNEL_URL`.
  Включена для канала **@shapitogram** (chat_id `-1004345842212`); бот там админ.
  Гейт стоит в middleware — покрывает все действия, а не только `/start`.

## Сборка ПК-клиента (desktop)

- Репо конвейера: `exepka-beep/shapitogram-desktop-build`. Драйвер — `desktop/tools/run_build.py`
  (`check` / `dispatch` / `status` / `watch` / `logs` / `download`), токен в `desktop/.gh_token`.
- Запускать с `export PYTHONPATH= PYTHONIOENCODING=utf-8 PYTHONUTF8=1 MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'`,
  Python — `C:/Users/rgali/.workbuddy-ai/binaries/python/envs/default/Scripts/python.exe`.
- Рабочие параметры: `--build-type Release --ffmpeg-fix login --parallel 2`
  (`parallel=2` обязателен: на 4+ MSVC падает `error C1060: compiler is out of heap space`).
- 🔴 Шаг `Locate the exe` в `.github/workflows/build-desktop.yml` искал `Telegram.exe`,
  а форк собирает `ShapitoGram.exe` → exe не находился, артефакт не заливался.
  Исправлено на поиск `ShapitoGram.exe` с фолбэком на `Telegram.exe`.
- Артефакт CI: `ShapitoGram-desktop-Release-x64` → внутри `ShapitoGram-Release-x64.exe` + `SHA256SUMS.txt`.
  Готовый exe кладём в `shapitogram/dist/desktop/` (сейчас ~217 МБ, хеш сверяем с `SHA256SUMS.txt`).
- Проверка бинарника: `desktop/scripts/scan_exe.py` (лежит в `scripts/`, НЕ в `tools/`) —
  `--absent Xtreegram --absent "XTree Gram" --absent 2.27.200.203 --present ShapitoGram --present 94.156.170.106`.
