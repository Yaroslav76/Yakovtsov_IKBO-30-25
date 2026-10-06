# Эмулятор оболочки UNIX-подобной ОС (вариант 30)

Консольное приложение на Python 3.8+ (только стандартная библиотека). Имитирует командную строку UNIX; файловая
система — виртуальная (VFS), целиком в памяти, источник — ZIP-архив.

```text
python3 emulator.py [--vfs PATH] [--script PATH]      # на Windows: python emulator.py ...
```

| Параметр | Смысл |
|---|---|
| `--vfs PATH` | ZIP-архив с VFS; если не указан — VFS по умолчанию создаётся в памяти |
| `--script PATH` | стартовый скрипт: команды выполняются с показом ввода и вывода, остановка на первой ошибке |

## Структура

```text
emulator.py   оболочка: разбор строки, REPL, параметры, скрипты и все команды (ls, cd, cal, tail, mv, exit)
vfs.py        VFS в памяти: каталог — dict, файл — bytes; загрузка из ZIP
scripts/      стартовые скрипты эмулятора (*.emu)
tests/        скрипты реальной ОС (test_stage2.sh, test_stage3.sh), tests/vfs/*.zip — тестовые VFS,
              make_vfs.py — их генератор
```

Строка скрипта, начинающаяся с `-`, — «ожидаемая ошибка»: она выполняется, ошибка показывается, но скрипт идёт дальше
(иначе в одном скрипте нельзя показать несколько ошибок). Обычная ошибка останавливает скрипт.

---

## Этап 1. REPL

- Приглашение содержит имя VFS и текущий каталог: `default:/$ `.
- Разбор строки: `shlex.split` (пробелы, кавычки, комментарии `#`) и `os.path.expandvars` — подстановка
  переменных окружения реальной ОС (`$HOME`, `${USER}`). Неизвестная переменная остаётся как есть.
  Подстановка выполняется во всём аргументе, в том числе в кавычках (упрощение: в bash внутри `'...'` её нет).
- Команда `exit [код]`, Ctrl+D — выход, Ctrl+C — отмена строки.
- Ошибки: неизвестная команда (код 127), незакрытая кавычка, `exit` с нечисловым или лишним аргументом.
- Ввод из файла/канала дублируется в вывод (удобно для демонстрации).

Демонстрация (`HOME=/home/rid USER=rid python3 emulator.py < tests/stage1.in`):

```text
[debug] Параметры запуска:
[debug]   --vfs    = (не задан)
[debug]   --script = (не задан)
[debug] VFS не указана: создана VFS по умолчанию в памяти
[debug]   имя VFS = default; каталогов: 4, файлов: 3, байт: 304
default:/$ ls
etc  home  tmp
default:/$ ls -l /home
d  4096 user
default:/$ cd home/user
default:/home/user$ ls $HOME ${USER} "$HOME/x" '$NO_EXPANSION'
ls: cannot access '/home/rid': No such file or directory
ls: cannot access 'rid': No such file or directory
ls: cannot access '/home/rid/x': No such file or directory
ls: cannot access '$NO_EXPANSION': No such file or directory
default:/home/user$ cd
default:/$ # комментарий
default:/$ foo bar
foo: command not found
default:/$ ls "незакрытая
parse error: No closing quotation
default:/$ exit abc
exit: abc: numeric argument required
default:/$ exit 1 2
exit: too many arguments
default:/$ exit 3
[код возврата: 3]
```

## Этап 2. Конфигурация

- Параметры `--vfs PATH` и `--script PATH` (`argparse`), при запуске печатается отладочный вывод всех параметров.
- Стартовый скрипт: каждая строка показывается с приглашением, затем её вывод; остановка на первой ошибке
  (с номером строки). После скрипта эмулятор переходит в интерактивный режим; `exit` в скрипте завершает его.
  Нечитаемый скрипт — код возврата 1.
- Скрипт реальной ОС: `tests/test_stage2.sh` — все сочетания параметров, включая ошибочные.

Демонстрация (`bash tests/test_stage2.sh`):

```text

$ python3 emulator.py 
[debug] Параметры запуска:
[debug]   --vfs    = (не задан)
[debug]   --script = (не задан)
[debug] VFS не указана: создана VFS по умолчанию в памяти
[debug]   имя VFS = default; каталогов: 4, файлов: 3, байт: 304
default:/$ exit
[код возврата: 0]

$ python3 emulator.py --vfs tests/vfs/minimal.zip
[debug] Параметры запуска:
[debug]   --vfs    = tests/vfs/minimal.zip
[debug]   --script = (не задан)
[debug]   имя VFS = minimal; каталогов: 0, файлов: 1, байт: 12
minimal:/$ exit
[код возврата: 0]

$ python3 emulator.py --script scripts/stage2_ok.emu
[debug] Параметры запуска:
[debug]   --vfs    = (не задан)
[debug]   --script = scripts/stage2_ok.emu
[debug] VFS не указана: создана VFS по умолчанию в памяти
[debug]   имя VFS = default; каталогов: 4, файлов: 3, байт: 304
default:/$ # Скрипт без ошибок (работает с любой VFS)
default:/$ ls
etc  home  tmp
default:/$ ls -a
.  ..  etc  home  tmp
default:/$ cal 2 2024
   February 2024
Su Mo Tu We Th Fr Sa
             1  2  3
 4  5  6  7  8  9 10
11 12 13 14 15 16 17
18 19 20 21 22 23 24
25 26 27 28 29
default:/$ exit
[код возврата: 0]

$ python3 emulator.py --vfs tests/vfs/minimal.zip --script scripts/stage2_ok.emu
[debug] Параметры запуска:
[debug]   --vfs    = tests/vfs/minimal.zip
[debug]   --script = scripts/stage2_ok.emu
[debug]   имя VFS = minimal; каталогов: 0, файлов: 1, байт: 12
minimal:/$ # Скрипт без ошибок (работает с любой VFS)
minimal:/$ ls
hello.txt
minimal:/$ ls -a
.  ..  hello.txt
minimal:/$ cal 2 2024
   February 2024
Su Mo Tu We Th Fr Sa
             1  2  3
 4  5  6  7  8  9 10
11 12 13 14 15 16 17
18 19 20 21 22 23 24
25 26 27 28 29
minimal:/$ exit
[код возврата: 0]

$ python3 emulator.py --script scripts/stage2_error.emu
[debug] Параметры запуска:
[debug]   --vfs    = (не задан)
[debug]   --script = scripts/stage2_error.emu
[debug] VFS не указана: создана VFS по умолчанию в памяти
[debug]   имя VFS = default; каталогов: 4, файлов: 3, байт: 304
default:/$ # Скрипт останавливается на первой ошибке (вторая строка)
default:/$ ls
etc  home  tmp
default:/$ nosuchcmd arg
nosuchcmd: command not found
Скрипт остановлен: ошибка в строке 3 (код 127)
default:/$ exit
[код возврата: 0]

$ python3 emulator.py --script scripts/no_such_script.emu
[debug] Параметры запуска:
[debug]   --vfs    = (не задан)
[debug]   --script = scripts/no_such_script.emu
[debug] VFS не указана: создана VFS по умолчанию в памяти
[debug]   имя VFS = default; каталогов: 4, файлов: 3, байт: 304
Ошибка: не удалось прочитать скрипт 'scripts/no_such_script.emu': No such file or directory
[код возврата: 1]

$ python3 emulator.py --unknown
usage: emulator.py [-h] [--vfs PATH] [--script PATH]
emulator.py: error: unrecognized arguments: --unknown
[код возврата: 2]
```

## Этап 3. VFS

- Источник — ZIP-архив (`--vfs`). Он читается в память (`zipfile` + `io.BytesIO`); на диск ничего не
  распаковывается и не пишется, исходный ZIP не меняется.
- Каталог — `dict`, файл — `bytes`. Двоичные данные (не UTF-8) при выводе кодируются в base64.
- Имя VFS = имя архива без расширения (`deep.zip` → `deep`).
- Ошибки загрузки: файл не найден, это каталог, неверный формат/повреждённый архив, небезопасный путь (`..`).
- Нет `--vfs` — создаётся VFS по умолчанию. Служебная команда `vfs-info` показывает сведения о VFS.
- Тестовые архивы (`tests/vfs/`, создаются `tests/make_vfs.py`): `minimal.zip` (1 файл), `files.zip` (несколько
  файлов), `deep.zip` (вложенность до 5 уровней), `not_a_zip.zip` и `corrupt.zip` (для ошибок).
- Скрипт реальной ОС `tests/test_stage3.sh` и стартовый скрипт всех команд `scripts/stage3_all.emu`.

Демонстрация (`bash tests/test_stage3.sh`):

```text

$ python3 emulator.py --script scripts/stage3_info.emu
[debug] Параметры запуска:
[debug]   --vfs    = (не задан)
[debug]   --script = scripts/stage3_info.emu
[debug] VFS не указана: создана VFS по умолчанию в памяти
[debug]   имя VFS = default; каталогов: 4, файлов: 3, байт: 304
default:/$ vfs-info
name:   default
source: (в памяти, по умолчанию)
dirs: 4, files: 3, bytes: 304
default:/$ ls
etc  home  tmp
default:/$ exit
[код возврата: 0]

$ python3 emulator.py --vfs tests/vfs/minimal.zip --script scripts/stage3_info.emu
[debug] Параметры запуска:
[debug]   --vfs    = tests/vfs/minimal.zip
[debug]   --script = scripts/stage3_info.emu
[debug]   имя VFS = minimal; каталогов: 0, файлов: 1, байт: 12
minimal:/$ vfs-info
name:   minimal
source: tests/vfs/minimal.zip
dirs: 0, files: 1, bytes: 12
minimal:/$ ls
hello.txt
minimal:/$ exit
[код возврата: 0]

$ python3 emulator.py --vfs tests/vfs/files.zip --script scripts/stage3_info.emu
[debug] Параметры запуска:
[debug]   --vfs    = tests/vfs/files.zip
[debug]   --script = scripts/stage3_info.emu
[debug]   имя VFS = files; каталогов: 1, файлов: 6, байт: 1122
files:/$ vfs-info
name:   files
source: tests/vfs/files.zip
dirs: 1, files: 6, bytes: 1122
files:/$ ls
empty  log.txt  logo.bin  no_newline.txt  readme.txt  short.txt
files:/$ exit
[код возврата: 0]

$ python3 emulator.py --vfs tests/vfs/deep.zip --script scripts/stage3_info.emu
[debug] Параметры запуска:
[debug]   --vfs    = tests/vfs/deep.zip
[debug]   --script = scripts/stage3_info.emu
[debug]   имя VFS = deep; каталогов: 12, файлов: 9, байт: 183
deep:/$ vfs-info
name:   deep
source: tests/vfs/deep.zip
dirs: 12, files: 9, bytes: 183
deep:/$ ls
a  etc  projects  README.md  tmp
deep:/$ exit
[код возврата: 0]

$ python3 emulator.py --vfs tests/vfs/no_such.zip
[debug] Параметры запуска:
[debug]   --vfs    = tests/vfs/no_such.zip
[debug]   --script = (не задан)
Ошибка загрузки VFS: файл не найден: tests/vfs/no_such.zip
[код возврата: 1]

$ python3 emulator.py --vfs tests/vfs/not_a_zip.zip
[debug] Параметры запуска:
[debug]   --vfs    = tests/vfs/not_a_zip.zip
[debug]   --script = (не задан)
Ошибка загрузки VFS: неверный формат (не ZIP-архив): tests/vfs/not_a_zip.zip
[код возврата: 1]

$ python3 emulator.py --vfs tests/vfs/corrupt.zip
[debug] Параметры запуска:
[debug]   --vfs    = tests/vfs/corrupt.zip
[debug]   --script = (не задан)
Ошибка загрузки VFS: неверный формат (не ZIP-архив): tests/vfs/corrupt.zip
[код возврата: 1]

$ python3 emulator.py --vfs tests
[debug] Параметры запуска:
[debug]   --vfs    = tests
[debug]   --script = (не задан)
Ошибка загрузки VFS: это каталог, а не ZIP-архив: tests
[код возврата: 1]

$ python3 emulator.py --vfs tests/vfs/deep.zip --script scripts/stage3_all.emu
[debug] Параметры запуска:
[debug]   --vfs    = tests/vfs/deep.zip
[debug]   --script = scripts/stage3_all.emu
[debug]   имя VFS = deep; каталогов: 12, файлов: 9, байт: 183
deep:/$ # Все команды этапов 1-3 (запуск с deep.zip). Строки с '-' — ожидаемые ошибки.
deep:/$ vfs-info
name:   deep
source: tests/vfs/deep.zip
dirs: 12, files: 9, bytes: 183
deep:/$ ls
a  etc  projects  README.md  tmp
deep:/$ ls -l a
d  4096 b
deep:/$ cd projects/app
deep:/projects/app$ ls
README.md  src
deep:/projects/app$ cd /
deep:/$ ls $HOME
ls: cannot access '/home/rid': No such file or directory
[ожидаемая ошибка, код 2; скрипт продолжается]
deep:/$ ls "$HOME и ${USER}"
ls: cannot access '/home/rid и rid': No such file or directory
[ожидаемая ошибка, код 2; скрипт продолжается]
deep:/$ vfs-info extra
vfs-info: too many arguments
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ unknown_cmd 1 2
unknown_cmd: command not found
[ожидаемая ошибка, код 127; скрипт продолжается]
deep:/$ ls "незакрытая кавычка
parse error: No closing quotation
[ожидаемая ошибка, код 2; скрипт продолжается]
deep:/$ exit abc
exit: abc: numeric argument required
[ожидаемая ошибка, код 2; скрипт продолжается]
deep:/$ exit 1 2
exit: too many arguments
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ # обычная ошибка останавливает скрипт
deep:/$ nosuchcmd
nosuchcmd: command not found
Скрипт остановлен: ошибка в строке 16 (код 127)
deep:/$ exit
[код возврата: 0]
```

## Этап 4. Основные команды

| Команда | Режимы |
|---|---|
| `ls [-l] [-a] [путь ...]` | текущий каталог, каталог, файл, несколько путей (с заголовками); `-a` — скрытые файлы и `.`/`..`; `-l` — тип, размер, имя |
| `cd [путь]` | без аргумента — корень VFS; абсолютные и относительные пути, `.`, `..` |
| `cal [[месяц] год]` | без аргументов — текущий месяц; `год` — весь год; `месяц год` |
| `tail [-n N] файл ...` | последние 10 строк или N; несколько файлов — с заголовками `==> имя <==`; двоичный файл — base64 |

Сообщения об ошибках — как в coreutils. Обрабатываются: несуществующий путь, `cd` в файл, `tail` каталога,
неверное число/опция, лишние аргументы, неверный месяц/год.

Запуск: `python3 emulator.py --vfs tests/vfs/deep.zip --script scripts/stage4_commands.emu`
(`cal` без аргументов зависит от текущей даты).

```text
$ python3 emulator.py --vfs tests/vfs/deep.zip --script scripts/stage4_commands.emu
[debug] Параметры запуска:
[debug]   --vfs    = tests/vfs/deep.zip
[debug]   --script = scripts/stage4_commands.emu
[debug]   имя VFS = deep; каталогов: 12, файлов: 9, байт: 183
deep:/$ # Этап 4: ls, cd, cal, tail (запуск с deep.zip). Строки с '-' — ожидаемые ошибки.
deep:/$ ls
a  etc  projects  README.md  tmp
deep:/$ ls -l
d  4096 a
d  4096 etc
d  4096 projects
-     7 README.md
d  4096 tmp
deep:/$ ls -a
.  ..  a  etc  projects  README.md  tmp
deep:/$ ls -la projects
d  4096 .
d  4096 ..
d  4096 app
d  4096 empty_dir
d  4096 lib
deep:/$ ls projects/app projects/lib
projects/app:
README.md  src

projects/lib:
readme.txt
deep:/$ ls a/b/c/d/deep.txt
a/b/c/d/deep.txt
deep:/$ cd projects
deep:/projects$ cd app/src
deep:/projects/app/src$ ls -l
-    12 main.py
-    22 util.py
deep:/projects/app/src$ cd ../..
deep:/projects$ cd /a/b/c/d
deep:/a/b/c/d$ ls
deep.txt
deep:/a/b/c/d$ cd
deep:/$ cd /a/b/c
deep:/a/b/c$ tail note.txt
note 3
note 4
note 5
note 6
note 7
note 8
note 9
note 10
note 11
note 12
deep:/a/b/c$ tail -n 3 note.txt
note 10
note 11
note 12
deep:/a/b/c$ tail -n 0 note.txt
deep:/a/b/c$ tail note.txt d/deep.txt
==> note.txt <==
note 3
note 4
note 5
note 6
note 7
note 8
note 9
note 10
note 11
note 12

==> d/deep.txt <==
Файл на 5-м уровне
deep:/a/b/c$ cal 2 2024
   February 2024
Su Mo Tu We Th Fr Sa
             1  2  3
 4  5  6  7  8  9 10
11 12 13 14 15 16 17
18 19 20 21 22 23 24
25 26 27 28 29
deep:/a/b/c$ cal 2026
                                  2026

      January                   February                   March
Su Mo Tu We Th Fr Sa      Su Mo Tu We Th Fr Sa      Su Mo Tu We Th Fr Sa
             1  2  3       1  2  3  4  5  6  7       1  2  3  4  5  6  7
 4  5  6  7  8  9 10       8  9 10 11 12 13 14       8  9 10 11 12 13 14
11 12 13 14 15 16 17      15 16 17 18 19 20 21      15 16 17 18 19 20 21
18 19 20 21 22 23 24      22 23 24 25 26 27 28      22 23 24 25 26 27 28
25 26 27 28 29 30 31                                29 30 31

       April                      May                       June
Su Mo Tu We Th Fr Sa      Su Mo Tu We Th Fr Sa      Su Mo Tu We Th Fr Sa
          1  2  3  4                      1  2          1  2  3  4  5  6
 5  6  7  8  9 10 11       3  4  5  6  7  8  9       7  8  9 10 11 12 13
12 13 14 15 16 17 18      10 11 12 13 14 15 16      14 15 16 17 18 19 20
19 20 21 22 23 24 25      17 18 19 20 21 22 23      21 22 23 24 25 26 27
26 27 28 29 30            24 25 26 27 28 29 30      28 29 30
                          31

        July                     August                  September
Su Mo Tu We Th Fr Sa      Su Mo Tu We Th Fr Sa      Su Mo Tu We Th Fr Sa
          1  2  3  4                         1             1  2  3  4  5
 5  6  7  8  9 10 11       2  3  4  5  6  7  8       6  7  8  9 10 11 12
12 13 14 15 16 17 18       9 10 11 12 13 14 15      13 14 15 16 17 18 19
19 20 21 22 23 24 25      16 17 18 19 20 21 22      20 21 22 23 24 25 26
26 27 28 29 30 31         23 24 25 26 27 28 29      27 28 29 30
                          30 31

      October                   November                  December
Su Mo Tu We Th Fr Sa      Su Mo Tu We Th Fr Sa      Su Mo Tu We Th Fr Sa
             1  2  3       1  2  3  4  5  6  7             1  2  3  4  5
 4  5  6  7  8  9 10       8  9 10 11 12 13 14       6  7  8  9 10 11 12
11 12 13 14 15 16 17      15 16 17 18 19 20 21      13 14 15 16 17 18 19
18 19 20 21 22 23 24      22 23 24 25 26 27 28      20 21 22 23 24 25 26
25 26 27 28 29 30 31      29 30                     27 28 29 30 31
deep:/a/b/c$ cal
    October 2026
Su Mo Tu We Th Fr Sa
             1  2  3
 4  5  6  7  8  9 10
11 12 13 14 15 16 17
18 19 20 21 22 23 24
25 26 27 28 29 30 31
deep:/a/b/c$ cd /
deep:/$ ls /nope
ls: cannot access '/nope': No such file or directory
[ожидаемая ошибка, код 2; скрипт продолжается]
deep:/$ ls -z
ls: invalid option -- 'z'
[ожидаемая ошибка, код 2; скрипт продолжается]
deep:/$ cd /nope
cd: /nope: No such file or directory
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ cd README.md
cd: README.md: Not a directory
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ cd a b
cd: too many arguments
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ tail
tail: missing file operand
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ tail nofile.txt
tail: cannot open 'nofile.txt' for reading: No such file or directory
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ tail a
tail: error reading 'a': Is a directory
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ tail -n abc README.md
tail: invalid number of lines: 'abc'
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ tail -n
tail: option requires an argument -- 'n'
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ cal 13 2026
cal: 13 is not a month number (1..12)
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ cal 5 0
cal: year '0' not in range 1..9999
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ cal abc
cal: usage: cal [[месяц] год]  (числа)
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ cal 1 2 3
cal: usage: cal [[месяц] год]  (числа)
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ exit
[код возврата: 0]
```

## Этап 5. Дополнительные команды

`mv источник назначение` — переименование или перенос файла/каталога. Если назначение — существующий каталог,
источник переносится внутрь него. Файл можно заменить файлом; остальные случаи «поверх существующего» — ошибка.
Изменяется только VFS в памяти, исходный ZIP остаётся прежним.

Обрабатываемые ошибки: нет операндов/назначения, лишние аргументы, источник не найден, источник и цель совпадают,
каталог в самого себя, перезапись каталога или каталогом, несуществующий родитель назначения, путь через файл,
перемещение корня и каталога, содержащего текущий.

Запуск: `python3 emulator.py --vfs tests/vfs/deep.zip --script scripts/stage5_mv.emu`

```text
$ python3 emulator.py --vfs tests/vfs/deep.zip --script scripts/stage5_mv.emu
[debug] Параметры запуска:
[debug]   --vfs    = tests/vfs/deep.zip
[debug]   --script = scripts/stage5_mv.emu
[debug]   имя VFS = deep; каталогов: 12, файлов: 9, байт: 183
deep:/$ # Этап 5: mv (запуск с deep.zip). Изменения только в памяти. Строки с '-' — ожидаемые ошибки.
deep:/$ ls
a  etc  projects  README.md  tmp
deep:/$ mv README.md INTRO.md
deep:/$ ls
a  etc  INTRO.md  projects  tmp
deep:/$ mv INTRO.md tmp
deep:/$ ls tmp
INTRO.md
deep:/$ mv tmp/INTRO.md projects/lib/intro.txt
deep:/$ ls projects/lib
intro.txt  readme.txt
deep:/$ mv a/b/mid.txt tmp
deep:/$ mv projects/empty_dir projects/archive
deep:/$ mv projects/archive tmp
deep:/$ ls projects tmp
projects:
app  lib

tmp:
archive  mid.txt
deep:/$ mv projects/app /etc
deep:/$ ls etc etc/app/src
etc:
app  config

etc/app/src:
main.py  util.py
deep:/$ cd /etc/app/src
deep:/etc/app/src$ mv main.py ../main_copy.py
deep:/etc/app/src$ ls . ..
.:
util.py

..:
main_copy.py  README.md  src
deep:/etc/app/src$ cd /
deep:/$ mv tmp/mid.txt projects/lib/intro.txt
deep:/$ tail projects/lib/intro.txt
mid
deep:/$ mv
mv: missing file operand
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ mv a
mv: missing destination file operand after 'a'
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ mv a b c
mv: too many arguments
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ mv nofile tmp
mv: cannot stat 'nofile': No such file or directory
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ mv a/b/c/d/deep.txt a/b/c/d/deep.txt
mv: 'a/b/c/d/deep.txt' and 'a/b/c/d/deep.txt' are the same file
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ mv a a/b/c
mv: cannot move 'a' to a subdirectory of itself
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ mv etc projects/lib/readme.txt
mv: cannot overwrite 'projects/lib/readme.txt': already exists
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ mv a/b/c/d projects/lib/x/y
mv: cannot move 'a/b/c/d' to 'projects/lib/x/y': No such file or directory
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ mv a/b/c/d/deep.txt/x tmp
mv: cannot stat 'a/b/c/d/deep.txt/x': Not a directory
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ mv / tmp
mv: cannot move the root directory
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ cd a/b
deep:/a/b$ mv /a /tmp
mv: cannot move '/a': it contains the current directory
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/a/b$ cd /
deep:/$ ls
a  etc  projects  tmp
deep:/$ ls a/b/c/d
deep.txt
deep:/$ exit
[код возврата: 0]
```
