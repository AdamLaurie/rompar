import json
import os
import sys
from PyQt5.QtWidgets import QMessageBox

def exit_message(msg, prefer_cli=True):
    # TODO: consider making this a config option
    # Until then, in practice most Windows users want message boxes 
    # and most Linux users want console messages
    ""
    if prefer_cli is None:
        prefer_cli = os.name == 'posix'

    if prefer_cli:
        sys.exit(msg)
    else:
        QMessageBox.about(None, "Oh noes!", msg)
        sys.exit(msg)

def json_load_exit_bad(fn, prefix):
    if not os.path.exists(fn):
        exit_message("%s: file does not exist: %s" % (prefix, fn))
    try:
        return json.load(open(fn, "r"))
    except json.decoder.JSONDecodeError:
        exit_message("%s: file is not valid JSON: %s" % (prefix, fn))
