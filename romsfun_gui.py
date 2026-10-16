#!/usr/bin/env python3
"""Punto de entrada de la app de escritorio PySide6."""

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(SCRIPT_DIR, ".venv", "bin", "python3")
if os.path.exists(VENV_PYTHON) and sys.executable != VENV_PYTHON and "VIRTUAL_ENV" not in os.environ:
    os.execv(VENV_PYTHON, [VENV_PYTHON] + sys.argv)

sys.path.insert(0, SCRIPT_DIR)

from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("RomsFun Downloader")
    app.setOrganizationName("RomsFun")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
