#!/usr/bin/env bash
# Этап 3: VFS с несколькими файлами
cd "$(dirname "$0")/.." || exit 1
python3 tests/make_vfs.py > /dev/null
PY=${PYTHON:-python3}
run() { echo; echo "\$ $PY src/emulator.py $*"; "$PY" src/emulator.py "$@" < /dev/null 2>&1; echo "[код возврата: $?]"; }
run --vfs tests/vfs/files.zip --script scripts/stage3_info.emu
