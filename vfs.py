import base64
import io
import os
import posixpath
import zipfile


class VFSError(Exception):
    class VFS:
        def __init__(self, name="default", source=None):
            self.name = name  # имя VFS (показывается в приглашении)
            self.source = source  # путь к ZIP или None
            self.root = {}

        # ---------- работа с путями ----------
        def path(self, cwd, text):
            """Превращает 'a/../b' в абсолютный путь вида '/b'."""
            full = posixpath.normpath(posixpath.join(cwd, text))
            return "/" + full.lstrip("/")

        def get(self, path):
            """Возвращает узел по абсолютному пути (dict или bytes)."""
            node = self.root
            for part in path.split("/"):
                if part == "":
                    continue
                if not isinstance(node, dict):
                    raise VFSError("Not a directory")
                if part not in node:
                    raise VFSError("No such file or directory")
                node = node[part]
            return node

        # ---------- изменение ----------
        def add(self, path, data=None):
            """Создаёт файл (data — bytes) или каталог (data=None), недостающие каталоги создаются."""
            *dirs, name = [p for p in path.split("/") if p]
            node = self.root
            for d in dirs:
                node = node.setdefault(d, {})
                if not isinstance(node, dict):
                    raise VFSError(f"'{d}' is a file, not a directory")
            if data is None:
                data = node.setdefault(name, {})
                if not isinstance(data, dict):
                    raise VFSError(f"'{name}' is a file, not a directory")
            elif isinstance(node.get(name), dict):
                raise VFSError(f"'{name}' is a directory, not a file")
            else:
                node[name] = data

        def move(self, src, dst):
            """Переносит узел src в dst (оба — абсолютные пути)."""
            dst_parent = self.get(posixpath.dirname(dst))
            if not isinstance(dst_parent, dict):
                raise VFSError("Not a directory")
            node = self.get(src)
            del self.get(posixpath.dirname(src))[posixpath.basename(src)]
            dst_parent[posixpath.basename(dst)] = node

        # ---------- сведения ----------
        def text(self, data):
            """Содержимое файла для вывода: текст, а двоичные данные — в base64."""
            try:
                return data.decode("utf-8")
            except UnicodeDecodeError:
                return base64.encodebytes(data).decode("ascii").rstrip()

        def stats(self, node=None):
            """-> (каталогов, файлов, байт) внутри node (по умолчанию — всей VFS)."""
            node = self.root if node is None else node
            dirs = files = size = 0
            for child in node.values():
                if isinstance(child, dict):
                    d, f, s = self.stats(child)
                    dirs, files, size = dirs + 1 + d, files + f, size + s
                else:
                    files, size = files + 1, size + len(child)
            return dirs, files, size

    def default_vfs():
        """VFS по умолчанию (создаётся в памяти, если --vfs не указан)."""
        vfs = VFS("default")
        vfs.add("/tmp")
        vfs.add("/etc/hostname", b"emulator\n")
        vfs.add("/home/user/readme.txt", "Добро пожаловать в VFS по умолчанию!\n".encode())
        vfs.add("/home/user/notes.txt", "".join(f"строка {i}\n" for i in range(1, 16)).encode())
        return vfs

    def load_zip(path):
        """Читает ZIP-архив в память. При ошибке бросает VFSError с понятным текстом."""
        try:
            with open(path, "rb") as f:
                raw = f.read()
        except FileNotFoundError:
            raise VFSError(f"файл не найден: {path}")
        except IsADirectoryError:
            raise VFSError(f"это каталог, а не ZIP-архив: {path}")
        except OSError as e:
            raise VFSError(f"не удалось прочитать '{path}': {e.strerror}")
        try:
            archive = zipfile.ZipFile(io.BytesIO(raw))
        except zipfile.BadZipFile:
            raise VFSError(f"неверный формат (не ZIP-архив): {path}")

        vfs = VFS(os.path.splitext(os.path.basename(path))[0] or "vfs", path)
        try:
            for info in archive.infolist():
                name = "/" + info.filename.replace("\\", "/").strip("/")
                if ".." in name.split("/"):
                    raise VFSError(f"недопустимый путь в архиве: {info.filename}")
                if info.is_dir():
                    vfs.add(name)
                else:
                    vfs.add(name, archive.read(info))
        except VFSError:
            raise
        except Exception as e:  # повреждённый или зашифрованный архив
            raise VFSError(f"архив повреждён или не поддерживается: {e}")
        return vfs