#!/usr/bin/env python3
"""Создаёт тестовые VFS-архивы в tests/vfs/."""
"""Запуск: python3 tests/make_vfs.py."""

import os
import zipfile

"""Папка для создаваемых архивов."""
OUT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "vfs"
)

"""Фиксированная дата для воспроизводимости архивов."""
DATE = (2026, 1, 1, 0, 0, 0)


"""Создаёт ZIP-архив с указанными файлами и каталогами."""
def build(name, files, dirs=()):
    with zipfile.ZipFile(
        os.path.join(OUT, name), "w", zipfile.ZIP_DEFLATED
    ) as z:
        for d in dirs:
            z.writestr(
                zipfile.ZipInfo(d.rstrip("/") + "/", DATE), b""
            )
        for path, data in files.items():
            z.writestr(zipfile.ZipInfo(path, DATE), data)


"""Создаёт указанное количество строк."""
def lines(n, prefix="line"):
    return "".join(
        f"{prefix} {i}\n" for i in range(1, n + 1)
    ).encode()


os.makedirs(OUT, exist_ok=True)


"""Минимальный архив: один файл."""
build("minimal.zip", {
    "hello.txt": "Hello, VFS!\n".encode()
})


"""Архив с несколькими файлами."""
build("files.zip", {
    "readme.txt": "Это VFS с несколькими файлами.\n".encode(),
    "log.txt": lines(25, "запись журнала"),
    "short.txt": b"one\ntwo\nthree\n",
    "no_newline.txt": b"first\nlast without newline",
    ".hidden": b"secret\n",
    "logo.bin": bytes(range(256)),
}, dirs=["empty/"])


"""Архив с глубокой вложенностью каталогов."""
build("deep.zip", {
    "README.md": b"# deep\n",
    "a/b/c/d/deep.txt": "Файл на 5-м уровне\n".encode(),
    "a/b/c/note.txt": lines(12, "note"),
    "a/b/mid.txt": b"mid\n",
    "projects/app/src/main.py": b"print('hi')\n",
    "projects/app/src/util.py": b"def f():\n    return 1\n",
    "projects/app/README.md": b"app\n",
    "projects/lib/readme.txt": b"lib\n",
    "etc/config/app.conf": b"debug=true\n",
}, dirs=["projects/empty_dir/", "tmp/"])


"""Создаёт файл, который не является ZIP-архивом."""
with open(
    os.path.join(OUT, "not_a_zip.zip"), "wb"
) as f:
    f.write("Это обычный текст, а не ZIP-архив\n".encode())


"""Создаёт повреждённую копию минимального архива."""
with open(os.path.join(OUT, "minimal.zip"), "rb") as src:
    with open(
        os.path.join(OUT, "corrupt.zip"), "wb"
    ) as dst:
        dst.write(src.read()[:-30])


print(
    "Готово:", ", ".join(sorted(os.listdir(OUT)))
)