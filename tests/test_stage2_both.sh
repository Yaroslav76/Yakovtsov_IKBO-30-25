#!/usr/bin/env bash
# Этап 2: оба параметра, без параметров, неизвестный параметр
cd "$(dirname "$0")/.." || exit 1
PY=${PYTHON:-python3}
run() { echo; echo "\$ $PY src/emulator.py $*"; "$PY" src/emulator.py "$@" < /dev/null 2>&1; echo "[код возврата: $?]"; }
run                                                       # без параметров
run --vfs tests/vfs/deep.zip --script scripts/stage2_ok.emu   # оба параметра
run --unknown                                             # неизвестный параметр
