#!/usr/bin/env bash
# Этап 2: параметр --vfs (запуск: bash tests/)
cd "$(dirname "$0")/.." || exit 1
PY=${PYTHON:-python3}
run() { echo; echo "\$ $PY src/emulator.py $*"; "$PY" src/emulator.py "$@" < /dev/null 2>&1; echo "[код возврата: $?]"; }
run --vfs tests/vfs/minimal.zip   # корректный путь
run --vfs tests/vfs/no_such.zip   # путь неверный
