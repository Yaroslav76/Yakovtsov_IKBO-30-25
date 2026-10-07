#!/usr/bin/env bash
# Этап 3: VFS с вложенностью 3+ уровней и стартовый скрипт всех команд
cd "$(dirname "$0")/.." || exit 1
PY=${PYTHON:-python3}
run() { echo; echo "\$ $PY src/emulator.py $*"; "$PY" src/emulator.py "$@" < /dev/null 2>&1; echo "[код возврата: $?]"; }
run --vfs tests/vfs/deep.zip --script scripts/stage3_info.emu
run --vfs tests/vfs/deep.zip --script scripts/stage3_all.emu
