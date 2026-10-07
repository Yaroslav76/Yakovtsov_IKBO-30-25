#!/usr/bin/env bash
# Этап 3: минимальная VFS (один файл)
cd "$(dirname "$0")/.." || exit 1
PY=${PYTHON:-python3}
run() { echo; echo "\$ $PY src/emulator.py $*"; "$PY" src/emulator.py "$@" < /dev/null 2>&1; echo "[код возврата: $?]"; }
run --vfs tests/vfs/minimal.zip --script scripts/stage3_info.emu
