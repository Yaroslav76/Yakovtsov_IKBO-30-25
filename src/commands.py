"""Команды эмулятора: ls, cd, cal, tail, mv, exit и служебная vfs-info."""
import calendar
import datetime
import posixpath
import sys

from vfs import VFSError

MAX_CD_ARGS = 1
MAX_EXIT_ARGS = 1
MAX_CAL_ARGS = 2
YEAR_ONLY = 1
MONTH_AND_YEAR = 2
MV_OPERANDS = 2
MIN_YEAR = 1
MAX_YEAR = 9999
FIRST_MONTH = 1
LAST_MONTH = 12
TAIL_DEFAULT_LINES = 10
EXIT_MASK = 0xFF
DIR_SIZE = 4096


class Exit(Exception):
    """Сигнал завершения работы эмулятора."""

    def __init__(self, code):
        """code - код возврата процесса."""
        super().__init__(code)
        self.code = code


def out(text=""):
    """Печатает строку в стандартный вывод."""
    print(text, flush=True)


def err(text):
    """Печатает сообщение об ошибке в стандартный поток ошибок."""
    print(text, file=sys.stderr, flush=True)


def _ls_items(node, path, show_all):
    """Возвращает записи для вывода ls: {имя: узел}."""
    if not isinstance(node, dict):
        return {path: node}
    names = sorted(node, key=str.lower)
    items = {n: node[n] for n in names
             if show_all or not n.startswith(".")}
    if show_all:
        items = {".": node, "..": node, **items}
    return items


def _ls_print(items, long_format):
    """Печатает записи: в строку или в длинном формате (-l)."""
    if not long_format:
        out("  ".join(items))
        return
    for name, child in items.items():
        if isinstance(child, dict):
            kind, size = "d", DIR_SIZE
        else:
            kind, size = "-", len(child)
        out(f"{kind} {size:>5} {name}")


def _ls_one(shell, path, letters, prefix):
    """Выводит один путь команды ls; возвращает код возврата."""
    try:
        node = shell.vfs.get(shell.vfs.path(shell.cwd, path))
    except VFSError as e:
        err(f"ls: cannot access '{path}': {e}")
        return 2
    if prefix is not None:
        out(prefix + f"{path}:")
    _ls_print(_ls_items(node, path, "a" in letters), "l" in letters)
    return 0


def _ls_parse(args):
    """Разбирает опции и пути ls; возвращает (буквы опций, пути)."""
    letters = "".join(a[1:] for a in args if a.startswith("-"))
    bad = [c for c in letters if c not in "la"]
    if bad:
        raise ValueError(f"ls: invalid option -- '{bad[0]}'")
    paths = [a for a in args if not a.startswith("-")]
    return letters, paths or ["."]


def cmd_ls(shell, args):
    """ls [-l] [-a] [путь ...]: содержимое каталога или сам файл."""
    try:
        letters, paths = _ls_parse(args)
    except ValueError as e:
        err(str(e))
        return 2
    many = bool(paths[1:])
    status = 0
    for i, path in enumerate(paths):
        prefix = ("\n" if i else "") if many else None
        status = _ls_one(shell, path, letters, prefix) or status
    return status


def cmd_cd(shell, args):
    """cd [путь]: смена текущего каталога (без аргумента - корень)."""
    if len(args) > MAX_CD_ARGS:
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


def _cal_check(year, month):
    """Проверяет год и месяц; при ошибке бросает ValueError."""
    if year not in range(MIN_YEAR, MAX_YEAR + 1):
        raise ValueError(f"cal: year '{year}' not in range 1..9999")
    if month is None:
        return
    if month not in range(FIRST_MONTH, LAST_MONTH + 1):
        raise ValueError(f"cal: {month} is not a month number (1..12)")


def _cal_parse(args):
    """Разбирает аргументы cal; возвращает (год, месяц или None)."""
    numbers = [a for a in args if a.isdigit()]
    if len(args) > MAX_CAL_ARGS or numbers != args:
        raise ValueError("cal: usage: cal [[месяц] год]  (числа)")
    today = datetime.date.today()
    if len(args) == YEAR_ONLY:
        year, month = int(args[0]), None
    elif len(args) == MONTH_AND_YEAR:
        month, year = int(args[0]), int(args[1])
    else:
        year, month = today.year, today.month
    _cal_check(year, month)
    return year, month


def cmd_cal(shell, args):
    """cal | cal ГОД | cal МЕСЯЦ ГОД: календарь, неделя с воскресенья."""
    try:
        year, month = _cal_parse(args)
    except ValueError as e:
        err(str(e))
        return 1
    calendar.setfirstweekday(calendar.SUNDAY)
    text = calendar.month(year, month) if month else calendar.calendar(year)
    for line in text.rstrip().split("\n"):
        out(line.rstrip())
    return 0


def _tail_parse(args):
    """Разбирает [-n N] файл...; возвращает (число строк, имена файлов)."""
    count = TAIL_DEFAULT_LINES
    if args[:1] == ["-n"]:
        value = args[1:2]
        if not value:
            raise ValueError("tail: option requires an argument -- 'n'")
        if not value[0].isdigit():
            raise ValueError(f"tail: invalid number of lines: '{value[0]}'")
        count, args = int(value[0]), args[2:]
    if not args:
        raise ValueError("tail: missing file operand")
    return count, args


def _tail_file(shell, name, count, prefix):
    """Печатает последние строки одного файла; возвращает код возврата."""
    try:
        node = shell.vfs.get(shell.vfs.path(shell.cwd, name))
    except VFSError as e:
        err(f"tail: cannot open '{name}' for reading: {e}")
        return 1
    if isinstance(node, dict):
        err(f"tail: error reading '{name}': Is a directory")
        return 1
    if prefix is not None:
        out(prefix + f"==> {name} <==")
    lines = shell.vfs.text(node).splitlines()
    for line in (lines[-count:] if count else []):
        out(line)
    return 0


def cmd_tail(shell, args):
    """tail [-n N] файл ...: последние строки (по умолчанию 10)."""
    try:
        count, names = _tail_parse(args)
    except ValueError as e:
        err(str(e))
        return 1
    many = bool(names[1:])
    status = 0
    for i, name in enumerate(names):
        prefix = ("\n" if i else "") if many else None
        status = _tail_file(shell, name, count, prefix) or status
    return status


def _mv_operands(args):
    """Проверяет число операндов mv; возвращает (источник, назначение)."""
    if not args:
        raise ValueError("mv: missing file operand")
    if len(args) < MV_OPERANDS:
        raise ValueError(
            f"mv: missing destination file operand after '{args[0]}'")
    if len(args) > MV_OPERANDS:
        raise ValueError("mv: too many arguments")
    return args[0], args[1]


def _mv_target(vfs, dst_full, src_full):
    """Если назначение - каталог, возвращает путь внутри него."""
    try:
        is_dir = isinstance(vfs.get(dst_full), dict)
    except VFSError:
        return dst_full
    if is_dir:
        return posixpath.join(dst_full, posixpath.basename(src_full))
    return dst_full


def _mv_check(shell, names, full, node):
    """Проверки перед переносом; возвращает текст ошибки или None.

    names - (src, dst) как введено, full - (src_full, target) абсолютные.
    """
    (src, dst), (src_full, target) = names, full
    if src_full == "/":
        return "mv: cannot move the root directory"
    if target == src_full:
        return f"mv: '{src}' and '{dst}' are the same file"
    if target.startswith(src_full + "/"):
        return f"mv: cannot move '{src}' to a subdirectory of itself"
    if shell.cwd == src_full or shell.cwd.startswith(src_full + "/"):
        return f"mv: cannot move '{src}': it contains the current directory"
    try:
        existing = shell.vfs.get(target)
    except VFSError:
        return None
    if isinstance(existing, dict) or isinstance(node, dict):
        return f"mv: cannot overwrite '{dst}': already exists"
    return None


def cmd_mv(shell, args):
    """mv источник назначение: переименование или перенос в VFS."""
    try:
        src, dst = _mv_operands(args)
    except ValueError as e:
        err(str(e))
        return 1
    vfs = shell.vfs
    src_full = vfs.path(shell.cwd, src)
    try:
        node = vfs.get(src_full)
    except VFSError as e:
        err(f"mv: cannot stat '{src}': {e}")
        return 1
    target = _mv_target(vfs, vfs.path(shell.cwd, dst), src_full)
    message = _mv_check(shell, (src, dst), (src_full, target), node)
    if message:
        err(message)
        return 1
    try:
        vfs.move(src_full, target)
    except VFSError as e:
        err(f"mv: cannot move '{src}' to '{dst}': {e}")
        return 1
    return 0


def cmd_exit(shell, args):
    """exit [код]: завершает эмулятор."""
    if len(args) > MAX_EXIT_ARGS:
        err("exit: too many arguments")
        return 1
    if args and not args[0].lstrip("-").isdigit():
        err(f"exit: {args[0]}: numeric argument required")
        return 2
    raise Exit(int(args[0]) & EXIT_MASK if args else 0)


def cmd_vfs_info(shell, args):
    """vfs-info: служебная команда, сведения о подключённой VFS."""
    if args:
        err("vfs-info: too many arguments")
        return 1
    dirs, files, size = shell.vfs.stats()
    out(f"name:   {shell.vfs.name}")
    out(f"source: {shell.vfs.source or '(в памяти, по умолчанию)'}")
    out(f"dirs: {dirs}, files: {files}, bytes: {size}")
    return 0


COMMANDS = {
    "ls": cmd_ls,
    "cd": cmd_cd,
    "cal": cmd_cal,
    "tail": cmd_tail,
    "mv": cmd_mv,
    "exit": cmd_exit,
    "vfs-info": cmd_vfs_info,
}
