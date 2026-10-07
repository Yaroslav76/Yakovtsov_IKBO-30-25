#!/usr/bin/env bash
# Этап 3: ошибки загрузки VFS и VFS по умолчанию
cd "$(dirname "$0")/.." || exit 1
PY=${PYTHON:-python3}
run() { echo; echo "\$ $PY src/emulator.py $*"; "$PY" src/emulator.py "$@" < /dev/null 2>&1; echo "[код возврата: $?]"; }
run --script scripts/stage3_info.emu      # VFS по умолчанию (--vfs не указан)
run --vfs tests/vfs/no_such.zip       # файл не найден
run --vfs tests/vfs/not_a_zip.zip     # неверный формат
run --vfs tests/vfs/corrupt.zip       # повреждённый архив
run --vfs tests                       # каталог вместо файла
