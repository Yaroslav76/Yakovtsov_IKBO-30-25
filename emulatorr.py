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

