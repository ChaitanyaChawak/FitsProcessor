"""Consistent terminal output for FitsProcessor (no external dependencies).

Colours are used only when writing to a terminal and NO_COLOR is not set.
"""
import os
import re
import shutil
import sys
import textwrap
import unicodedata

_USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
_ANSI = re.compile(r"\033\[[0-9;]*m")
INDENT = "   "
LABEL_WIDTH = 14


def _style(code, text):
    return f"\033[{code}m{text}\033[0m" if _USE_COLOR else str(text)


def bold(text):   return _style("1", text)
def dim(text):    return _style("2", text)
def cyan(text):   return _style("36", text)
def green(text):  return _style("32", text)
def yellow(text): return _style("33", text)
def red(text):    return _style("31", text)


def visible_len(text):
    """Number of terminal columns the text occupies (ANSI codes excluded,
    wide East Asian characters such as 'ヮ' count as two, combining marks as zero)."""
    return sum(0 if unicodedata.combining(ch) else 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
               for ch in _ANSI.sub("", text))


def term_width():
    return min(shutil.get_terminal_size((100, 24)).columns, 100)


def step(number, total, title):
    """Print a numbered step header, e.g. '[2/4] Matching columns'."""
    print(f"\n{bold(cyan(f'[{number}/{total}]'))} {bold(title)}")


def info(label, value):
    """Print an aligned 'label  value' line."""
    print(f"{INDENT}{dim(f'{label:<{LABEL_WIDTH}}')}{value}")


def info_list(label, items):
    """Print an aligned label followed by a comma-separated list wrapped to the terminal width."""
    prefix = f"{INDENT}{' ' * LABEL_WIDTH}"
    width = max(term_width() - len(prefix), 30)
    lines = textwrap.wrap(", ".join(items), width=width) or [""]
    info(label, lines[0])
    for line in lines[1:]:
        print(f"{prefix}{line}")


def item(text):
    """Print an indented sub-item."""
    print(f"{INDENT}{' ' * LABEL_WIDTH}{text}")


def success(text):
    print(f"{INDENT}{green('✓')} {text}")


def warn(text):
    print(f"{INDENT}{yellow('!')} {yellow(text)}")


def error(text):
    print(f"{INDENT}{red('✗')} {red(text)}")


def box(title, rows):
    """Print a box with a title and aligned (label, value) rows.
    Falls back to plain lines when the box would not fit in the terminal."""
    lines = [f"{dim(f'{label:<8}')}{value}" for label, value in rows]
    inner = max([visible_len(line) for line in lines] + [visible_len(title) + 2])
    if inner + 4 > shutil.get_terminal_size((100, 24)).columns:
        print(f"\n{bold(title)}")
        for line in lines:
            print(f"{INDENT}{line}")
        return
    print("\n" + green("╭─ ") + bold(title) + green(" " + "─" * (inner - visible_len(title) - 1) + "╮"))
    for line in lines:
        print(f"{green('│')} {line}{' ' * (inner - visible_len(line))} {green('│')}")
    print(green("╰" + "─" * (inner + 2) + "╯"))


def format_size(num_bytes):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num_bytes < 1024 or unit == "TB":
            return f"{num_bytes:.0f} {unit}" if unit == "B" else f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024


def format_duration(seconds):
    if seconds < 60:
        return f"{seconds:.1f} s"
    minutes, seconds = divmod(seconds, 60)
    return f"{int(minutes)} min {seconds:.0f} s"


# tqdm bar layout matching the rest of the output
BAR_FORMAT = INDENT + "{desc:<" + str(LABEL_WIDTH) + "}{bar:30} {percentage:3.0f}%  {n_fmt}/{total_fmt} chunks  [{elapsed}<{remaining}]"
