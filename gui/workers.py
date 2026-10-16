"""Workers en QThread para no bloquear la UI."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QThread, Signal


class SearchWorker(QThread):
    finished_ok = Signal(list)
    failed = Signal(str)

    def __init__(self, fn: Callable[[], list], parent=None):
        super().__init__(parent)
        self._fn = fn

    def run(self):
        try:
            self.finished_ok.emit(self._fn())
        except Exception as e:
            self.failed.emit(str(e))


class DownloadWorker(QThread):
    progress = Signal(dict)
    finished_ok = Signal(dict)
    failed = Signal(str)

    def __init__(
        self,
        items: list,
        output: str,
        unzip: bool,
        single_version: bool,
        clean_tags: bool,
        parent=None,
    ):
        super().__init__(parent)
        self.items = items
        self.output = output
        self.unzip = unzip
        self.single_version = single_version
        self.clean_tags = clean_tags
        self._cancel = False

    def request_cancel(self):
        self._cancel = True

    def run(self):
        from romsfun_core import process_download_batch

        try:
            result = process_download_batch(
                self.items,
                base_output=self.output,
                unzip=self.unzip,
                single_version=self.single_version,
                clean_tags=self.clean_tags,
                on_progress=lambda event: self.progress.emit(event),
                cancel_check=lambda: self._cancel,
            )
            self.finished_ok.emit(result)
        except Exception as e:
            self.failed.emit(str(e))
