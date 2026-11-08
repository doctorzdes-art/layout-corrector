"""
Custom dialogs for LayoutCorrector v2.
Includes UpdateDialog styled to match Material 3 Expressive theme.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPixmap
from config import get_resource_path, APP_VERSION
import ui_common

class UpdateDialog(QDialog):
    def __init__(self, new_version: str, current_version: str = APP_VERSION, parent=None):
        super().__init__(parent)
        self.new_version = new_version
        self.current_version = current_version

        self.setObjectName("UpdateDialog")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.init_ui()

    def init_ui(self):
        # Outer layout with 10px margins for drop shadow
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(10, 10, 10, 10)
        outer_layout.setSpacing(0)

        # Dialog Card (400px width, bg #202027, radius 28px)
        card = QFrame(self)
        card.setObjectName("DialogCard")
        card.setFixedWidth(400)

        # Drop shadow: blur 40, offset (0, 16), rgba(0, 0, 0, 150)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 16)
        card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(16)

        # Logo 64x64
        logo_lbl = QLabel(card)
        logo_pm = QPixmap(get_resource_path("logo.png"))
        if not logo_pm.isNull():
            logo_lbl.setPixmap(logo_pm.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        logo_lbl.setFixedSize(64, 64)
        card_layout.addWidget(logo_lbl)

        # Text Column (gap 6px)
        text_col = QVBoxLayout()
        text_col.setSpacing(6)
        text_col.setContentsMargins(0, 0, 0, 0)

        lbl_title = QLabel(f"Вийшла версія {self.new_version}", card)
        lbl_title.setObjectName("DialogTitle")
        lbl_title.setFont(ui_common.display_font(24, QFont.Weight.Bold))
        text_col.addWidget(lbl_title)

        lbl_body = QLabel(
            f"У вас {self.current_version}. Завантажити оновлення зараз? Налаштування та ваші розкладки збережуться.",
            card
        )
        lbl_body.setObjectName("DialogText")
        lbl_body.setFont(ui_common.text_font(14, QFont.Weight.Normal))
        lbl_body.setWordWrap(True)
        text_col.addWidget(lbl_body)

        card_layout.addLayout(text_col)

        # Buttons Row (Right aligned, gap 8px)
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(8)
        btn_row.addStretch()

        btn_later = QPushButton("Пізніше", card)
        btn_later.setProperty("variant", "text")
        btn_later.setProperty("size", "popup")
        btn_later.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_later.clicked.connect(self.reject)
        btn_row.addWidget(btn_later)

        btn_download = QPushButton("Завантажити", card)
        btn_download.setProperty("variant", "primary")
        btn_download.setProperty("size", "popup")
        btn_download.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_download.clicked.connect(self.accept)
        btn_row.addWidget(btn_download)

        card_layout.addLayout(btn_row)
        outer_layout.addWidget(card)
