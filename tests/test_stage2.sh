#!/usr/bin/env bash
# Проверка параметров командной строки (этап 2). Запуск: bash tests/test_stage2.sh
cd "$(dirname "$0")/.." || exit 1
PY=${PYTHON:-python3}
run() { echo; echo "\$ $PY emulator.py $*"; "$PY" emulator.py "$@" < /dev/null 2>&1; echo "[код возврата: $?]"; }

run                                              # без параметров
run --vfs tests/vfs/minimal.zip                      # только --vfs
run --script scripts/stage2_ok.emu               # только --script
run --vfs tests/vfs/minimal.zip --script scripts/stage2_ok.emu # оба параметра
run --script scripts/stage2_error.emu            # ошибка внутри скрипта
run --script scripts/no_such_script.emu          # скрипт не найден
run --unknown                                    # неизвестный параметр
