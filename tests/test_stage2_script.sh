#!/usr/bin/env bash
# Этап 2: параметр --script
cd "$(dirname "$0")/.." || exit 1
PY=${PYTHON:-python3}
run() { echo; echo "\$ $PY src/emulator.py $*"; "$PY" src/emulator.py "$@" < /dev/null 2>&1; echo "[код возврата: $?]"; }
run --script scripts/stage2_ok.emu      # скрипт без ошибок
run --script scripts/stage2_error.emu   # остановка на первой ошибке
run --script scripts/no_such.emu        # скрипт не найден
