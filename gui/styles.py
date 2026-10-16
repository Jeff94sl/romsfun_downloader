"""Tema azul celeste — mismos colores que la UI Electron anterior."""

APP_QSS = """
QWidget {
    font-family: "Outfit", "Segoe UI", "Ubuntu", sans-serif;
    font-size: 14px;
    color: #f3fafd;
    background: transparent;
}

QMainWindow, #centralRoot {
    background-color: #0b1f33;
}

#sidebar {
    background-color: #123049;
    border-right: 1px solid rgba(143, 214, 239, 40);
    min-width: 240px;
    max-width: 240px;
}

#brandMark {
    background-color: #5bc4e8;
    color: #071521;
    font-family: "Sora", "Segoe UI", sans-serif;
    font-weight: 700;
    font-size: 15px;
    border-radius: 12px;
    min-width: 40px;
    max-width: 40px;
    min-height: 40px;
    max-height: 40px;
}

#brandTitle {
    font-family: "Sora", "Segoe UI", sans-serif;
    font-size: 20px;
    font-weight: 700;
    color: #f3fafd;
    padding: 0;
    margin: 0;
}

#brandSubtitle, #sidebarFoot, #pageSubtitle {
    color: #c8ebf7;
    font-size: 12px;
}

#sidebarFoot {
    color: rgba(215, 234, 245, 140);
    font-size: 11px;
}

QPushButton#navBtn {
    text-align: left;
    padding: 10px 12px;
    border: none;
    border-radius: 10px;
    background: transparent;
    color: #d7eaf5;
}

QPushButton#navBtn:hover {
    background-color: rgba(91, 196, 232, 30);
}

QPushButton#navBtn[active="true"] {
    background-color: rgba(46, 179, 223, 55);
    border-left: 3px solid #5bc4e8;
    color: white;
    font-weight: 600;
}

#contentPanel {
    background-color: rgba(26, 64, 96, 110);
    border: 1px solid rgba(143, 214, 239, 40);
    border-radius: 16px;
}

QLabel#pageTitle {
    font-family: "Sora", "Segoe UI", sans-serif;
    font-size: 22px;
    font-weight: 700;
    color: #f3fafd;
}

QLabel#fieldLabel {
    color: #c8ebf7;
    font-size: 12px;
}

QLineEdit, QComboBox, QSpinBox {
    background-color: rgba(7, 21, 33, 140);
    border: 1px solid rgba(143, 214, 239, 70);
    border-radius: 8px;
    padding: 9px 12px;
    min-height: 20px;
    color: #f3fafd;
    selection-background-color: #149fcf;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #5bc4e8;
}

QComboBox::drop-down {
    border: none;
    width: 28px;
}

QComboBox QAbstractItemView {
    background-color: #123049;
    border: 1px solid #5bc4e8;
    selection-background-color: #149fcf;
    color: #f3fafd;
}

QPushButton#btnPrimary, QPushButton#btnGhost, QPushButton#btnDanger {
    border-radius: 8px;
    padding: 9px 14px;
    min-height: 18px;
    font-weight: 600;
}

QPushButton#btnPrimary {
    background-color: #2eb3df;
    color: #071521;
    border: none;
}

QPushButton#btnPrimary:hover {
    background-color: #5bc4e8;
}

QPushButton#btnPrimary:disabled {
    background-color: rgba(46, 179, 223, 80);
    color: rgba(7, 21, 33, 120);
}

QPushButton#btnGhost {
    background-color: rgba(91, 196, 232, 28);
    color: #f3fafd;
    border: 1px solid rgba(143, 214, 239, 55);
}

QPushButton#btnGhost:hover {
    background-color: rgba(91, 196, 232, 48);
}

QPushButton#btnGhost:disabled {
    color: rgba(243, 250, 253, 100);
}

QPushButton#btnDanger {
    background-color: #ef6b6b;
    color: white;
    border: none;
}

#errorBanner {
    background-color: rgba(239, 107, 107, 40);
    border: 1px solid rgba(239, 107, 107, 90);
    border-radius: 8px;
    color: #ffd5d5;
    padding: 10px 12px;
}

#listToolbar {
    background: transparent;
    max-height: 40px;
}

#progressBox {
    background-color: rgba(7, 21, 33, 120);
    border: 1px solid rgba(143, 214, 239, 50);
    border-radius: 12px;
    min-height: 72px;
}

QProgressBar {
    border: 1px solid rgba(143, 214, 239, 35);
    border-radius: 6px;
    background-color: rgba(7, 21, 33, 160);
    min-height: 12px;
    max-height: 12px;
    text-align: center;
    color: transparent;
}

QProgressBar::chunk {
    border-radius: 5px;
    background-color: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #149fcf,
        stop:1 #8fd6ef
    );
}

QListWidget {
    background-color: transparent;
    border: none;
    outline: none;
    padding: 2px;
}

QListWidget::item {
    background-color: rgba(7, 21, 33, 80);
    border: 1px solid transparent;
    border-radius: 10px;
    padding: 4px;
    margin-bottom: 6px;
}

QListWidget::item:hover {
    border: 1px solid rgba(91, 196, 232, 70);
}

QListWidget::item:selected {
    background-color: rgba(46, 179, 223, 40);
    border: 1px solid rgba(91, 196, 232, 140);
}

QCheckBox {
    color: #f3fafd;
    spacing: 10px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #5bc4e8;
    background: rgba(7, 21, 33, 120);
}

QCheckBox::indicator:checked {
    background-color: #2eb3df;
    border-color: #2eb3df;
}

QTableWidget {
    background-color: transparent;
    border: none;
    gridline-color: rgba(143, 214, 239, 30);
    color: #f3fafd;
}

QHeaderView::section {
    background-color: transparent;
    color: #c8ebf7;
    border: none;
    border-bottom: 1px solid rgba(143, 214, 239, 30);
    padding: 8px;
    font-weight: 600;
}

QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: rgba(91, 196, 232, 90);
    border-radius: 4px;
    min-height: 30px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QLabel#badge {
    background-color: rgba(91, 196, 232, 40);
    color: #c8ebf7;
    border-radius: 11px;
    padding: 4px 12px;
    font-size: 12px;
    font-weight: 600;
    min-height: 14px;
    max-height: 22px;
}

QLabel#rowBadge {
    background-color: rgba(91, 196, 232, 40);
    color: #c8ebf7;
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 600;
    max-height: 20px;
}

QLabel#emptyHint {
    color: rgba(232, 247, 252, 150);
    padding: 28px 12px;
    font-size: 14px;
}

QLabel#progressMsg {
    font-weight: 600;
    font-size: 13px;
}

QLabel#progressCount {
    color: #8fd6ef;
    font-size: 12px;
}
"""
