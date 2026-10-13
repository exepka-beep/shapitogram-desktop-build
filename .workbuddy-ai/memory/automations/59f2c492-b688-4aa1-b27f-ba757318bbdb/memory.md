# Automation memory — проверка сборки ShapitoGram desktop

## 2026-10-12 (первый прогон автоматизации)

Проверял прогон #10 (run 38148881289, head d9bdbf47ae).

**Итог #10: failure, но НЕ из-за сборки.**
- Шаг 26 `Build` — **успешно**. `parallel=2` вылечил `error C1060: compiler is out of heap space`
  из прогона #9. Собран `ShapitoGram.exe` = 227 487 232 байта (~217 МиБ) в `TBuild/src/out/Release`.
- Упал шаг 27 `Locate the exe`: `FAIL: не нашёл Telegram.exe в ...` — шаг искал `Telegram.exe`,
  а форк собирает `ShapitoGram.exe`. Пустой `EXE` → шаг 28 `Scan` пропущен → шаг 29
  `Collect artifacts` напечатал «exe не собран — выкладывать нечего» → артефактов 0.
- Длительность #10: 14:51:31Z → 18:30:43Z (~3 ч 39 мин).

**Действие:** поправил `.github/workflows/build-desktop.yml` (шаг «Locate the exe.») —
теперь ищет `ShapitoGram.exe`, с фолбэком на `Telegram.exe`. Задиспатчен прогон #11
(run 38279515774, коммит aa48c82f5a, ffmpeg_fix=login, Release, parallel=2).

**Состояние на конец прогона:** #11 in_progress, шаг 5/30 `Checkout this repository`, прошло <1 мин.

## Что делать в следующий раз
- Артефакт #10 скачать невозможно (total_count: 0) — ждать #11.
- Если #11 упадёт на шаге 28 `Scan the exe` — смотреть, какие строки брендинга не сошлись
  (`--absent Xtreegram/"XTree Gram"/2.27.200.203`, `--present ShapitoGram/94.156.170.106`, `--info OwpenGram`).
- `tools/scan_exe.py` фактически лежит в `scripts/scan_exe.py` (в задании путь указан как `tools/`).

## Полезные факты
- Токен: `.gh_token` рядом с конвейером. Репо: exepka-beep/shapitogram-desktop-build @ main.
- Обязательное окружение: `export PYTHONPATH= PYTHONIOENCODING=utf-8 PYTHONUTF8=1 MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'`
- Python: `C:\Users\rgali\.workbuddy-ai\binaries\python\envs\default\Scripts\python.exe`
- `run_build.py` дефолты: `--ffmpeg-fix login`, `--build-type Release`, `--parallel 2`.
- Прогон #10 шёл с `ffmpeg_fix=login` (в логе: «добавлен --login к вызову build_ffmpeg_win.sh»).
