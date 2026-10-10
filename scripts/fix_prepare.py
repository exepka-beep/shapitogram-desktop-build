"""Починить стадию `ffmpeg` в `Telegram/build/prepare/prepare.py`.

Зачем
-----
Сборка Windows в форке `owpengram/owpengram-desktop-client` падает на стадии
`Libraries/ffmpeg`:

    [25/32](Libraries/ffmpeg): FAILED
    cl.exe is unable to create an executable file.
    C compiler test failed.

Из-за fail-fast это отменяет всю матрицу воркфлоу, поэтому ни один прогон
`win.yml` в форке не доходил до конца (46 прогонов — 0 успешных). Ровно та же
стена у upstream `telegramdesktop/tdesktop` в его собственном `win.yml`.

Форк стоит на tdesktop 7.2.2, а upstream с тех пор поменял стадию `ffmpeg`:

    форк:      git clone -b n6.1.6 ... ; bash ../patches/build_ffmpeg_win.sh
    upstream:  git clone -b n8.1.3 ... ; bash --login ../patches/build_ffmpeg_win.sh
               (и убрана строка, добавлявшая %VCToolsInstallDir%\\bin\\Hostx64\\x64 в PATH)

Варианты фикса
--------------
`login`    — минимальный: внутри стадии ffmpeg убрать строку с
             `VCToolsInstallDir` и добавить `--login` к bash. Версию ffmpeg и
             коммит патчей не трогаем. Меньше всего риска.
`upstream` — повторить upstream целиком: ffmpeg `n8.1.3` + `--login`.
             Требует ещё и свежий `ffmpeg.patch`, потому что патч
             версионно-зависимый — воркфлоу подкладывает его из коммита
             `desktop-app/patches@aec474953ff7ee9b6e4cd9b8658288ea86d124f3`.

Почему правим только стадию ffmpeg
----------------------------------
Строка с `VCToolsInstallDir` встречается в prepare.py дважды: в `libvpx` (стр.
~1082) и в `ffmpeg` (~1187). Стадия `libvpx` в логе упавшего прогона прошла
успешно («0 Error(s)»), поэтому её не трогаем — правим ровно блок ffmpeg.

Коммит патчей целиком обновлять НЕЛЬЗЯ: между `73a88cda` (форк) и `aec47495`
(upstream) в `desktop-app/patches` поменялось 187 файлов, включая весь набор
патчей Qt — на исходниках 7.2.2 они не наложатся.

Использование
-------------
    fix_prepare.py --prepare <путь к prepare.py> --variant login
    fix_prepare.py --prepare <путь к prepare.py> --variant upstream
"""

import argparse
import os
import re
import sys

STAGE_OPEN = re.compile(r"^stage\('ffmpeg', \"\"\"\n", re.M)
STAGE_CLOSE = "\n\"\"\")"

# Строка, которая ставит MSVC-компилятор в начало PATH. Для задания x64_x86
# путь HostX64\x64 указывает на x64-компилятор, а собирается x86 — то есть
# строка ещё и неверна. upstream её убрал.
VCTOOLS_LINE = re.compile(
    r'^[ \t]*if not "%VCToolsInstallDir%"=="" set "PATH=[^\n]*\n',
    re.M,
)

BASH_FFMPEG = re.compile(
    r"^(?P<indent>[ \t]*)bash \.\./patches/build_ffmpeg_win\.sh[ \t]*$",
    re.M,
)

FFMPEG_CLONE = re.compile(
    r"git clone -b n6\.1\.6 https://github\.com/FFmpeg/FFmpeg\.git ffmpeg",
)

# Патч ffmpeg версионно-зависимый, поэтому при переходе на n8.1.3 надо взять и
# свежий `ffmpeg.patch` со скриптом сборки. Клонируем `desktop-app/patches`
# целиком нельзя (разошлось 187 файлов), поэтому подкладываем ровно эти два
# файла прямо в стадию ffmpeg — ПОСЛЕ того, как стадия `patches` отработала
# (иначе её `git clone` их перезапишет).
PATCHES_REF = "aec474953ff7ee9b6e4cd9b8658288ea86d124f3"
PATCH_URL = ("https://raw.githubusercontent.com/desktop-app/patches/%s/" % PATCHES_REF)
APPLY_PATCH = re.compile(
    r"^(?P<indent>[ \t]*)git apply \.\./patches/ffmpeg\.patch[ \t]*$", re.M
)

OLD_FFMPEG = "n6.1.6"
NEW_FFMPEG = "n8.1.3"


def stage_bounds(text):
    """Границы блока `stage('ffmpeg', \"\"\"...\"\"\")` в тексте файла."""
    match = STAGE_OPEN.search(text)
    if not match:
        return None
    start = match.end()
    end = text.find(STAGE_CLOSE, start)
    if end < 0:
        return None
    return start, end


def apply_to_block(block, variant):
    changes = []
    if VCTOOLS_LINE.search(block):
        block = VCTOOLS_LINE.sub("", block)
        changes.append("убран PATH-хак VCToolsInstallDir (HostX64\\x64)")
    else:
        changes.append("ВНИМАНИЕ: строки VCToolsInstallDir в стадии ffmpeg нет")

    if re.search(r"^[ \t]*bash --login \.\./patches/build_ffmpeg_win\.sh[ \t]*$",
                 block, re.M):
        changes.append("bash --login уже стоит")
    else:
        block, count = BASH_FFMPEG.subn(
            lambda m: "%sbash --login ../patches/build_ffmpeg_win.sh"
                      % m.group("indent"),
            block,
        )
        if count == 0:
            return None, ["FAIL: не нашёл вызов build_ffmpeg_win.sh в стадии ffmpeg"]
        changes.append("добавлен --login к вызову build_ffmpeg_win.sh (%d шт.)" % count)

    if variant == "upstream":
        if FFMPEG_CLONE.search(block):
            block = FFMPEG_CLONE.sub(
                "git clone -b %s https://github.com/FFmpeg/FFmpeg.git ffmpeg"
                % NEW_FFMPEG,
                block,
            )
            changes.append("ffmpeg %s -> %s" % (OLD_FFMPEG, NEW_FFMPEG))
        elif re.search(r"git clone -b %s " % re.escape(NEW_FFMPEG), block):
            changes.append("ffmpeg уже %s" % NEW_FFMPEG)
        else:
            return None, ["FAIL: не нашёл git clone ffmpeg в стадии ffmpeg"]

        if "PATCHES_REF" in block:
            changes.append("свежий ffmpeg-патч уже подкладывается")
        else:
            if not APPLY_PATCH.search(block):
                return None, ["FAIL: не нашёл `git apply ../patches/ffmpeg.patch`"]

            def inject(match):
                indent = match.group("indent")
                return (
                    '%spowershell -Command "iwr -OutFile ../patches/ffmpeg.patch '
                    '%sffmpeg.patch"\n'
                    '%spowershell -Command "iwr -OutFile '
                    '../patches/build_ffmpeg_win.sh %sbuild_ffmpeg_win.sh"\n'
                    "%s# PATCHES_REF %s\n"
                    "%s"
                ) % (indent, PATCH_URL, indent, PATCH_URL,
                     indent, PATCHES_REF, match.group(0))

            block = APPLY_PATCH.sub(inject, block)
            changes.append(
                "подложен свежий ffmpeg.patch + build_ffmpeg_win.sh "
                "из patches@%s" % PATCHES_REF[:8]
            )

    return block, changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", required=True, help="путь к prepare.py")
    parser.add_argument("--variant", choices=("login", "upstream"),
                        default="login")
    args = parser.parse_args()

    path = args.prepare
    if not os.path.isfile(path):
        print("FAIL: нет файла %s" % path)
        return 1

    with open(path, "rb") as handle:
        text = handle.read().decode("utf-8", errors="surrogateescape")
    original = text

    bounds = stage_bounds(text)
    if bounds is None:
        print("FAIL: не нашёл блок stage('ffmpeg', ...) в %s" % path)
        return 1
    start, end = bounds

    new_block, changes = apply_to_block(text[start:end], args.variant)
    if new_block is None:
        print("FAIL (вариант %s):" % args.variant)
        for line in changes:
            print("   %s" % line)
        return 1

    text = text[:start] + new_block + text[end:]
    if text == original:
        print("prepare.py уже пропатчен, менять нечего.")
    else:
        with open(path, "wb") as handle:
            handle.write(text.encode("utf-8", errors="surrogateescape"))
        print("prepare.py пропатчен (вариант %s):" % args.variant)
    for line in changes:
        print("   %s" % line)

    # Самопроверка — только внутри стадии ffmpeg, чтобы не задеть libvpx.
    with open(path, "rb") as handle:
        check = handle.read().decode("utf-8", errors="surrogateescape")
    bounds = stage_bounds(check)
    block = check[bounds[0]:bounds[1]]
    bad = []
    if re.search(r"^[ \t]*bash \.\./patches/build_ffmpeg_win\.sh", block, re.M):
        bad.append("в стадии ffmpeg остался вызов без --login")
    if "VCToolsInstallDir" in block:
        bad.append("в стадии ffmpeg осталась строка VCToolsInstallDir")
    if args.variant == "upstream" and OLD_FFMPEG in block:
        bad.append("в стадии ffmpeg остался ffmpeg %s" % OLD_FFMPEG)
    if bad:
        print("\nFAIL: %s" % "; ".join(bad))
        return 1

    print("проверка пройдена (libvpx не тронут: %s)"
          % ("да" if "VCToolsInstallDir" in check else "нет, его там и не было"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
