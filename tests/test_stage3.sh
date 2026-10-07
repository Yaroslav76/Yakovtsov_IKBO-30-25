#!/usr/bin/env bash
# Проверка работы с разными VFS (этап 3). Запуск: bash tests/test_stage3.sh
cd "$(dirname "$0")/.." || exit 1
PY=${PYTHON:-python3}
V=tests/vfs
run() { echo; echo "\$ $PY emulator.py $*"; "$PY" emulator.py "$@" < /dev/null 2>&1; echo "[код возврата: $?]"; }

run --script scripts/stage3_info.emu                              # VFS по умолчанию
run --vfs $V/minimal.zip --script scripts/stage3_info.emu         # минимальный
run --vfs $V/files.zip   --script scripts/stage3_info.emu         # несколько файлов
run --vfs $V/deep.zip    --script scripts/stage3_info.emu         # 3+ уровня вложенности
run --vfs $V/no_such.zip                                          # файл не найден
run --vfs $V/not_a_zip.zip                                        # неверный формат
run --vfs $V/corrupt.zip                                          # повреждённый архив
run --vfs tests                                                   # каталог вместо файла
run --vfs $V/deep.zip --script scripts/stage3_all.emu             # все команды этапов 1-3
