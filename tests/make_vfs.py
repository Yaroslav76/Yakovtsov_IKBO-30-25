"""Создаёт тестовые VFS-архивы в папке tests/vfs/.

Запуск: python3 tests/make_vfs.py
"""
import os
import zipfile

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vfs")
DATE = (2026, 1, 1, 0, 0, 0)
CUT_BYTES = 30


def build(name, files, dirs=()):
    """Создаёт ZIP-архив с указанными файлами и каталогами."""
    with zipfile.ZipFile(
        os.path.join(OUT, name), "w", zipfile.ZIP_DEFLATED
    ) as archive:
        for directory in dirs:
            info = zipfile.ZipInfo(directory.rstrip("/") + "/", DATE)
            archive.writestr(info, b"")
        for path, data in files.items():
            archive.writestr(zipfile.ZipInfo(path, DATE), data)


def lines(count, prefix="line"):
    """Возвращает count строк вида '<prefix> <номер>' как bytes."""
    text = "".join(f"{prefix} {i}\n" for i in range(1, count + 1))
    return text.encode()


def make_valid():
    """Создаёт корректные архивы: minimal, files и deep."""
    build("minimal.zip", {"hello.txt": "Hello, VFS!\n".encode()})
    build("files.zip", {
        "readme.txt": "Это VFS с несколькими файлами.\n".encode(),
        "log.txt": lines(25, "запись журнала"),
        "short.txt": b"one\ntwo\nthree\n",
        "no_newline.txt": b"first\nlast without newline",
        ".hidden": b"secret\n",
        "logo.bin": bytes(range(256)),
    }, dirs=["empty/"])
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


def make_broken():
    """Создаёт некорректные источники: не ZIP и повреждённый ZIP."""
    not_zip = os.path.join(OUT, "not_a_zip.zip")
    with open(not_zip, "wb") as f:
        f.write("Это обычный текст, а не ZIP-архив\n".encode())
    with open(os.path.join(OUT, "minimal.zip"), "rb") as src:
        data = src.read()
    with open(os.path.join(OUT, "corrupt.zip"), "wb") as dst:
        dst.write(data[:-CUT_BYTES])


def main():
    """Создаёт все тестовые архивы и печатает их список."""
    os.makedirs(OUT, exist_ok=True)
    make_valid()
    make_broken()
    print("Готово:", ", ".join(sorted(os.listdir(OUT))))


if __name__ == "__main__":
    main()