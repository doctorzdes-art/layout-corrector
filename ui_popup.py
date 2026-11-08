"""
TextPopup window for LayoutCorrector v2.
Displays translated text near the cursor with a sleek modern design,
direction chip, strikethrough original text, copy button, and progress timer bar.
"""

from pathlib import Path
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QGraphicsDropShadowEffect, QApplication, QFrame
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, pyqtProperty
from PyQt6.QtGui import QColor, QCursor, QFont, QPixmap
from config import get_resource_path
import ui_common

class TextPopup(QWidget):
    def __init__(self, text: str, original_text: str = "", direction: str = "EN → UA", duration: int = 5, parent=None):
        super().__init__(parent)
        self.text = text
        self.original_text = original_text
        self.direction = direction
        self.duration_sec = max(1, duration)
        self.fade_anim = None
        self.is_paused = False

        # Configure window attributes
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.init_ui()
        self.position_near_cursor()

        # Smooth countdown timer: updates progress bar every 30ms
        self.total_ticks = int(self.duration_sec * 1000 / 30)
        self.current_tick = self.total_ticks

        self.progress_timer = QTimer(self)
        self.progress_timer.setInterval(30)
        self.progress_timer.timeout.connect(self._on_timer_tick)
        self.progress_timer.start()

    def init_ui(self):
        base_dir = Path(get_resource_path("icons")).parent

        # Outer layout with 10px margin to accommodate drop shadow
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(10, 10, 10, 10)
        outer_layout.setSpacing(0)

        # PopupContainer card (380px fixed width)
        self.container = QFrame(self)
        self.container.setObjectName("PopupContainer")
        self.container.setFixedWidth(380)

        # Drop shadow: blur 32, offset (0, 12), rgba(0, 0, 0, 140)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32)
        shadow.setColor(QColor(0, 0, 0, 140))
        shadow.setOffset(0, 12)
        self.container.setGraphicsEffect(shadow)

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(20, 16, 16, 16)
        container_layout.setSpacing(12)

        # ---------------- Row 1: Header (Logo + Title + Direction + Close) ----------------
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        # Logo
        logo_lbl = QLabel(self.container)
        logo_path = get_resource_path("logo.png")
        logo_pm = QPixmap(logo_path)
        if not logo_pm.isNull():
            logo_lbl.setPixmap(logo_pm.scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        logo_lbl.setFixedSize(22, 22)
        header_layout.addWidget(logo_lbl)

        # Title
        title_lbl = QLabel("Розкладку виправлено", self.container)
        title_lbl.setObjectName("PopupTitle")
        title_lbl.setFont(ui_common.text_font(13, QFont.Weight.DemiBold))
        header_layout.addWidget(title_lbl)

        header_layout.addStretch()

        # Direction Chip
        dir_lbl = QLabel(self.direction, self.container)
        dir_lbl.setObjectName("PopupDir")
        dir_lbl.setFont(ui_common.display_font(12, QFont.Weight.DemiBold))
        dir_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(dir_lbl)

        # Close Button
        btn_close = QPushButton(self.container)
        btn_close.setObjectName("PopupClose")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        close_icon_path = base_dir / "icons" / "close.svg"
        if close_icon_path.exists():
            btn_close.setIcon(ui_common.svg_icon(close_icon_path, "#A4A4B2", 14))
        else:
            btn_close.setText("✕")
        btn_close.clicked.connect(self.close)
        header_layout.addWidget(btn_close)

        container_layout.addLayout(header_layout)

        # ---------------- Row 2: Original Text (Strikethrough) ----------------
        if self.original_text and self.original_text != self.text:
            orig_lbl = QLabel(self.original_text, self.container)
            orig_lbl.setObjectName("PopupOriginal")
            orig_lbl.setWordWrap(True)
            orig_font = ui_common.text_font(13, QFont.Weight.Normal)
            orig_font.setStrikeOut(True)
            orig_lbl.setFont(orig_font)
            container_layout.addWidget(orig_lbl)

        # ---------------- Row 3: Translated Text ----------------
        self.text_label = QLabel(self.text, self.container)
        self.text_label.setObjectName("PopupText")
        self.text_label.setWordWrap(True)
        self.text_label.setFont(ui_common.display_font(22, QFont.Weight.DemiBold))
        self.text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        container_layout.addWidget(self.text_label)

        # ---------------- Row 4: Full-width Copy Button ----------------
        self.btn_copy = QPushButton("Копіювати", self.container)
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.setProperty("variant", "primary")
        self.btn_copy.setProperty("size", "popup")
        copy_icon_path = base_dir / "icons" / "copy.svg"
        if copy_icon_path.exists():
            self.btn_copy.setIcon(ui_common.svg_icon(copy_icon_path, "#03213F", 16))
        self.btn_copy.clicked.connect(self.copy_to_clipboard)
        container_layout.addWidget(self.btn_copy)

        # ---------------- Row 5: Timer Progress Bar ----------------
        self.timer_bar = QProgressBar(self.container)
        self.timer_bar.setObjectName("PopupTimer")
        self.timer_bar.setTextVisible(False)
        self.timer_bar.setRange(0, 1000)
        self.timer_bar.setValue(1000)
        container_layout.addWidget(self.timer_bar)

        outer_layout.addWidget(self.container)

    def _on_timer_tick(self):
        if self.is_paused:
            return

        self.current_tick -= 1
        val = int(max(0, (self.current_tick / self.total_ticks) * 1000))
        self.timer_bar.setValue(val)

        if self.current_tick <= 0:
            self.progress_timer.stop()
            self.fade_out()

    def enterEvent(self, event):
        """Pause timer when hovering over popup."""
        self.is_paused = True
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Resume timer when mouse leaves popup."""
        self.is_paused = False
        super().leaveEvent(event)

    def copy_to_clipboard(self):
        cb = QApplication.clipboard()
        if cb:
            cb.setText(self.text)
        self.btn_copy.setText("Скопійовано ✓")
        QTimer.singleShot(1200, lambda: self.btn_copy.setText("Копіювати"))

    def position_near_cursor(self):
        cursor_pos = QCursor.pos()
        screen = QApplication.screenAt(cursor_pos)
        if not screen:
            screen = QApplication.primaryScreen()

        screen_geom = screen.availableGeometry()
        self.adjustSize()

        w = self.width()
        h = self.height()

        x = cursor_pos.x() + 15
        y = cursor_pos.y() + 15

        # Check right boundary
        if x + w > screen_geom.right():
            x = cursor_pos.x() - w - 10

        # Check bottom boundary
        if y + h > screen_geom.bottom():
            y = cursor_pos.y() - h - 10

        # Ensure within screen bounds
        x = max(screen_geom.left() + 10, min(x, screen_geom.right() - w - 10))
        y = max(screen_geom.top() + 10, min(y, screen_geom.bottom() - h - 10))

        self.move(x, y)

    def _get_opacity(self):
        return self.windowOpacity()

    def _set_opacity(self, opacity):
        self.setWindowOpacity(opacity)

    opacity = pyqtProperty(float, _get_opacity, _set_opacity)

    def fade_out(self):
        if self.fade_anim and self.fade_anim.state() == QPropertyAnimation.State.Running:
            return

        self.fade_anim = QPropertyAnimation(self, b"opacity")
        self.fade_anim.setDuration(400)
        self.fade_anim.setStartValue(1.0)
        self.fade_anim.setEndValue(0.0)
        self.fade_anim.finished.connect(self.close)
        self.fade_anim.start()
