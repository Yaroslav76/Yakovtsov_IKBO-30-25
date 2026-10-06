# Эмулятор оболочки UNIX-подобной ОС (вариант 30)

Консольное приложение на Python 3.8+ (только стандартная библиотека), имитирующее работу в командной строке UNIX.
Файловая система — виртуальная (VFS), целиком в памяти; источник VFS — ZIP-архив.

## Быстрый старт

```text
python3 emulator.py [--vfs PATH] [--script PATH]      # на Windows: python emulator.py ...
```

| Параметр | Смысл |
|---|---|
| `--vfs PATH` | ZIP-архив с VFS; если не указан — VFS по умолчанию создаётся в памяти |
| `--script PATH` | стартовый скрипт: команды выполняются с показом ввода и вывода, остановка на первой ошибке |

Команды: `ls`, `cd`, `cal`, `tail`, `mv`, `exit`, служебная `vfs-info`.
Пример: `python3 emulator.py --vfs tests/vfs/deep.zip` (интерактивно) или
`python3 emulator.py --vfs tests/vfs/deep.zip --script scripts/all_commands.emu`.

## Структура проекта

```text
emulator.py        точка входа: парсер, REPL, параметры, стартовые скрипты
commands.py        команды ls, cd, cal, tail, mv, exit, vfs-info
vfs.py             VFS в памяти, загрузка из ZIP
scripts/*.emu      стартовые скрипты эмулятора (по этапам + all_commands.emu)
tests/test_stageN.sh|.bat   скрипты реальной ОС (Linux/macOS | Windows), вызывающие эмулятор
tests/make_vfs.py  генератор тестовых VFS; готовые архивы — в tests/vfs/
docs/              сохранённый вывод демонстраций (подставлен ниже)
```

Все демонстрации ниже — реальный вывод; чтобы воспроизвести, запустите соответствующий скрипт из `tests/`.
Строки стартовых скриптов, начинающиеся с `-`, — «ожидаемые ошибки» (см. этап 3).

---

## Этап 1. REPL

**Что сделано**

- CLI-приложение с циклом «приглашение → ввод → выполнение». Приглашение содержит имя VFS: `default:/$ `.
- Парсер строки (`tokenize` в `emulator.py`): разделение по пробелам, кавычки `'...'` (без раскрытия) и `"..."`
  (с раскрытием), экранирование `\`, комментарии `#`, раскрытие переменных окружения реальной ОС:
  `$HOME`, `${HOME}`. Неопределённая переменная раскрывается в пустую строку (пустой аргумент без кавычек исчезает,
  как в bash). На Windows `$HOME` при отсутствии `HOME` берётся из `USERPROFILE`.
- Команды-заглушки `ls`, `cd` печатают своё имя и аргументы. Команда `exit [код]` завершает эмулятор.
- Ошибки: неизвестная команда (код 127), незакрытая кавычка, неверная подстановка `${1bad}`,
  `exit` с нечисловым или лишним аргументом. Ctrl+D (EOF) — выход, Ctrl+C — отмена строки.
- Если ввод идёт не с терминала (канал/файл), введённые строки дублируются в вывод — так удобно показывать диалог.

**Демонстрация** (`HOME=/home/rid USER=rid python3 emulator.py < docs/stage1.in`):

```text
default:/$ ls
ls args: []
default:/$ ls -l /tmp "my dir"
ls args: ['-l', '/tmp', 'my dir']
default:/$ cd /home
cd args: ['/home']
default:/$ ls $HOME ${USER} "$HOME/x" '$HOME' \$HOME
ls args: ['/home/rid', 'rid', '/home/rid/x', '$HOME', '$HOME']
default:/$ ls $NOPE_UNDEFINED a
ls args: ['a']
default:/$ ls "$HOME and ${USER}"
ls args: ['/home/rid and rid']
default:/$ cd
cd args: []
default:/$ # комментарий
default:/$ foo bar
foo: command not found
default:/$ ls "незакрытая
parse error: unexpected EOF while looking for matching `"'
default:/$ ls ${1bad}
parse error: bad substitution
default:/$ exit abc
exit: abc: numeric argument required
default:/$ exit 1 2
exit: too many arguments
default:/$ exit 3
```

---

## Этап 2. Конфигурация

**Что сделано**

- Параметры командной строки: `--vfs PATH` (путь к физическому расположению VFS) и `--script PATH`
  (путь к стартовому скрипту). Оба необязательны. На этом этапе VFS только передаётся в приложение
  (загрузка — этап 3).
- При запуске печатается отладочный вывод всех заданных параметров (`[debug] ...`).
- Стартовый скрипт (`*.emu`): каждая непустая строка показывается с приглашением, затем её вывод — получается
  имитация диалога. Скрипт **останавливается при первой ошибке** (ненулевой код возврата команды, ошибка разбора,
  неизвестная команда); выводится номер строки. После скрипта (в т. ч. после ошибки) эмулятор переходит в
  интерактивный режим; `exit` в скрипте завершает эмулятор сразу. Нечитаемый скрипт — код возврата 1.
- Тестовые скрипты реальной ОС: `tests/test_stage2.sh` (Linux/macOS) и `tests/test_stage2.bat` (Windows) —
  вызывают эмулятор со всеми сочетаниями параметров, включая ошибочные. Стартовые скрипты — в `scripts/`.

**Демонстрация** (`bash tests/test_stage2.sh`, интерактивный режим закрывается EOF из `/dev/null`):

```text

$ python3 emulator.py 
[debug] Параметры запуска:
[debug]   --vfs    = (не задан)
[debug]   --script = (не задан)
default:/$ exit
[код возврата: 0]

$ python3 emulator.py --vfs some/path/vfs.zip
[debug] Параметры запуска:
[debug]   --vfs    = some/path/vfs.zip
[debug]   --script = (не задан)
default:/$ exit
[код возврата: 0]

$ python3 emulator.py --script scripts/stage2_ok.emu
[debug] Параметры запуска:
[debug]   --vfs    = (не задан)
[debug]   --script = scripts/stage2_ok.emu
default:/$ # Стартовый скрипт этапа 2: ошибок нет
default:/$ ls -l /tmp
ls args: ['-l', '/tmp']
default:/$ cd "/home/$USER"
cd args: ['/home/rid']
default:/$ ls $HOME
ls args: ['/home/rid']
default:/$ exit
[код возврата: 0]

$ python3 emulator.py --vfs vfs.zip --script scripts/stage2_ok.emu
[debug] Параметры запуска:
[debug]   --vfs    = vfs.zip
[debug]   --script = scripts/stage2_ok.emu
default:/$ # Стартовый скрипт этапа 2: ошибок нет
default:/$ ls -l /tmp
ls args: ['-l', '/tmp']
default:/$ cd "/home/$USER"
cd args: ['/home/rid']
default:/$ ls $HOME
ls args: ['/home/rid']
default:/$ exit
[код возврата: 0]

$ python3 emulator.py --script scripts/stage2_error.emu
[debug] Параметры запуска:
[debug]   --vfs    = (не задан)
[debug]   --script = scripts/stage2_error.emu
default:/$ # Скрипт останавливается на первой ошибке (третья строка)
default:/$ ls one
ls args: ['one']
default:/$ nosuchcmd arg
nosuchcmd: command not found
Скрипт остановлен: ошибка в строке 3 (код 127)
default:/$ exit
[код возврата: 0]

$ python3 emulator.py --script scripts/stage2_exit.emu
[debug] Параметры запуска:
[debug]   --vfs    = (не задан)
[debug]   --script = scripts/stage2_exit.emu
default:/$ # exit в скрипте завершает эмулятор с заданным кодом
default:/$ ls before-exit
ls args: ['before-exit']
default:/$ exit 7
[код возврата: 7]

$ python3 emulator.py --script scripts/no_such_script.emu
[debug] Параметры запуска:
[debug]   --vfs    = (не задан)
[debug]   --script = scripts/no_such_script.emu
Ошибка: не удалось прочитать скрипт 'scripts/no_such_script.emu': No such file or directory
[код возврата: 1]

$ python3 emulator.py --unknown
usage: emulator.py [-h] [--vfs PATH] [--script PATH]
emulator.py: error: unrecognized arguments: --unknown
[код возврата: 2]
```

---

## Этап 3. VFS

**Что сделано** (модуль `vfs.py`)

- Источник VFS — ZIP-архив (`--vfs PATH`). Архив **целиком читается в память** (`zipfile` + `io.BytesIO`), дерево
  каталогов и файлов строится в оперативной памяти; на диск ничего не распаковывается и не пишется. Исходный ZIP
  никогда не изменяется.
- Содержимое файлов хранится как `bytes`. Файл считается двоичным, если не декодируется как UTF-8 или содержит
  NUL; при выводе его данные представляются в **base64** (строки по 76 символов).
- Имя VFS = имя архива без расширения (`deep.zip` → `deep`), попадает в приглашение: `deep:/$ `.
- Ошибки загрузки: файл не найден, это каталог, неверный формат / повреждённый архив, небезопасные пути (`..`),
  конфликт «файл/каталог» в архиве. Сообщение `Ошибка загрузки VFS: ...`, код возврата 1.
- Если `--vfs` не указан, в памяти создаётся VFS по умолчанию (имя `default`, несколько файлов и каталогов).
- Служебная команда `vfs-info` — имя, источник и размер VFS (нужна, чтобы увидеть, что загрузилось).
- Расширение скриптов: строка вида `-команда` — **ожидаемая ошибка**: ошибка показывается, но скрипт продолжается
  (без этого в одном скрипте нельзя показать несколько ошибок, ведь скрипт стоит на первой). Обычные строки по-прежнему
  останавливают скрипт.
- Тестовые архивы создаёт `tests/make_vfs.py` (лежат в `tests/vfs/`): `minimal.zip` (1 файл), `files.zip`
  (несколько файлов, скрытый, двоичный, пустой каталог), `deep.zip` (вложенность до 5 уровней), `not_a_zip.zip` и
  `corrupt.zip` (для ошибок).
- Скрипты реальной ОС: `tests/test_stage3.sh` / `.bat` — все варианты VFS и все ошибки загрузки.
  Стартовый скрипт всех команд этапов 1–3: `scripts/stage3_all.emu`.

**Демонстрация** (`bash tests/test_stage3.sh`):

```text

$ python3 emulator.py --script scripts/stage3_info.emu
[debug] Параметры запуска:
[debug]   --vfs    = (не задан)
[debug]   --script = scripts/stage3_info.emu
[debug] VFS не указана: создана VFS по умолчанию в памяти
[debug]   имя VFS = default; каталогов: 5, файлов: 4, байт: 325
default:/$ vfs-info
name:   default
source: (в памяти, по умолчанию)
dirs:   5
files:  4
bytes:  325
default:/$ ls
ls args: []
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
dirs:   0
files:  1
bytes:  12
minimal:/$ ls
ls args: []
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
dirs:   1
files:  6
bytes:  1122
files:/$ ls
ls args: []
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
dirs:   12
files:  9
bytes:  183
deep:/$ ls
ls args: []
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
deep:/$ # Все команды этапов 1-3 (успешные режимы) + ожидаемые ошибки (строки с '-')
deep:/$ vfs-info
name:   deep
source: tests/vfs/deep.zip
dirs:   12
files:  9
bytes:  183
deep:/$ ls
ls args: []
deep:/$ ls -l /home "my dir"
ls args: ['-l', '/home', 'my dir']
deep:/$ cd /home/user
cd args: ['/home/user']
deep:/$ ls $HOME ${USER} "$HOME/x" '$HOME' \$HOME
ls args: ['/home/rid', 'rid', '/home/rid/x', '$HOME', '$HOME']
deep:/$ ls $NOPE_UNDEFINED a
ls args: ['a']
deep:/$ # --- обработка ошибок: строки с '-' не останавливают скрипт ---
deep:/$ vfs-info extra
vfs-info: too many arguments
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ unknown_cmd 1 2
unknown_cmd: command not found
[ожидаемая ошибка, код 127; скрипт продолжается]
deep:/$ ls "незакрытая кавычка
parse error: unexpected EOF while looking for matching `"'
[ожидаемая ошибка, код 2; скрипт продолжается]
deep:/$ ls ${1bad}
parse error: bad substitution
[ожидаемая ошибка, код 2; скрипт продолжается]
deep:/$ exit abc
exit: abc: numeric argument required
[ожидаемая ошибка, код 2; скрипт продолжается]
deep:/$ exit 1 2
exit: too many arguments
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ # --- обычная ошибка останавливает скрипт ---
deep:/$ nosuchcmd
nosuchcmd: command not found
Скрипт остановлен: ошибка в строке 16 (код 127)
deep:/$ exit
[код возврата: 0]
```

---

## Этап 4. Основные команды

**Что сделано** (`commands.py`). Сообщения об ошибках — в формате coreutils (на английском), как в настоящей оболочке.

| Команда | Режимы |
|---|---|
| `ls [-l] [-a] [путь...]` | текущий каталог; каталог; файл; несколько путей (файлы, затем каталоги с заголовками `путь:`); `-a` — скрытые файлы и `.`/`..`; `-l` — длинный формат (тип/права условные, размер, имя); `-la`; `--`. Вывод в столбцах по ширине терминала. |
| `cd [путь \| -]` | без аргументов — корень VFS; абсолютные/относительные пути, `.`/`..`; `cd -` — предыдущий каталог (печатает его). Приглашение показывает текущий каталог. |
| `cal [-m] [[месяц] год]` | без аргументов — текущий месяц; `год` — весь год; `месяц год` (число 1–12 или имя `Feb`/`February`); `-m` — неделя с понедельника. |
| `tail [-n N \| -n +N \| -N] [-q] файл...` | последние 10 строк; `-n N`/`-N` — последние N; `-n +N` — начиная со строки N; несколько файлов с заголовками `==> имя <==` (`-q` — без заголовков); двоичные файлы выводятся в base64. |

Особенности: ввод — только аргументы (конвейеров и `stdin` нет); если последняя строка файла без `\n`,
`tail` добавляет перевод строки, чтобы приглашение не «прилипало» к выводу.
Обрабатываемые ошибки: несуществующий путь, `cd` в файл, `tail` каталога, неверное число/опция, лишние аргументы,
неверный месяц/год и т. д.

**Стартовые скрипты:** `scripts/stage4_commands.emu` (VFS `deep.zip`, все режимы + ошибки) и
`scripts/stage4_files.emu` (VFS `files.zip`: скрытые, пустой каталог, двоичный файл, файл без `\n`).
Запуск обоих: `bash tests/test_stage4.sh` (или `tests\test_stage4.bat`).

**Демонстрация** (вывод `bash tests/test_stage4.sh`; результат `cal` без аргументов зависит от текущей даты):

```text

$ python3 emulator.py --vfs tests/vfs/deep.zip --script scripts/stage4_commands.emu
[debug] Параметры запуска:
[debug]   --vfs    = tests/vfs/deep.zip
[debug]   --script = scripts/stage4_commands.emu
[debug]   имя VFS = deep; каталогов: 12, файлов: 9, байт: 183
deep:/$ # Этап 4: ls, cd, cal, tail на VFS deep.zip. Запуск:
deep:/$ #   python3 emulator.py --vfs tests/vfs/deep.zip --script scripts/stage4_commands.emu
deep:/$ # ---------- ls ----------
deep:/$ ls
a  etc  projects  README.md  tmp
deep:/$ ls -l
drwxr-xr-x 4096 a
drwxr-xr-x 4096 etc
drwxr-xr-x 4096 projects
-rw-r--r--    7 README.md
drwxr-xr-x 4096 tmp
deep:/$ ls -a
.  ..  a  etc  projects  README.md  tmp
deep:/$ ls -la projects
drwxr-xr-x 4096 .
drwxr-xr-x 4096 ..
drwxr-xr-x 4096 app
drwxr-xr-x 4096 empty_dir
drwxr-xr-x 4096 lib
deep:/$ ls projects/app projects/lib
projects/app:
README.md  src

projects/lib:
readme.txt
deep:/$ ls README.md projects
README.md

projects:
app  empty_dir  lib
deep:/$ ls a/b/c/d/deep.txt
a/b/c/d/deep.txt
deep:/$ ls -l /a/b/c
drwxr-xr-x 4096 d
-rw-r--r--   87 note.txt
deep:/$ ls -- projects
app  empty_dir  lib
deep:/$ # ---------- cd ----------
deep:/$ cd projects
deep:/projects$ cd app/src
deep:/projects/app/src$ ls -l
-rw-r--r-- 12 main.py
-rw-r--r-- 22 util.py
deep:/projects/app/src$ cd ..
deep:/projects/app$ cd ../..
deep:/$ cd -
/projects/app
deep:/projects/app$ cd -
/
deep:/$ cd /a/b/c/d
deep:/a/b/c/d$ ls
deep.txt
deep:/a/b/c/d$ cd
deep:/$ # ---------- tail ----------
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
deep:/a/b/c$ tail -3 note.txt
note 10
note 11
note 12
deep:/a/b/c$ tail -n +10 note.txt
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
deep:/a/b/c$ tail -q note.txt ../mid.txt
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
mid
deep:/a/b/c$ tail -n 1 /README.md
# deep
deep:/a/b/c$ # ---------- cal ----------
deep:/a/b/c$ cal 2 2024
   February 2024
Su Mo Tu We Th Fr Sa
             1  2  3
 4  5  6  7  8  9 10
11 12 13 14 15 16 17
18 19 20 21 22 23 24
25 26 27 28 29
deep:/a/b/c$ cal -m 10 2026
    October 2026
Mo Tu We Th Fr Sa Su
          1  2  3  4
 5  6  7  8  9 10 11
12 13 14 15 16 17 18
19 20 21 22 23 24 25
26 27 28 29 30 31
deep:/a/b/c$ cal Feb 2026
   February 2026
Su Mo Tu We Th Fr Sa
 1  2  3  4  5  6  7
 8  9 10 11 12 13 14
15 16 17 18 19 20 21
22 23 24 25 26 27 28
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
deep:/$ # ---------- ошибки (ожидаемые, скрипт продолжается) ----------
deep:/$ ls /nope
ls: cannot access '/nope': No such file or directory
[ожидаемая ошибка, код 2; скрипт продолжается]
deep:/$ ls -z
ls: invalid option -- 'z'
[ожидаемая ошибка, код 2; скрипт продолжается]
deep:/$ ls projects /nope README.md
ls: cannot access '/nope': No such file or directory
README.md

projects:
app  empty_dir  lib
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
deep:/$ cd -x
cd: -x: invalid option
[ожидаемая ошибка, код 2; скрипт продолжается]
deep:/$ tail
tail: missing file operand
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ tail nofile.txt
tail: cannot open 'nofile.txt' for reading: No such file or directory
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ tail d
tail: cannot open 'd' for reading: No such file or directory
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ tail -n abc note.txt
tail: invalid number of lines: 'abc'
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ tail -n
tail: option requires an argument -- 'n'
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ tail -z note.txt
tail: invalid option -- 'z'
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ cal 13 2026
cal: 13 is neither a month number (1..12) nor a name
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ cal 5 0
cal: year '0' not in range 1..9999
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ cal abc
cal: year 'abc' not in range 1..9999
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ cal 1 2 3
cal: too many arguments
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ cal -x
cal: invalid option -- 'x'
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ exit
[код возврата: 0]

$ python3 emulator.py --vfs tests/vfs/files.zip --script scripts/stage4_files.emu
[debug] Параметры запуска:
[debug]   --vfs    = tests/vfs/files.zip
[debug]   --script = scripts/stage4_files.emu
[debug]   имя VFS = files; каталогов: 1, файлов: 6, байт: 1122
files:/$ # Этап 4 на VFS files.zip: скрытые файлы, пустой каталог, двоичный файл, файл без \n в конце. Запуск:
files:/$ #   python3 emulator.py --vfs tests/vfs/files.zip --script scripts/stage4_files.emu
files:/$ ls
empty  log.txt  logo.bin  no_newline.txt  readme.txt  short.txt
files:/$ ls -a
.  ..  .hidden  empty  log.txt  logo.bin  no_newline.txt  readme.txt  short.txt
files:/$ ls -l
drwxr-xr-x 4096 empty
-rw-r--r--  766 log.txt
-rw-r--r--  256 logo.bin
-rw-r--r--   26 no_newline.txt
-rw-r--r--   53 readme.txt
-rw-r--r--   14 short.txt
files:/$ ls empty
files:/$ ls -a empty
.  ..
files:/$ cd empty
files:/empty$ ls -a
.  ..
files:/empty$ cd ..
files:/$ tail -n 3 log.txt
запись журнала 23
запись журнала 24
запись журнала 25
files:/$ tail -n +24 log.txt
запись журнала 24
запись журнала 25
files:/$ tail -n 2 no_newline.txt
first
last without newline
files:/$ tail .hidden short.txt
==> .hidden <==
secret

==> short.txt <==
one
two
three
files:/$ tail -n 2 logo.bin
q6ytrq+wsbKztLW2t7i5uru8vb6/wMHCw8TFxsfIycrLzM3Oz9DR0tPU1dbX2Nna29zd3t/g4eLj
5OXm5+jp6uvs7e7v8PHy8/T19vf4+fr7/P3+/w==
files:/$ tail empty
tail: error reading 'empty': Is a directory
[ожидаемая ошибка, код 1; скрипт продолжается]
files:/$ exit
[код возврата: 0]
```

---

## Этап 5. Дополнительные команды

**Что сделано:** команда `mv`, изменяющая VFS только в памяти (исходный ZIP не затрагивается).

| Режим | Пример |
|---|---|
| переименование файла/каталога | `mv README.md INTRO.md` |
| перемещение в существующий каталог | `mv INTRO.md tmp` |
| перемещение с переименованием | `mv tmp/INTRO.md projects/lib/intro.txt` |
| несколько источников в каталог | `mv a/b/mid.txt a/b/c/note.txt tmp` |
| каталог целиком | `mv projects/app /etc` |
| перезапись существующего файла (по умолчанию) / запрет `-n` | `mv x y` / `mv -n x y` |
| подробный вывод `-v` | `mv -v x dir` → `'x' -> 'dir/x'` |
| окончание опций `--` | `mv -- tmp/archive projects` |

Обрабатываемые ошибки: нет операндов / нет назначения; источник не найден; неверная опция; источник и цель совпадают;
каталог в самого себя; несколько источников в «не каталог»; каталог поверх файла и файл поверх каталога;
непустой каталог-цель; несуществующий родитель; путь через файл; перемещение корня; перемещение каталога,
содержащего текущий (`it contains the current directory` — ограничение эмулятора).

**Стартовые скрипты:** `scripts/stage5_mv.emu` (все режимы `mv` + ошибки), `scripts/stage5_check.emu`
(повторный запуск показывает исходную структуру — изменения не сохраняются), итоговый `scripts/all_commands.emu`
(все команды всех этапов). `bash tests/test_stage5.sh` (или `tests\test_stage5.bat`) также сверяет SHA-256
ZIP-архива до и после — он не меняется.

**Демонстрация** (вывод `bash tests/test_stage5.sh`):

```text
sha256 deep.zip до запуска:    91a680e6beb2f0d6

$ python3 emulator.py --vfs tests/vfs/deep.zip --script scripts/stage5_mv.emu
[debug] Параметры запуска:
[debug]   --vfs    = tests/vfs/deep.zip
[debug]   --script = scripts/stage5_mv.emu
[debug]   имя VFS = deep; каталогов: 12, файлов: 9, байт: 183
deep:/$ # Этап 5: mv, изменения только в памяти. Запуск:
deep:/$ #   python3 emulator.py --vfs tests/vfs/deep.zip --script scripts/stage5_mv.emu
deep:/$ ls
a  etc  projects  README.md  tmp
deep:/$ # ---------- переименование файла ----------
deep:/$ mv README.md INTRO.md
deep:/$ ls
a  etc  INTRO.md  projects  tmp
deep:/$ # ---------- перемещение файла в каталог (-v показывает действие) ----------
deep:/$ mv -v INTRO.md tmp
'INTRO.md' -> 'tmp/INTRO.md'
deep:/$ ls tmp
INTRO.md
deep:/$ # ---------- переименование + перемещение в другой каталог ----------
deep:/$ mv tmp/INTRO.md projects/lib/intro.txt
deep:/$ ls projects/lib
intro.txt  readme.txt
deep:/$ # ---------- несколько источников в каталог ----------
deep:/$ mv -v a/b/mid.txt a/b/c/note.txt tmp
'a/b/mid.txt' -> 'tmp/mid.txt'
'a/b/c/note.txt' -> 'tmp/note.txt'
deep:/$ ls tmp
mid.txt  note.txt
deep:/$ ls a/b a/b/c
a/b:
c

a/b/c:
d
deep:/$ # ---------- переименование и перемещение каталога ----------
deep:/$ mv projects/empty_dir projects/archive
deep:/$ mv projects/archive tmp
deep:/$ ls projects tmp
projects:
app  lib

tmp:
archive  mid.txt  note.txt
deep:/$ # ---------- каталог с содержимым ----------
deep:/$ mv -v projects/app /etc
'projects/app' -> '/etc/app'
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
deep:/etc/app/src$ tail ../main_copy.py
print('hi')
deep:/etc/app/src$ cd /
deep:/$ # ---------- перезапись файла и режим -n ----------
deep:/$ mv tmp/mid.txt tmp/note.txt
deep:/$ tail tmp/note.txt
mid
deep:/$ mv -n projects/lib/intro.txt tmp/note.txt
deep:/$ tail tmp/note.txt
mid
deep:/$ mv -v projects/lib/intro.txt tmp/note.txt
'projects/lib/intro.txt' -> 'tmp/note.txt'
deep:/$ tail tmp/note.txt
# deep
deep:/$ # ---------- '--' и перемещение каталога ----------
deep:/$ mv -- tmp/archive projects
deep:/$ ls projects
archive  lib
deep:/$ # ---------- подготовка к ошибкам ----------
deep:/$ mv tmp/note.txt tmp/app
deep:/$ mv projects/archive projects/src
deep:/$ ls tmp projects
projects:
lib  src

tmp:
app
deep:/$ # ---------- ошибки (ожидаемые, скрипт продолжается) ----------
deep:/$ mv
mv: missing file operand
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ mv a
mv: missing destination file operand after 'a'
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ mv nofile tmp
mv: cannot stat 'nofile': No such file or directory
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ mv -z a tmp
mv: invalid option -- 'z'
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ mv a/b/c/d/deep.txt a/b/c/d/deep.txt
mv: 'a/b/c/d/deep.txt' and 'a/b/c/d/deep.txt' are the same file
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ mv a a/b/c
mv: cannot move 'a' to a subdirectory of itself, 'a/b/c/a'
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ mv a/b a/b/c/d/deep.txt
mv: cannot move 'a/b' to a subdirectory of itself, 'a/b/c/d/deep.txt'
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ mv a/b/c/d/deep.txt etc/app/README.md projects/lib/readme.txt
mv: target 'projects/lib/readme.txt' is not a directory
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ mv etc/app tmp/app
mv: cannot overwrite non-directory 'tmp/app' with directory 'etc/app'
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ mv tmp/app etc
mv: cannot overwrite directory 'etc/app' with non-directory
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ mv projects/src etc/app
mv: cannot move 'projects/src' to 'etc/app/src': Directory not empty
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ mv a/b/c/d projects/lib/x/y
mv: cannot move 'a/b/c/d' to 'projects/lib/x/y': No such file or directory
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ mv a/b/c/d/deep.txt/x tmp
mv: cannot stat 'a/b/c/d/deep.txt/x': Not a directory
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ mv a/b/c/d/deep.txt tmp/newname/
mv: cannot move to 'tmp/newname/': Not a directory
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ mv / tmp
mv: cannot move the root directory
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ cd a/b
deep:/a/b$ mv /a /tmp
mv: cannot move '/a': it contains the current directory
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/a/b$ mv .. /tmp
mv: cannot move '..': it contains the current directory
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/a/b$ cd /
deep:/$ # ---------- состояние после ошибок не повреждено ----------
deep:/$ ls
a  etc  projects  tmp
deep:/$ ls a/b/c/d etc/app
a/b/c/d:
deep.txt

etc/app:
main_copy.py  README.md  src
deep:/$ exit
[код возврата: 0]

sha256 deep.zip после запуска: 91a680e6beb2f0d6  (должен совпадать)

$ python3 emulator.py --vfs tests/vfs/deep.zip --script scripts/stage5_check.emu
[debug] Параметры запуска:
[debug]   --vfs    = tests/vfs/deep.zip
[debug]   --script = scripts/stage5_check.emu
[debug]   имя VFS = deep; каталогов: 12, файлов: 9, байт: 183
deep:/$ # Показывает исходную структуру VFS (после предыдущего запуска с mv): ZIP-файл не изменился
deep:/$ ls
a  etc  projects  README.md  tmp
deep:/$ ls projects
app  empty_dir  lib
deep:/$ tail README.md
# deep
deep:/$ exit
[код возврата: 0]

$ python3 emulator.py --vfs tests/vfs/deep.zip --script scripts/all_commands.emu
[debug] Параметры запуска:
[debug]   --vfs    = tests/vfs/deep.zip
[debug]   --script = scripts/all_commands.emu
[debug]   имя VFS = deep; каталогов: 12, файлов: 9, байт: 183
deep:/$ # Итоговый стартовый скрипт: все команды всех этапов. Запуск:
deep:/$ #   python3 emulator.py --vfs tests/vfs/deep.zip --script scripts/all_commands.emu
deep:/$ vfs-info
name:   deep
source: tests/vfs/deep.zip
dirs:   12
files:  9
bytes:  183
deep:/$ ls -la
drwxr-xr-x 4096 .
drwxr-xr-x 4096 ..
drwxr-xr-x 4096 a
drwxr-xr-x 4096 etc
drwxr-xr-x 4096 projects
-rw-r--r--    7 README.md
drwxr-xr-x 4096 tmp
deep:/$ ls $NOPE_UNDEFINED projects "a/b"
a/b:
c  mid.txt

projects:
app  empty_dir  lib
deep:/$ cd a/b/c
deep:/a/b/c$ ls -l
drwxr-xr-x 4096 d
-rw-r--r--   87 note.txt
deep:/a/b/c$ tail -n 4 note.txt
note 9
note 10
note 11
note 12
deep:/a/b/c$ tail -q note.txt d/deep.txt
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
Файл на 5-м уровне
deep:/a/b/c$ cd -
/
deep:/$ mv -v README.md projects/app/INTRO.md
'README.md' -> 'projects/app/INTRO.md'
deep:/$ ls projects/app
INTRO.md  README.md  src
deep:/$ cal -m 2 2024
   February 2024
Mo Tu We Th Fr Sa Su
          1  2  3  4
 5  6  7  8  9 10 11
12 13 14 15 16 17 18
19 20 21 22 23 24 25
26 27 28 29
deep:/$ ls /nope
ls: cannot access '/nope': No such file or directory
[ожидаемая ошибка, код 2; скрипт продолжается]
deep:/$ cd /nope
cd: /nope: No such file or directory
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ tail /nope
tail: cannot open '/nope' for reading: No such file or directory
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ mv /nope tmp
mv: cannot stat '/nope': No such file or directory
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ cal 13 2026
cal: 13 is neither a month number (1..12) nor a name
[ожидаемая ошибка, код 1; скрипт продолжается]
deep:/$ exit abc
exit: abc: numeric argument required
[ожидаемая ошибка, код 2; скрипт продолжается]
deep:/$ exit 0
[код возврата: 0]
```
