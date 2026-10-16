"""Ventana principal — diseño equivalente a la UI Electron (azul celeste)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from PySide6.QtCore import Qt, QSettings, QSize
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from romsfun_core import CONSOLE_OPTIONS, extract_console_from_url, search_roms, list_console_roms
from romsfun_core.catalog import pages_for_limit

from .styles import APP_QSS
from .workers import DownloadWorker, SearchWorker

SCRIPT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = str(SCRIPT_DIR / "downloads")

TABS = {
    "search": ("Buscar juegos", "Encuentra ROMs por nombre y descarga la mejor versión"),
    "console": ("Por consola", "Busca por nombre dentro de una consola o lista un lote completo"),
    "url": ("URL directa", "Pega el enlace de la ficha o descarga en RomsFun"),
    "settings": ("Ajustes", "Carpeta de salida, idioma y limpieza FAT32"),
}


def _unique_consoles():
    seen = set()
    out = []
    for c in CONSOLE_OPTIONS:
        if c["slug"] not in seen:
            seen.add(c["slug"])
            out.append(c)
    return out


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RomsFun Downloader")
        self.resize(1180, 760)
        self.setMinimumSize(920, 640)

        self.settings = QSettings("RomsFun", "Downloader")
        self.games: list[dict] = []
        self._search_worker: SearchWorker | None = None
        self._download_worker: DownloadWorker | None = None
        self._busy = False
        self._loading = False

        self._build_ui()
        self.setStyleSheet(APP_QSS)
        self._apply_dark_palette()
        self._load_settings()
        self._show_tab("search")

    def _apply_dark_palette(self):
        pal = QPalette()
        pal.setColor(QPalette.Window, QColor("#0b1f33"))
        pal.setColor(QPalette.WindowText, QColor("#f3fafd"))
        pal.setColor(QPalette.Base, QColor("#071521"))
        pal.setColor(QPalette.Text, QColor("#f3fafd"))
        pal.setColor(QPalette.Button, QColor("#123049"))
        pal.setColor(QPalette.ButtonText, QColor("#f3fafd"))
        pal.setColor(QPalette.Highlight, QColor("#149fcf"))
        pal.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        self.setPalette(pal)

    def _build_ui(self):
        root = QWidget(objectName="centralRoot")
        self.setCentralWidget(root)
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        # Sidebar
        sidebar = QFrame(objectName="sidebar")
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(18, 22, 18, 18)
        side.setSpacing(20)

        brand = QVBoxLayout()
        brand.setSpacing(4)
        mark = QLabel("RF", objectName="brandMark", alignment=Qt.AlignCenter)
        mark.setFixedSize(40, 40)
        title = QLabel("RomsFun", objectName="brandTitle")
        subtitle = QLabel("Downloader & R36S Optimizer", objectName="brandSubtitle")
        subtitle.setWordWrap(True)
        brand.addWidget(mark, 0, Qt.AlignLeft)
        brand.addSpacing(4)
        brand.addWidget(title)
        brand.addWidget(subtitle)
        side.addLayout(brand)

        self.nav_buttons: dict[str, QPushButton] = {}
        nav = QVBoxLayout()
        nav.setSpacing(6)
        for key, label in [
            ("search", "Buscar"),
            ("console", "Por consola"),
            ("url", "URL directa"),
            ("settings", "Ajustes"),
        ]:
            btn = QPushButton(label, objectName="navBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("active", "false")
            btn.clicked.connect(lambda checked=False, k=key: self._show_tab(k))
            self.nav_buttons[key] = btn
            nav.addWidget(btn)
        side.addLayout(nav)
        side.addStretch(1)
        side.addWidget(QLabel("Tema azul celeste · Núcleo Python", objectName="sidebarFoot"))
        shell.addWidget(sidebar)

        # Main
        main = QWidget()
        main_l = QVBoxLayout(main)
        main_l.setContentsMargins(24, 18, 24, 20)
        main_l.setSpacing(10)

        top = QHBoxLayout()
        titles = QVBoxLayout()
        self.page_title = QLabel(objectName="pageTitle")
        self.page_subtitle = QLabel(objectName="pageSubtitle")
        titles.addWidget(self.page_title)
        titles.addWidget(self.page_subtitle)
        top.addLayout(titles, 1)
        open_btn = QPushButton("Abrir carpeta", objectName="btnGhost")
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.clicked.connect(self._open_output)
        top.addWidget(open_btn, 0, Qt.AlignTop)
        main_l.addLayout(top)

        self.error_banner = QLabel(objectName="errorBanner")
        self.error_banner.setWordWrap(True)
        self.error_banner.hide()
        main_l.addWidget(self.error_banner)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_search_page())
        self.stack.addWidget(self._build_console_page())
        self.stack.addWidget(self._build_url_page())
        self.stack.addWidget(self._build_settings_page())
        main_l.addWidget(self.stack, 1)

        shell.addWidget(main, 1)

    def _panel(self) -> QFrame:
        panel = QFrame(objectName="contentPanel")
        return panel

    def _build_search_page(self) -> QWidget:
        page = self._panel()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(14)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        field = QVBoxLayout()
        field.setSpacing(4)
        field.addWidget(QLabel("Palabra clave", objectName="fieldLabel"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("mario kart, pokemon, zelda...")
        self.search_input.returnPressed.connect(self._run_search)
        field.addWidget(self.search_input)
        toolbar.addLayout(field, 1)

        self.search_btn = QPushButton("Buscar", objectName="btnPrimary")
        self.search_btn.setCursor(Qt.PointingHandCursor)
        self.search_btn.setFixedHeight(38)
        self.search_btn.clicked.connect(self._run_search)
        toolbar.addWidget(self.search_btn, 0, Qt.AlignBottom)

        self.search_dl_btn = QPushButton("Descargar seleccionados", objectName="btnGhost")
        self.search_dl_btn.setCursor(Qt.PointingHandCursor)
        self.search_dl_btn.setFixedHeight(38)
        self.search_dl_btn.clicked.connect(self._download_selected)
        toolbar.addWidget(self.search_dl_btn, 0, Qt.AlignBottom)
        lay.addLayout(toolbar)

        self.search_list_host = self._build_game_list_block("search")
        lay.addWidget(self.search_list_host, 1)
        self.search_progress = self._build_progress_block()
        lay.addWidget(self.search_progress)
        return page

    def _build_console_page(self) -> QWidget:
        page = self._panel()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(14)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        c_field = QVBoxLayout()
        c_field.setSpacing(4)
        c_field.addWidget(QLabel("Consola", objectName="fieldLabel"))
        self.console_combo = QComboBox()
        self.console_combo.setFixedHeight(38)
        for c in _unique_consoles():
            self.console_combo.addItem(f"{c['label']} ({c['folder']})", c)
        c_field.addWidget(self.console_combo)
        toolbar.addLayout(c_field, 2)

        n_field = QVBoxLayout()
        n_field.setSpacing(4)
        n_field.addWidget(QLabel("Nombre del juego", objectName="fieldLabel"))
        self.console_query = QLineEdit()
        self.console_query.setPlaceholderText("Opcional: mario, pokemon, zelda...")
        self.console_query.returnPressed.connect(self._run_console)
        n_field.addWidget(self.console_query)
        toolbar.addLayout(n_field, 2)

        l_field = QVBoxLayout()
        l_field.setSpacing(4)
        l_field.addWidget(QLabel("Límite", objectName="fieldLabel"))
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(1, 200)
        self.limit_spin.setValue(10)
        self.limit_spin.setFixedWidth(90)
        self.limit_spin.setFixedHeight(38)
        self.limit_spin.valueChanged.connect(self._persist_settings)
        l_field.addWidget(self.limit_spin)
        toolbar.addLayout(l_field, 0)

        self.console_btn = QPushButton("Listar", objectName="btnPrimary")
        self.console_btn.setCursor(Qt.PointingHandCursor)
        self.console_btn.setFixedHeight(38)
        self.console_btn.clicked.connect(self._run_console)
        toolbar.addWidget(self.console_btn, 0, Qt.AlignBottom)

        self.console_dl_btn = QPushButton("Descargar lote", objectName="btnGhost")
        self.console_dl_btn.setCursor(Qt.PointingHandCursor)
        self.console_dl_btn.setFixedHeight(38)
        self.console_dl_btn.clicked.connect(self._download_selected)
        toolbar.addWidget(self.console_dl_btn, 0, Qt.AlignBottom)

        lay.addLayout(toolbar)
        self.console_list_host = self._build_game_list_block("console")
        lay.addWidget(self.console_list_host, 1)
        self.console_progress = self._build_progress_block()
        lay.addWidget(self.console_progress)
        return page

    def _build_url_page(self) -> QWidget:
        page = self._panel()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        toolbar = QHBoxLayout()
        field = QVBoxLayout()
        field.addWidget(QLabel("URL de RomsFun", objectName="fieldLabel"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://romsfun.com/roms/...")
        field.addWidget(self.url_input)
        toolbar.addLayout(field, 1)

        self.url_btn = QPushButton("Descargar", objectName="btnPrimary")
        self.url_btn.setCursor(Qt.PointingHandCursor)
        self.url_btn.clicked.connect(self._download_url)
        toolbar.addWidget(self.url_btn, 0, Qt.AlignBottom)
        lay.addLayout(toolbar)

        self.url_progress = self._build_progress_block()
        lay.addWidget(self.url_progress)
        lay.addStretch(1)
        return page

    def _build_settings_page(self) -> QWidget:
        page = self._panel()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(14)

        toolbar = QHBoxLayout()
        field = QVBoxLayout()
        field.addWidget(QLabel("Carpeta de descargas", objectName="fieldLabel"))
        self.output_input = QLineEdit()
        self.output_input.setReadOnly(True)
        field.addWidget(self.output_input)
        toolbar.addLayout(field, 1)
        pick = QPushButton("Elegir...", objectName="btnPrimary")
        pick.setCursor(Qt.PointingHandCursor)
        pick.clicked.connect(self._pick_output)
        toolbar.addWidget(pick, 0, Qt.AlignBottom)
        lay.addLayout(toolbar)

        self.chk_unzip = QCheckBox("Extraer archivos comprimidos automáticamente")
        self.chk_single = QCheckBox("Solo la mejor versión (ES > EN)")
        self.chk_tags = QCheckBox("Limpiar etiquetas de región () []")
        for chk in (self.chk_unzip, self.chk_single, self.chk_tags):
            chk.stateChanged.connect(self._persist_settings)
            lay.addWidget(chk)
        lay.addStretch(1)
        return page

    def _build_game_list_block(self, key: str) -> QWidget:
        host = QWidget()
        lay = QVBoxLayout(host)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        toolbar = QFrame(objectName="listToolbar")
        toolbar.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        bar = QHBoxLayout(toolbar)
        bar.setContentsMargins(0, 0, 0, 0)
        bar.setSpacing(10)

        toggle = QPushButton("Seleccionar todo", objectName="btnGhost")
        toggle.setCursor(Qt.PointingHandCursor)
        toggle.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        toggle.clicked.connect(lambda: self._toggle_all(key))

        badge = QLabel("0 juegos", objectName="badge")
        badge.setAlignment(Qt.AlignCenter)
        badge.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        badge.setFixedHeight(28)
        badge.adjustSize()

        bar.addWidget(toggle, 0, Qt.AlignVCenter)
        bar.addWidget(badge, 0, Qt.AlignVCenter)
        bar.addStretch(1)
        lay.addWidget(toolbar, 0)

        results = QStackedWidget()
        empty = QLabel("Sin resultados todavía. Busca o lista una consola.", objectName="emptyHint")
        empty.setAlignment(Qt.AlignCenter)
        empty.setWordWrap(True)

        lst = QListWidget()
        lst.setSelectionMode(QAbstractItemView.NoSelection)
        lst.setSpacing(2)
        lst.setUniformItemSizes(False)

        results.addWidget(empty)
        results.addWidget(lst)
        results.setCurrentIndex(0)
        lay.addWidget(results, 1)

        host.toggle_btn = toggle
        host.badge = badge
        host.empty = empty
        host.list = lst
        host.results = results
        host.key = key
        return host

    def _build_progress_block(self) -> QFrame:
        box = QFrame(objectName="progressBox")
        box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        lay = QVBoxLayout(box)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        head = QHBoxLayout()
        msg = QLabel("Listo", objectName="progressMsg")
        msg.setWordWrap(True)
        count = QLabel("", objectName="progressCount")
        head.addWidget(msg, 1)
        head.addWidget(count, 0, Qt.AlignRight | Qt.AlignVCenter)
        lay.addLayout(head)

        batch_bar = QProgressBar()
        batch_bar.setRange(0, 100)
        batch_bar.setValue(0)
        batch_bar.setTextVisible(False)
        batch_bar.setFixedHeight(12)
        lay.addWidget(batch_bar)

        file_label = QLabel("")
        file_label.hide()
        lay.addWidget(file_label)
        file_bar = QProgressBar()
        file_bar.setRange(0, 100)
        file_bar.setValue(0)
        file_bar.setTextVisible(False)
        file_bar.setFixedHeight(12)
        file_bar.hide()
        lay.addWidget(file_bar)

        cancel = QPushButton("Cancelar", objectName="btnDanger")
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        cancel.hide()
        cancel.clicked.connect(self._cancel_download)
        lay.addWidget(cancel, 0, Qt.AlignLeft)

        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(["Juego", "ROM", "Tamaño", "Estado"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.NoSelection)
        table.setMaximumHeight(160)
        table.hide()
        lay.addWidget(table)

        box.msg = msg
        box.count = count
        box.batch_bar = batch_bar
        box.file_label = file_label
        box.file_bar = file_bar
        box.cancel = cancel
        box.table = table
        return box

    # --- navigation / settings ---

    def _show_tab(self, key: str):
        idx = {"search": 0, "console": 1, "url": 2, "settings": 3}[key]
        self.stack.setCurrentIndex(idx)
        title, subtitle = TABS[key]
        self.page_title.setText(title)
        self.page_subtitle.setText(subtitle)
        for k, btn in self.nav_buttons.items():
            btn.setProperty("active", "true" if k == key else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _load_settings(self):
        self.output_input.setText(self.settings.value("outputDir", DEFAULT_OUTPUT))
        self.chk_unzip.setChecked(self.settings.value("unzip", True, type=bool))
        self.chk_single.setChecked(self.settings.value("singleVersion", True, type=bool))
        self.chk_tags.setChecked(self.settings.value("cleanTags", False, type=bool))
        self.limit_spin.setValue(int(self.settings.value("limit", 10)))

    def _persist_settings(self, *_args):
        self.settings.setValue("outputDir", self.output_input.text())
        self.settings.setValue("unzip", self.chk_unzip.isChecked())
        self.settings.setValue("singleVersion", self.chk_single.isChecked())
        self.settings.setValue("cleanTags", self.chk_tags.isChecked())
        self.settings.setValue("limit", self.limit_spin.value())

    def _pick_output(self):
        path = QFileDialog.getExistingDirectory(self, "Carpeta de descargas", self.output_input.text())
        if path:
            self.output_input.setText(path)
            self._persist_settings()

    def _open_output(self):
        path = self.output_input.text() or DEFAULT_OUTPUT
        os.makedirs(path, exist_ok=True)
        subprocess.Popen(["xdg-open", path])

    def _set_error(self, message: str | None):
        if message:
            self.error_banner.setText(message)
            self.error_banner.show()
        else:
            self.error_banner.hide()

    def _set_loading(self, loading: bool):
        self._loading = loading
        self.search_btn.setEnabled(not loading and not self._busy)
        self.console_btn.setEnabled(not loading and not self._busy)
        if loading:
            self.search_btn.setText("Buscando...")
            self.console_btn.setText("Buscando...")
        else:
            self.search_btn.setText("Buscar")
            name = self.console_query.text().strip()
            self.console_btn.setText("Buscar" if name else "Listar")

    # --- search / console ---

    def _run_search(self):
        query = self.search_input.text().strip()
        if not query or self._loading or self._busy:
            return
        self._set_error(None)
        self._set_loading(True)

        def work():
            return search_roms(query)

        self._start_search_worker(work, select_all=False)

    def _run_console(self):
        if self._loading or self._busy:
            return
        self._set_error(None)
        self._set_loading(True)
        meta = self.console_combo.currentData()
        slug = meta["slug"]
        name = self.console_query.text().strip()
        limit = self.limit_spin.value()

        def work():
            if name:
                results = search_roms(name)
                found = [
                    g
                    for g in results
                    if g.get("console_slug") == slug
                    or g.get("console") == meta["folder"]
                    or g.get("console") == meta["label"]
                ][:limit]
                if not found:
                    listed = list_console_roms(
                        slug, max_pages=pages_for_limit(max(limit * 3, 40)), target_count=max(limit * 3, 40)
                    )
                    needle = name.lower()
                    found = [g for g in listed if needle in g["title"].lower()][:limit]
                return found
            return list_console_roms(slug, max_pages=pages_for_limit(limit), target_count=limit)[:limit]

        self._start_search_worker(work, select_all=True)

    def _start_search_worker(self, fn, select_all: bool):
        if self._search_worker and self._search_worker.isRunning():
            return
        worker = SearchWorker(fn, self)
        self._search_worker = worker

        def ok(games):
            self._set_loading(False)
            self.games = games
            self._populate_lists(select_all=select_all)
            self._clear_progress_results()

        def fail(msg):
            self._set_loading(False)
            self._set_error(msg)

        worker.finished_ok.connect(ok)
        worker.failed.connect(fail)
        worker.start()

    def _active_list_host(self) -> QWidget:
        return self.search_list_host if self.stack.currentIndex() == 0 else self.console_list_host

    def _populate_lists(self, select_all: bool):
        for host in (self.search_list_host, self.console_list_host):
            lst: QListWidget = host.list
            lst.clear()
            host.badge.setText(f"{len(self.games)} juegos")
            host.badge.adjustSize()
            host.badge.setFixedHeight(28)

            if not self.games:
                host.results.setCurrentIndex(0)
                host.toggle_btn.setText("Seleccionar todo")
                continue

            host.results.setCurrentIndex(1)
            for game in self.games:
                item = QListWidgetItem()
                row = QWidget()
                row_l = QHBoxLayout(row)
                row_l.setContentsMargins(10, 8, 10, 8)
                row_l.setSpacing(12)

                chk = QCheckBox()
                chk.setChecked(select_all)
                chk.setProperty("game_url", game["url"])
                chk.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

                meta = QVBoxLayout()
                meta.setSpacing(2)
                title = QLabel(game["title"])
                title.setStyleSheet("font-weight: 600; font-size: 13px;")
                cons = QLabel(game["console"])
                cons.setStyleSheet("color: #8fd6ef; font-size: 11px;")
                meta.addWidget(title)
                meta.addWidget(cons)

                badge = QLabel(game["console"], objectName="rowBadge")
                badge.setAlignment(Qt.AlignCenter)
                badge.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                badge.setFixedHeight(22)

                row_l.addWidget(chk, 0, Qt.AlignVCenter)
                row_l.addLayout(meta, 1)
                row_l.addWidget(badge, 0, Qt.AlignVCenter)
                row.setMinimumHeight(48)
                item.setSizeHint(QSize(row.sizeHint().width(), 52))
                lst.addItem(item)
                lst.setItemWidget(item, row)
            host.toggle_btn.setText("Deseleccionar todo" if select_all else "Seleccionar todo")

    def _toggle_all(self, key: str):
        host = self.search_list_host if key == "search" else self.console_list_host
        lst: QListWidget = host.list
        if lst.count() == 0:
            return
        # Detect if all checked
        all_checked = True
        for i in range(lst.count()):
            w = lst.itemWidget(lst.item(i))
            chk = w.findChild(QCheckBox)
            if chk and not chk.isChecked():
                all_checked = False
                break
        new_val = not all_checked
        for i in range(lst.count()):
            w = lst.itemWidget(lst.item(i))
            chk = w.findChild(QCheckBox)
            if chk:
                chk.setChecked(new_val)
        host.toggle_btn.setText("Deseleccionar todo" if new_val else "Seleccionar todo")

    def _selected_games(self) -> list[dict]:
        host = self._active_list_host()
        lst: QListWidget = host.list
        selected_urls = set()
        for i in range(lst.count()):
            w = lst.itemWidget(lst.item(i))
            chk = w.findChild(QCheckBox)
            if chk and chk.isChecked():
                selected_urls.add(chk.property("game_url"))
        return [g for g in self.games if g["url"] in selected_urls]

    # --- downloads ---

    def _current_progress_box(self) -> QFrame:
        idx = self.stack.currentIndex()
        if idx == 0:
            return self.search_progress
        if idx == 1:
            return self.console_progress
        return self.url_progress

    def _clear_progress_results(self):
        for box in (self.search_progress, self.console_progress, self.url_progress):
            box.table.setRowCount(0)
            box.table.hide()
            box.msg.setText("Listo")
            box.count.setText("")
            box.batch_bar.setValue(0)
            box.file_bar.hide()
            box.file_label.hide()
            box.cancel.hide()

    def _download_selected(self):
        items = self._selected_games()
        if not items:
            self._set_error("Selecciona al menos un juego")
            return
        self._start_download(items)

    def _download_url(self):
        url = self.url_input.text().strip()
        if not url:
            return
        console_name = extract_console_from_url(url) or "ROM"
        title = url.split("/")[-1].replace(".html", "").replace("-", " ").title()
        self._start_download([{"title": title, "console": console_name, "url": url}])

    def _start_download(self, items: list[dict]):
        if self._busy:
            return
        self._set_error(None)
        self._busy = True
        self._set_loading(False)
        box = self._current_progress_box()
        box.msg.setText("Iniciando...")
        box.count.setText(f"0/{len(items)}")
        box.batch_bar.setValue(0)
        box.cancel.show()
        box.table.setRowCount(0)
        box.table.hide()

        for btn in (self.search_dl_btn, self.console_dl_btn, self.url_btn, self.search_btn, self.console_btn):
            btn.setEnabled(False)

        worker = DownloadWorker(
            items=items,
            output=self.output_input.text() or DEFAULT_OUTPUT,
            unzip=self.chk_unzip.isChecked(),
            single_version=self.chk_single.isChecked(),
            clean_tags=self.chk_tags.isChecked(),
            parent=self,
        )
        self._download_worker = worker
        worker.progress.connect(self._on_download_progress)
        worker.finished_ok.connect(self._on_download_done)
        worker.failed.connect(self._on_download_fail)
        worker.start()

    def _cancel_download(self):
        if self._download_worker:
            self._download_worker.request_cancel()

    def _on_download_progress(self, event: dict):
        box = self._current_progress_box()
        etype = event.get("type")
        if etype == "batch":
            current = event.get("current") or 0
            total = event.get("total") or 0
            box.msg.setText(event.get("message") or f"Procesando ({current}/{total})")
            box.count.setText(f"{current}/{total}" if total else "")
            if total:
                box.batch_bar.setValue(int(current * 100 / total))
        elif etype == "resolving":
            box.msg.setText(event.get("message") or "Resolviendo...")
            box.file_label.setText(event.get("filename") or "")
            box.file_label.show()
            box.file_bar.show()
            box.file_bar.setValue(0)
        elif etype == "file":
            total = event.get("total") or 0
            downloaded = event.get("downloaded") or 0
            box.file_label.setText(event.get("filename") or "")
            box.file_label.show()
            box.file_bar.show()
            if total:
                box.file_bar.setValue(int(downloaded * 100 / total))
            else:
                box.file_bar.setRange(0, 0)
        elif etype == "error":
            self._set_error(event.get("message") or "Error en la descarga")

    def _on_download_done(self, result: dict):
        self._busy = False
        box = self._current_progress_box()
        box.cancel.hide()
        box.file_bar.setRange(0, 100)
        box.file_bar.hide()
        box.file_label.hide()
        box.batch_bar.setValue(100)
        box.msg.setText("Descarga finalizada")
        items = result.get("items") or []
        self._fill_results_table(box, items)
        for btn in (self.search_dl_btn, self.console_dl_btn, self.url_btn, self.search_btn, self.console_btn):
            btn.setEnabled(True)
        self._set_loading(False)

    def _on_download_fail(self, msg: str):
        self._busy = False
        box = self._current_progress_box()
        box.cancel.hide()
        self._set_error(msg)
        for btn in (self.search_dl_btn, self.console_dl_btn, self.url_btn, self.search_btn, self.console_btn):
            btn.setEnabled(True)
        self._set_loading(False)

    def _fill_results_table(self, box: QFrame, items: list):
        table = box.table
        rows = []
        for item in items:
            status = item.get("status", "")
            if status == "success":
                label, color = "Éxito", "#2ecc8a"
            elif status == "already_exists":
                label, color = "Ya existía", "#f0b429"
            else:
                label, color = "Error", "#ef6b6b"
            for rom in item.get("roms") or []:
                if isinstance(rom, dict):
                    name, size = rom.get("name", ""), rom.get("size", "")
                else:
                    name, size = rom[0], rom[1]
                rows.append((f"[{item.get('console')}] {item.get('title')}", name, size, label, color))

        table.setRowCount(len(rows))
        for r, (game, rom, size, label, color) in enumerate(rows):
            table.setItem(r, 0, QTableWidgetItem(game))
            table.setItem(r, 1, QTableWidgetItem(rom))
            table.setItem(r, 2, QTableWidgetItem(size))
            st = QTableWidgetItem(label)
            st.setForeground(QColor(color))
            table.setItem(r, 3, st)
        table.setVisible(bool(rows))
