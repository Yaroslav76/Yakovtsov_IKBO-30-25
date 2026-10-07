"""Эмулятор оболочки UNIX-подобной ОС (вариант 30).

Запуск: python3 src/emulator.py [--vfs архив.zip] [--script скрипт.emu]
"""
import argparse
import os
import shlex
import sys

from commands import COMMANDS, Exit, err, out
from vfs import VFSError, default_vfs, load_zip

STATUS_SYNTAX = 2
STATUS_NOT_FOUND = 127
EXPECTED_MARK = "-"


class Shell:
    """Состояние оболочки: подключённая VFS и текущий каталог."""

    def __init__(self, vfs):
        """Создаёт оболочку над VFS; начальный каталог - корень."""
        self.vfs = vfs
        self.cwd = "/"

    def prompt(self):
        """Приглашение к вводу: имя VFS и текущий каталог."""
        return f"{self.vfs.name}:{self.cwd}$ "

    def execute(self, line):
        """Разбирает и выполняет строку; возвращает код возврата.

        shlex понимает кавычки и комментарии (знак решётки),
        expandvars подставляет переменные окружения ($HOME, ${USER}).
        """
        try:
            words = [os.path.expandvars(w)
                     for w in shlex.split(line, comments=True)]
        except ValueError as e:
            err(f"parse error: {e}")
            return STATUS_SYNTAX
        if not words:
            return 0
        command = COMMANDS.get(words[0])
        if command is None:
            err(f"{words[0]}: command not found")
            return STATUS_NOT_FOUND
        return command(self, words[1:])


def run_line(shell, number, line):
    """Выполняет строку скрипта; False - скрипт нужно остановить.

    Строка вида '-команда' - ожидаемая ошибка: скрипт продолжается.
    """
    expected = line.startswith(EXPECTED_MARK)
    if expected:
        line = line[len(EXPECTED_MARK):]
    out(shell.prompt() + line)
    status = shell.execute(line)
    if status and expected:
        out(f"[ожидаемая ошибка, код {status}; скрипт продолжается]")
    elif status:
        err(f"Скрипт остановлен: ошибка в строке {number} (код {status})")
        return False
    return True


def run_script(shell, path):
    """Выполняет стартовый скрипт с показом ввода и вывода.

    Останавливается на первой ошибке. False - скрипт не удалось прочитать.
    """
    try:
        with open(path, encoding="utf-8-sig") as f:
            lines = f.read().splitlines()
    except OSError as e:
        err(f"Ошибка: не удалось прочитать скрипт '{path}': {e.strerror}")
        return False
    for number, line in enumerate(lines, 1):
        if line.strip() and not run_line(shell, number, line):
            break
    return True


def repl(shell):
    """Интерактивный цикл: приглашение, ввод, выполнение."""
    from_terminal = sys.stdin.isatty()
    while True:
        try:
            line = input(shell.prompt())
        except EOFError:
            out("exit")
            return 0
        except KeyboardInterrupt:
            out()
            continue
        if not from_terminal:
            out(line)
        shell.execute(line)


def parse_args():
    """Разбирает параметры командной строки."""
    parser = argparse.ArgumentParser(
        description="Эмулятор оболочки UNIX-подобной ОС")
    parser.add_argument("--vfs", metavar="PATH", help="ZIP-архив с VFS")
    parser.add_argument("--script", metavar="PATH", help="стартовый скрипт")
    return parser.parse_args()


def print_params(args):
    """Отладочный вывод всех заданных параметров."""
    out("[debug] Параметры запуска:")
    out(f"[debug]   --vfs    = {args.vfs or '(не задан)'}")
    out(f"[debug]   --script = {args.script or '(не задан)'}")


def load_vfs(path):
    """Возвращает VFS из ZIP или по умолчанию; None при ошибке загрузки."""
    if path is None:
        out("[debug] VFS не указана: создана VFS по умолчанию в памяти")
        return default_vfs()
    try:
        return load_zip(path)
    except VFSError as e:
        err(f"Ошибка загрузки VFS: {e}")
        return None


def main():
    """Точка входа: параметры, загрузка VFS, скрипт, интерактивный режим."""
    args = parse_args()
    for stream in (sys.stdout, sys.stderr):
        if not stream.isatty():
            stream.reconfigure(encoding="utf-8")
    print_params(args)
    vfs = load_vfs(args.vfs)
    if vfs is None:
        return 1
    dirs, files, size = vfs.stats()
    out(f"[debug]   имя VFS = {vfs.name}; каталогов: {dirs}, "
        f"файлов: {files}, байт: {size}")
    shell = Shell(vfs)
    try:
        if args.script is not None and not run_script(shell, args.script):
            return 1
        return repl(shell)
    except Exit as e:
        return e.code


if __name__ == "__main__":
    sys.exit(main())
