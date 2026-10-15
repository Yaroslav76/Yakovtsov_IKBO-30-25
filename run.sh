#!/usr/bin/env bash
cd "$(dirname "$0")" || exit 1
[ -d tests/vfs ] || python3 tests/make_vfs.py > /dev/null
exec python3 src/emulator.py "$@"
