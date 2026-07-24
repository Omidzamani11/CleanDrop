from __future__ import annotations

STYLESHEET = """
QWidget {
    background: #0b1220;
    color: #e8eef8;
    font-family: "Segoe UI", "Vazirmatn", "Tahoma";
    font-size: 14px;
}
QMainWindow {
    background: #0b1220;
}
QLabel#brand {
    color: #5eead4;
    font-size: 23px;
    font-weight: 750;
}
QLabel#heroTitle {
    color: #f8fafc;
    font-size: 34px;
    font-weight: 750;
}
QLabel#heroSubtitle, QLabel#pageDescription, QLabel#muted {
    color: #94a3b8;
}
QLabel#pageTitle {
    color: #f8fafc;
    font-size: 27px;
    font-weight: 720;
}
QLabel#pageDescription {
    font-size: 15px;
}
QLabel#privacyBadge {
    background: #10352f;
    color: #99f6e4;
    border: 1px solid #176354;
    border-radius: 13px;
    padding: 7px 12px;
}
QLabel#warningBadge {
    background: #3a2d16;
    border: 1px solid #a77422;
    border-radius: 10px;
    color: #ffd88a;
    padding: 10px 14px;
}
QLabel#dropTitle, QLabel#fileName, QLabel#sectionTitle {
    color: #f8fafc;
    font-size: 17px;
    font-weight: 650;
}
QFrame#card {
    background: #111a29;
    border: 1px solid #243249;
    border-radius: 14px;
}
QFrame#dropPanel {
    background: #101927;
    border: 2px dashed #35506b;
    border-radius: 18px;
}
QListWidget, QLineEdit, QComboBox, QScrollArea {
    background: #0d1624;
    color: #e2e8f0;
    border: 1px solid #2a3a52;
    border-radius: 10px;
    padding: 7px;
    selection-background-color: #164e63;
    selection-color: #ecfeff;
}
QListWidget#dropList {
    background: #0c1522;
    border: 1px solid #263750;
    padding: 10px;
}
QListWidget::item {
    background: #121f31;
    border: 1px solid #253852;
    border-radius: 9px;
    padding: 10px;
    margin: 3px;
}
QListWidget::item:selected {
    background: #153f4b;
    border-color: #2dd4bf;
}
QPushButton {
    min-height: 38px;
    border-radius: 9px;
    padding: 0 16px;
    font-weight: 620;
}
QPushButton#primaryButton {
    background: #14b8a6;
    color: #032a26;
    border: 1px solid #2dd4bf;
}
QPushButton#primaryButton:hover {
    background: #2dd4bf;
}
QPushButton#secondaryButton {
    background: #1d3347;
    color: #dbeafe;
    border: 1px solid #355573;
}
QPushButton#secondaryButton:hover {
    background: #284762;
}
QPushButton#ghostButton {
    background: transparent;
    color: #b8c5d6;
    border: 1px solid #314158;
}
QPushButton#ghostButton:hover {
    background: #172235;
    color: #f8fafc;
}
QPushButton:disabled {
    background: #16202d;
    color: #607086;
    border-color: #243141;
}
QProgressBar {
    height: 20px;
    background: #0c1420;
    border: 1px solid #2b3d56;
    border-radius: 10px;
    text-align: center;
    color: #e2e8f0;
}
QProgressBar::chunk {
    background: #14b8a6;
    border-radius: 9px;
}
QComboBox::drop-down {
    border: none;
    width: 26px;
}
QScrollBar:vertical {
    background: #0d1624;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #35465c;
    border-radius: 5px;
    min-height: 28px;
}
QToolTip {
    background: #172235;
    color: #f8fafc;
    border: 1px solid #3a4d66;
    padding: 6px;
}
"""
