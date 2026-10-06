import argparse
import calendar
import datetime
import os
import posixpath
import shlex
import sys

from vfs import VFSError, default_vfs, load_zip


def out(text=""):
    print(text, flush=True)


def err(text):
    print(text, file=sys.stderr, flush=True)


class Exit(Exception):
    # ост эмулятора

    def __init__(self, code):
        self.code = code


def cmd_ls(shell, args):
    """ls [-l] [-a] [путь ...]"""
    letters = "".join(a[1:] for a in args if a.startswith("-"))
    bad = [c for c in letters if c not in "la"]
    if bad:
        err(f"ls: invalid option -- '{bad[0]}'")
        return 2
    paths = [a for a in args if not a.startswith("-")] or ["."]
    status = 0
    for i, path in enumerate(paths):
        try:
            node = shell.vfs.get(shell.vfs.path(shell.cwd, path))
        except VFSError as e:
            err(f"ls: cannot access '{path}': {e}")
            status = 2
            continue
        if len(paths) > 1:  # несколько путей — печатаем заголовки
            out(("\n" if i else "") + f"{path}:")
        if isinstance(node, dict):
            items = {name: node[name] for name in sorted(node, key=str.lower)
                     if "a" in letters or not name.startswith(".")}
            if "a" in letters:
                items = {".": node, "..": node, **items}
        else:
            items = {path: node}  # ls для файла показывает сам файл
        if "l" in letters:
            for name, child in items.items():
                kind, size = ("d", 4096) if isinstance(child, dict) else ("-", len(child))
                out(f"{kind} {size:>5} {name}")
        else:
            out("  ".join(items))
    return status


def cmd_cd(shell, args):
    """cd [путь]  (без аргумента — корень VFS)"""
    if len(args) > 1:
        err("cd: too many arguments")
        return 1
    target = args[0] if args else "/"
    full = shell.vfs.path(shell.cwd, target)
    try:
        node = shell.vfs.get(full)
    except VFSError as e:
        err(f"cd: {target}: {e}")
        return 1
    if not isinstance(node, dict):
        err(f"cd: {target}: Not a directory")
        return 1
    shell.cwd = full
    return 0


def cmd_cal(shell, args):
    """cal | cal ГОД | cal МЕСЯЦ ГОД"""
    if len(args) > 2 or not all(a.isdigit() for a in args):
        err("cal: usage: cal [[месяц] год]  (числа)")
        return 1
    calendar.setfirstweekday(6)  # неделя начинается с воскресенья, как в UNIX
    today = datetime.date.today()
    month, year = today.month, today.year
    if len(args) == 1:
        year, month = int(args[0]), None
    elif len(args) == 2:
        month, year = int(args[0]), int(args[1])
    if not 1 <= year <= 9999:
        err(f"cal: year '{year}' not in range 1..9999")
        return 1
    if month is not None and not 1 <= month <= 12:
        err(f"cal: {month} is not a month number (1..12)")
        return 1
    text = calendar.month(year, month) if month else calendar.calendar(year)
    for line in text.rstrip().split("\n"):
        out(line.rstrip())
    return 0


def cmd_tail(shell, args):
    """tail [-n N] файл ...  (по умолчанию — последние 10 строк)"""
    count = 10
    if args[:1] == ["-n"]:
        if len(args) < 2:
            err("tail: option requires an argument -- 'n'")
            return 1
        if not args[1].isdigit():
            err(f"tail: invalid number of lines: '{args[1]}'")
            return 1
        count, args = int(args[1]), args[2:]
    if not args:
        err("tail: missing file operand")
        return 1
    status = 0
    for i, name in enumerate(args):
        try:
            node = shell.vfs.get(shell.vfs.path(shell.cwd, name))
        except VFSError as e:
            err(f"tail: cannot open '{name}' for reading: {e}")
            status = 1
            continue
        if isinstance(node, dict):
            err(f"tail: error reading '{name}': Is a directory")
            status = 1
            continue
        if len(args) > 1:  # несколько файлов — печатаем заголовки
            out(("\n" if i else "") + f"==> {name} <==")
        lines = shell.vfs.text(node).splitlines()
        for line in lines[-count:] if count else []:
            out(line)
    return status


def cmd_mv(shell, args):
    """mv источник назначение  (если назначение — каталог, источник переносится внутрь)"""
    if len(args) < 2:
        err("mv: missing file operand" if not args else f"mv: missing destination file operand after '{args[0]}'")
        return 1
    if len(args) > 2:
        err("mv: too many arguments")
        return 1
    src, dst = args
    vfs = shell.vfs
    src_full = vfs.path(shell.cwd, src)
    dst_full = vfs.path(shell.cwd, dst)
    try:
        node = vfs.get(src_full)
    except VFSError as e:
        err(f"mv: cannot stat '{src}': {e}")
        return 1
    if src_full == "/":
        err("mv: cannot move the root directory")
        return 1
    try:  # назначение — существующий каталог: переносим внутрь него
        if isinstance(vfs.get(dst_full), dict):
            dst_full = posixpath.join(dst_full, posixpath.basename(src_full))
    except VFSError:
        pass
    if dst_full == src_full:
        err(f"mv: '{src}' and '{dst}' are the same file")
        return 1
    if dst_full.startswith(src_full + "/"):
        err(f"mv: cannot move '{src}' to a subdirectory of itself")
        return 1
    if shell.cwd == src_full or shell.cwd.startswith(src_full + "/"):
        err(f"mv: cannot move '{src}': it contains the current directory")
        return 1
    try:
        existing = vfs.get(dst_full)
    except VFSError:
        existing = None
    if existing is not None and (isinstance(existing, dict) or isinstance(node, dict)):
        err(f"mv: cannot overwrite '{dst}': already exists")  # заменять можно только файл файлом
        return 1
    try:
        vfs.move(src_full, dst_full)
    except VFSError as e:
        err(f"mv: cannot move '{src}' to '{dst}': {e}")
        return 1
    return 0


def cmd_exit(shell, args):
    """exit [код]"""
    if len(args) > 1:
        err("exit: too many arguments")
        return 1
    if args and not args[0].lstrip("-").isdigit():
        err(f"exit: {args[0]}: numeric argument required")
        return 2
    raise Exit(int(args[0]) & 0xFF if args else 0)


def cmd_vfs_info(shell, args):
    """Служебная команда: сведения о VFS."""
    if args:
        err("vfs-info: too many arguments")
        return 1
    dirs, files, size = shell.vfs.stats()
    out(f"name:   {shell.vfs.name}")
    out(f"source: {shell.vfs.source or '(в памяти, по умолчанию)'}")
    out(f"dirs: {dirs}, files: {files}, bytes: {size}")
    return 0


COMMANDS = {"ls": cmd_ls, "cd": cmd_cd, "cal": cmd_cal, "tail": cmd_tail,
            "mv": cmd_mv, "exit": cmd_exit, "vfs-info": cmd_vfs_info}


# ======================= оболочка =======================
class Shell:
    def __init__(self, vfs):
        self.vfs = vfs
        self.cwd = "/"

    def prompt(self):
        return f"{self.vfs.name}:{self.cwd}$ "

    def execute(self, line):
        """Разбирает и выполняет строку. Возвращает код возврата (0 — успех)."""
        try:
            # shlex понимает кавычки и комментарии (#), expandvars подставляет $HOME, ${USER} и т. п.
            words = [os.path.expandvars(w) for w in shlex.split(line, comments=True)]
        except ValueError as e:
            err(f"parse error: {e}")
            return 2
        if not words:
            return 0
        command = COMMANDS.get(words[0])
        if command is None:
            err(f"{words[0]}: command not found")
            return 127
        return command(self, words[1:])


def run_script(shell, path):
    """Выполняет стартовый скрипт, показывая ввод и вывод. Останавливается на первой ошибке.
    Строка вида '-команда' — ожидаемая ошибка: скрипт после неё продолжается (для демонстраций).
    Возвращает False, если скрипт не удалось прочитать."""
    try:
        with open(path, encoding="utf-8-sig") as f:
            lines = f.read().splitlines()
    except OSError as e:
        err(f"Ошибка: не удалось прочитать скрипт '{path}': {e.strerror}")
        return False
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        expected_error = line.startswith("-")
        if expected_error:
            line = line[1:]
        out(shell.prompt() + line)
        status = shell.execute(line)
        if status != 0 and expected_error:
            out(f"[ожидаемая ошибка, код {status}; скрипт продолжается]")
        elif status != 0:
            err(f"Скрипт остановлен: ошибка в строке {number} (код {status})")
            break
    return True


def repl(shell):
    """Интерактивный цикл: приглашение -> ввод -> выполнение."""
    from_terminal = sys.stdin.isatty()
    while True:
        try:
            line = input(shell.prompt())
        except EOFError:  # Ctrl+D
            out("exit")
            return 0
        except KeyboardInterrupt:  # Ctrl+C — отмена строки
            out()
            continue
        if not from_terminal:  # ввод из файла/канала: покажем введённую строку
            out(line)
        shell.execute(line)


def cmd_ls(shell, args):
    """ls [-l] [-a] [путь ...]"""
    letters = "".join(a[1:] for a in args if a.startswith("-"))
    bad = [c for c in letters if c not in "la"]
    if bad:
        err(f"ls: invalid option -- '{bad[0]}'")
        return 2
    paths = [a for a in args if not a.startswith("-")] or ["."]
    status = 0
    for i, path in enumerate(paths):
        try:
            node = shell.vfs.get(shell.vfs.path(shell.cwd, path))
        except VFSError as e:
            err(f"ls: cannot access '{path}': {e}")
            status = 2
            continue
        if len(paths) > 1:  # несколько путей — печатаем заголовки
            out(("\n" if i else "") + f"{path}:")
        if isinstance(node, dict):
            items = {name: node[name] for name in sorted(node, key=str.lower)
                     if "a" in letters or not name.startswith(".")}
            if "a" in letters:
                items = {".": node, "..": node, **items}
        else:
            items = {path: node}  # ls для файла показывает сам файл
        if "l" in letters:
            for name, child in items.items():
                kind, size = ("d", 4096) if isinstance(child, dict) else ("-", len(child))
                out(f"{kind} {size:>5} {name}")
        else:
            out("  ".join(items))
    return status


def cmd_cd(shell, args):
    """cd [путь]  (без аргумента — корень VFS)"""
    if len(args) > 1:
        err("cd: too many arguments")
        return 1
    target = args[0] if args else "/"
    full = shell.vfs.path(shell.cwd, target)
    try:
        node = shell.vfs.get(full)
    except VFSError as e:
        err(f"cd: {target}: {e}")
        return 1
    if not isinstance(node, dict):
        err(f"cd: {target}: Not a directory")
        return 1
    shell.cwd = full
    return 0


def cmd_cal(shell, args):
    """cal | cal ГОД | cal МЕСЯЦ ГОД"""
    if len(args) > 2 or not all(a.isdigit() for a in args):
        err("cal: usage: cal [[месяц] год]  (числа)")
        return 1
    calendar.setfirstweekday(6)  # неделя начинается с воскресенья, как в UNIX
    today = datetime.date.today()
    month, year = today.month, today.year
    if len(args) == 1:
        year, month = int(args[0]), None
    elif len(args) == 2:
        month, year = int(args[0]), int(args[1])
    if not 1 <= year <= 9999:
        err(f"cal: year '{year}' not in range 1..9999")
        return 1
    if month is not None and not 1 <= month <= 12:
        err(f"cal: {month} is not a month number (1..12)")
        return 1
    text = calendar.month(year, month) if month else calendar.calendar(year)
    for line in text.rstrip().split("\n"):
        out(line.rstrip())
    return 0


def cmd_tail(shell, args):
    """tail [-n N] файл ...  (по умолчанию — последние 10 строк)"""
    count = 10
    if args[:1] == ["-n"]:
        if len(args) < 2:
            err("tail: option requires an argument -- 'n'")
            return 1
        if not args[1].isdigit():
            err(f"tail: invalid number of lines: '{args[1]}'")
            return 1
        count, args = int(args[1]), args[2:]
    if not args:
        err("tail: missing file operand")
        return 1
    status = 0
    for i, name in enumerate(args):
        try:
            node = shell.vfs.get(shell.vfs.path(shell.cwd, name))
        except VFSError as e:
            err(f"tail: cannot open '{name}' for reading: {e}")
            status = 1
            continue
        if isinstance(node, dict):
            err(f"tail: error reading '{name}': Is a directory")
            status = 1
            continue
        if len(args) > 1:  # несколько файлов — печатаем заголовки
            out(("\n" if i else "") + f"==> {name} <==")
        lines = shell.vfs.text(node).splitlines()
        for line in lines[-count:] if count else []:
            out(line)
    return status


def cmd_mv(shell, args):
    """mv источник назначение  (если назначение — каталог, источник переносится внутрь)"""
    if len(args) < 2:
        err("mv: missing file operand" if not args else f"mv: missing destination file operand after '{args[0]}'")
        return 1
    if len(args) > 2:
        err("mv: too many arguments")
        return 1
    src, dst = args
    vfs = shell.vfs
    src_full = vfs.path(shell.cwd, src)
    dst_full = vfs.path(shell.cwd, dst)
    try:
        node = vfs.get(src_full)
    except VFSError as e:
        err(f"mv: cannot stat '{src}': {e}")
        return 1
    if src_full == "/":
        err("mv: cannot move the root directory")
        return 1
    try:  # назначение — существующий каталог: переносим внутрь него
        if isinstance(vfs.get(dst_full), dict):
            dst_full = posixpath.join(dst_full, posixpath.basename(src_full))
    except VFSError:
        pass
    if dst_full == src_full:
        err(f"mv: '{src}' and '{dst}' are the same file")
        return 1
    if dst_full.startswith(src_full + "/"):
        err(f"mv: cannot move '{src}' to a subdirectory of itself")
        return 1
    if shell.cwd == src_full or shell.cwd.startswith(src_full + "/"):
        err(f"mv: cannot move '{src}': it contains the current directory")
        return 1
    try:
        existing = vfs.get(dst_full)
    except VFSError:
        existing = None
    if existing is not None and (isinstance(existing, dict) or isinstance(node, dict)):
        err(f"mv: cannot overwrite '{dst}': already exists")  # заменять можно только файл файлом
        return 1
    try:
        vfs.move(src_full, dst_full)
    except VFSError as e:
        err(f"mv: cannot move '{src}' to '{dst}': {e}")
        return 1
    return 0


def cmd_exit(shell, args):
    """exit [код]"""
    if len(args) > 1:
        err("exit: too many arguments")
        return 1
    if args and not args[0].lstrip("-").isdigit():
        err(f"exit: {args[0]}: numeric argument required")
        return 2
    raise Exit(int(args[0]) & 0xFF if args else 0)


def cmd_vfs_info(shell, args):
    """Служебная команда: сведения о VFS."""
    if args:
        err("vfs-info: too many arguments")
        return 1
    dirs, files, size = shell.vfs.stats()
    out(f"name:   {shell.vfs.name}")
    out(f"source: {shell.vfs.source or '(в памяти, по умолчанию)'}")
    out(f"dirs: {dirs}, files: {files}, bytes: {size}")
    return 0


COMMANDS = {"ls": cmd_ls, "cd": cmd_cd, "cal": cmd_cal, "tail": cmd_tail,
            "mv": cmd_mv, "exit": cmd_exit, "vfs-info": cmd_vfs_info}


# ======================= оболочка =======================
class Shell:
    def __init__(self, vfs):
        self.vfs = vfs
        self.cwd = "/"

    def prompt(self):
        return f"{self.vfs.name}:{self.cwd}$ "

    def execute(self, line):
        """Разбирает и выполняет строку. Возвращает код возврата (0 — успех)."""
        try:
            # shlex понимает кавычки и комментарии (#), expandvars подставляет $HOME, ${USER} и т. п.
            words = [os.path.expandvars(w) for w in shlex.split(line, comments=True)]
        except ValueError as e:
            err(f"parse error: {e}")
            return 2
        if not words:
            return 0
        command = COMMANDS.get(words[0])
        if command is None:
            err(f"{words[0]}: command not found")
            return 127
        return command(self, words[1:])


def run_script(shell, path):
    """Выполняет стартовый скрипт, показывая ввод и вывод. Останавливается на первой ошибке.
    Строка вида '-команда' — ожидаемая ошибка: скрипт после неё продолжается (для демонстраций).
    Возвращает False, если скрипт не удалось прочитать."""
    try:
        with open(path, encoding="utf-8-sig") as f:
            lines = f.read().splitlines()
    except OSError as e:
        err(f"Ошибка: не удалось прочитать скрипт '{path}': {e.strerror}")
        return False
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        expected_error = line.startswith("-")
        if expected_error:
            line = line[1:]
        out(shell.prompt() + line)
        status = shell.execute(line)
        if status != 0 and expected_error:
            out(f"[ожидаемая ошибка, код {status}; скрипт продолжается]")
        elif status != 0:
            err(f"Скрипт остановлен: ошибка в строке {number} (код {status})")
            break
    return True


def repl(shell):
    """Интерактивный цикл: приглашение -> ввод -> выполнение."""
    from_terminal = sys.stdin.isatty()
    while True:
        try:
            line = input(shell.prompt())
        except EOFError:  # Ctrl+D
            out("exit")
            return 0
        except KeyboardInterrupt:  # Ctrl+C — отмена строки
            out()
            continue
        if not from_terminal:  # ввод из файла/канала: покажем введённую строку
            out(line)
        shell.execute(line)

def cmd_ls(shell, args):
    """ls [-l] [-a] [путь ...]"""
    letters = "".join(a[1:] for a in args if a.startswith("-"))
    bad = [c for c in letters if c not in "la"]
    if bad:
        err(f"ls: invalid option -- '{bad[0]}'")
        return 2
    paths = [a for a in args if not a.startswith("-")] or ["."]
    status = 0
    for i, path in enumerate(paths):
        try:
            node = shell.vfs.get(shell.vfs.path(shell.cwd, path))
        except VFSError as e:
            err(f"ls: cannot access '{path}': {e}")
            status = 2
            continue
        if len(paths) > 1:  # несколько путей — печатаем заголовки
            out(("\n" if i else "") + f"{path}:")
        if isinstance(node, dict):
            items = {name: node[name] for name in sorted(node, key=str.lower)
                     if "a" in letters or not name.startswith(".")}
            if "a" in letters:
                items = {".": node, "..": node, **items}
        else:
            items = {path: node}  # ls для файла показывает сам файл
        if "l" in letters:
            for name, child in items.items():
                kind, size = ("d", 4096) if isinstance(child, dict) else ("-", len(child))
                out(f"{kind} {size:>5} {name}")
        else:
            out("  ".join(items))
    return status


def cmd_cd(shell, args):
    """cd [путь]  (без аргумента — корень VFS)"""
    if len(args) > 1:
        err("cd: too many arguments")
        return 1
    target = args[0] if args else "/"
    full = shell.vfs.path(shell.cwd, target)
    try:
        node = shell.vfs.get(full)
    except VFSError as e:
        err(f"cd: {target}: {e}")
        return 1
    if not isinstance(node, dict):
        err(f"cd: {target}: Not a directory")
        return 1
    shell.cwd = full
    return 0


def cmd_cal(shell, args):
    """cal | cal ГОД | cal МЕСЯЦ ГОД"""
    if len(args) > 2 or not all(a.isdigit() for a in args):
        err("cal: usage: cal [[месяц] год]  (числа)")
        return 1
    calendar.setfirstweekday(6)  # неделя начинается с воскресенья, как в UNIX
    today = datetime.date.today()
    month, year = today.month, today.year
    if len(args) == 1:
        year, month = int(args[0]), None
    elif len(args) == 2:
        month, year = int(args[0]), int(args[1])
    if not 1 <= year <= 9999:
        err(f"cal: year '{year}' not in range 1..9999")
        return 1
    if month is not None and not 1 <= month <= 12:
        err(f"cal: {month} is not a month number (1..12)")
        return 1
    text = calendar.month(year, month) if month else calendar.calendar(year)
    for line in text.rstrip().split("\n"):
        out(line.rstrip())
    return 0


def cmd_tail(shell, args):
    """tail [-n N] файл ...  (по умолчанию — последние 10 строк)"""
    count = 10
    if args[:1] == ["-n"]:
        if len(args) < 2:
            err("tail: option requires an argument -- 'n'")
            return 1
        if not args[1].isdigit():
            err(f"tail: invalid number of lines: '{args[1]}'")
            return 1
        count, args = int(args[1]), args[2:]
    if not args:
        err("tail: missing file operand")
        return 1
    status = 0
    for i, name in enumerate(args):
        try:
            node = shell.vfs.get(shell.vfs.path(shell.cwd, name))
        except VFSError as e:
            err(f"tail: cannot open '{name}' for reading: {e}")
            status = 1
            continue
        if isinstance(node, dict):
            err(f"tail: error reading '{name}': Is a directory")
            status = 1
            continue
        if len(args) > 1:  # несколько файлов — печатаем заголовки
            out(("\n" if i else "") + f"==> {name} <==")
        lines = shell.vfs.text(node).splitlines()
        for line in lines[-count:] if count else []:
            out(line)
    return status


def cmd_mv(shell, args):
    """mv источник назначение  (если назначение — каталог, источник переносится внутрь)"""
    if len(args) < 2:
        err("mv: missing file operand" if not args else f"mv: missing destination file operand after '{args[0]}'")
        return 1
    if len(args) > 2:
        err("mv: too many arguments")
        return 1
    src, dst = args
    vfs = shell.vfs
    src_full = vfs.path(shell.cwd, src)
    dst_full = vfs.path(shell.cwd, dst)
    try:
        node = vfs.get(src_full)
    except VFSError as e:
        err(f"mv: cannot stat '{src}': {e}")
        return 1
    if src_full == "/":
        err("mv: cannot move the root directory")
        return 1
    try:  # назначение — существующий каталог: переносим внутрь него
        if isinstance(vfs.get(dst_full), dict):
            dst_full = posixpath.join(dst_full, posixpath.basename(src_full))
    except VFSError:
        pass
    if dst_full == src_full:
        err(f"mv: '{src}' and '{dst}' are the same file")
        return 1
    if dst_full.startswith(src_full + "/"):
        err(f"mv: cannot move '{src}' to a subdirectory of itself")
        return 1
    if shell.cwd == src_full or shell.cwd.startswith(src_full + "/"):
        err(f"mv: cannot move '{src}': it contains the current directory")
        return 1
    try:
        existing = vfs.get(dst_full)
    except VFSError:
        existing = None
    if existing is not None and (isinstance(existing, dict) or isinstance(node, dict)):
        err(f"mv: cannot overwrite '{dst}': already exists")  # заменять можно только файл файлом
        return 1
    try:
        vfs.move(src_full, dst_full)
    except VFSError as e:
        err(f"mv: cannot move '{src}' to '{dst}': {e}")
        return 1
    return 0


def cmd_exit(shell, args):
    """exit [код]"""
    if len(args) > 1:
        err("exit: too many arguments")
        return 1
    if args and not args[0].lstrip("-").isdigit():
        err(f"exit: {args[0]}: numeric argument required")
        return 2
    raise Exit(int(args[0]) & 0xFF if args else 0)


def cmd_vfs_info(shell, args):
    """Служебная команда: сведения о VFS."""
    if args:
        err("vfs-info: too many arguments")
        return 1
    dirs, files, size = shell.vfs.stats()
    out(f"name:   {shell.vfs.name}")
    out(f"source: {shell.vfs.source or '(в памяти, по умолчанию)'}")
    out(f"dirs: {dirs}, files: {files}, bytes: {size}")
    return 0


COMMANDS = {"ls": cmd_ls, "cd": cmd_cd, "cal": cmd_cal, "tail": cmd_tail,
            "mv": cmd_mv, "exit": cmd_exit, "vfs-info": cmd_vfs_info}


# ======================= оболочка =======================
class Shell:
    def __init__(self, vfs):
        self.vfs = vfs
        self.cwd = "/"

    def prompt(self):
        return f"{self.vfs.name}:{self.cwd}$ "

    def execute(self, line):
        """Разбирает и выполняет строку. Возвращает код возврата (0 — успех)."""
        try:
            # shlex понимает кавычки и комментарии (#), expandvars подставляет $HOME, ${USER} и т. п.
            words = [os.path.expandvars(w) for w in shlex.split(line, comments=True)]
        except ValueError as e:
            err(f"parse error: {e}")
            return 2
        if not words:
            return 0
        command = COMMANDS.get(words[0])
        if command is None:
            err(f"{words[0]}: command not found")
            return 127
        return command(self, words[1:])


def run_script(shell, path):
    """Выполняет стартовый скрипт, показывая ввод и вывод. Останавливается на первой ошибке.
    Строка вида '-команда' — ожидаемая ошибка: скрипт после неё продолжается (для демонстраций).
    Возвращает False, если скрипт не удалось прочитать."""
    try:
        with open(path, encoding="utf-8-sig") as f:
            lines = f.read().splitlines()
    except OSError as e:
        err(f"Ошибка: не удалось прочитать скрипт '{path}': {e.strerror}")
        return False
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        expected_error = line.startswith("-")
        if expected_error:
            line = line[1:]
        out(shell.prompt() + line)
        status = shell.execute(line)
        if status != 0 and expected_error:
            out(f"[ожидаемая ошибка, код {status}; скрипт продолжается]")
        elif status != 0:
            err(f"Скрипт остановлен: ошибка в строке {number} (код {status})")
            break
    return True


def repl(shell):
    """Интерактивный цикл: приглашение -> ввод -> выполнение."""
    from_terminal = sys.stdin.isatty()
    while True:
        try:
            line = input(shell.prompt())
        except EOFError:  # Ctrl+D
            out("exit")
            return 0
        except KeyboardInterrupt:  # Ctrl+C — отмена строки
            out()
            continue
        if not from_terminal:  # ввод из файла/канала: покажем введённую строку
            out(line)
        shell.execute(line)



def main():
    parser = argparse.ArgumentParser(description="Эмулятор оболочки UNIX-подобной ОС")
    parser.add_argument("--vfs", metavar="PATH", help="ZIP-архив с VFS")
    parser.add_argument("--script", metavar="PATH", help="стартовый скрипт")
    args = parser.parse_args()
    for stream in (sys.stdout, sys.stderr):
        if not stream.isatty():
            stream.reconfigure(encoding="utf-8")

    # отладочный вывод всех параметров
    out("[debug] Параметры запуска:")
    out(f"[debug]   --vfs    = {args.vfs or '(не задан)'}")
    out(f"[debug]   --script = {args.script or '(не задан)'}")

    if args.vfs is None:
        vfs = default_vfs()
        out("[debug] VFS не указана: создана VFS по умолчанию в памяти")
    else:
        try:
            vfs = load_zip(args.vfs)
        except VFSError as e:
            err(f"Ошибка загрузки VFS: {e}")
            return 1
    dirs, files, size = vfs.stats()
    out(f"[debug]   имя VFS = {vfs.name}; каталогов: {dirs}, файлов: {files}, байт: {size}")

    shell = Shell(vfs)
    try:
        if args.script is not None and not run_script(shell, args.script):
            return 1
        return repl(shell)
    except Exit as e:
        return e.code


if __name__ == "__main__":
    sys.exit(main())

