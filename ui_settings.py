"""
Settings window for LayoutCorrector v2.
Material 3 Expressive design with Navigation Rail, Hotkeys & Options page,
exact unit-based symmetric Layout Editor, and Feedback page with Snackbar.
"""

from pathlib import Path
import logging
import webbrowser
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QFrame, QCheckBox, QToolButton,
    QButtonGroup, QGraphicsOpacityEffect, QApplication, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QRectF, QUrl
from PyQt6.QtGui import (
    QFont, QColor, QIcon, QPixmap, QPainter, QDesktopServices
)

from config import (
    DEFAULT_EN_TO_UA, DEFAULT_EN_TO_UA_SHIFT, VK_TO_NAME,
    get_resource_path, APP_VERSION, FEEDBACK_URL, set_windows_autorun
)
import ui_common

# Visual keyboard row keys
EN_ROWS = [
    ["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "="],
    ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p", "[", "]", "\\"],
    ["a", "s", "d", "f", "g", "h", "j", "k", "l", ";", "'"],
    ["z", "x", "c", "v", "b", "n", "m", ",", ".", "/"]
]

EN_SHIFT_ROWS = [
    ["~", "!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "_", "+"],
    ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "{", "}", "|"],
    ["A", "S", "D", "F", "G", "H", "J", "K", "L", ":", "\""],
    ["Z", "X", "C", "V", "B", "N", "M", "<", ">", "?"]
]

UA_ROWS = [
    ["'", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "="],
    ["й", "ц", "у", "к", "е", "н", "г", "ш", "щ", "з", "х", "ї", "\\"],
    ["ф", "і", "в", "а", "п", "р", "о", "л", "д", "ж", "є"],
    ["я", "ч", "с", "м", "и", "т", "ь", "б", "ю", "."]
]

UA_SHIFT_ROWS = [
    ["\"", "!", "\"", "№", ";", "%", ":", "?", "*", "(", ")", "_", "+"],
    ["Й", "Ц", "У", "К", "Е", "Н", "Г", "Ш", "Щ", "З", "Х", "Ї", "/"],
    ["Ф", "І", "В", "А", "П", "Р", "О", "Л", "Д", "Ж", "Є"],
    ["Я", "Ч", "С", "М", "И", "Т", "Ь", "Б", "Ю", ","]
]

# ---------------------------------------------------------------------------
# Navigation Rail Item (QToolButton with 56x32 indicator pill)
# ---------------------------------------------------------------------------
class NavItem(QToolButton):
    def __init__(self, label: str, icon_path: Path, parent=None):
        super().__init__(parent)
        self.label = label
        self.icon_path = icon_path
        self.setObjectName("NavItem")
        self.setCheckable(True)
        self.setFixedSize(80, 58)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        checked = self.isChecked()
        hover = self.underMouse()

        # 1. Indicator Pill (56x32, radius 16)
        pill_rect = QRectF((self.width() - 56) / 2.0, 0.0, 56.0, 32.0)
        if checked:
            p.setBrush(QColor("#173A63"))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(pill_rect, 16.0, 16.0)
        elif hover:
            p.setBrush(QColor("#202027"))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(pill_rect, 16.0, 16.0)

        # 2. Icon (22x22 centered inside pill)
        icon_color = "#D3E7FF" if checked else ("#EDEDF2" if hover else "#A4A4B2")
        if self.icon_path.exists():
            pm = ui_common.svg_pixmap(self.icon_path, icon_color, 22)
            icon_x = (self.width() - 22) / 2.0
            icon_y = (32 - 22) / 2.0
            p.drawPixmap(int(icon_x), int(icon_y), pm)

        # 3. Label (12px, centered below pill)
        text_color = "#EDEDF2" if checked else "#A4A4B2"
        text_weight = QFont.Weight.DemiBold if checked else QFont.Weight.Medium
        p.setFont(ui_common.text_font(12, text_weight))
        p.setPen(QColor(text_color))
        text_rect = QRectF(0.0, 36.0, float(self.width()), 18.0)
        p.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.label)
        p.end()

# ---------------------------------------------------------------------------
# General Settings Row (Clickable row with Switch)
# ---------------------------------------------------------------------------
class SwitchRow(QWidget):
    def __init__(self, icon_path: Path, title: str, hint: str, is_checked: bool, on_toggle=None, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.on_toggle = on_toggle

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(14)

        # Icon Tile (40x40, radius 14)
        self.icon_tile = QLabel(self)
        self.icon_tile.setObjectName("IconTile")
        self.icon_tile.setFixedSize(40, 40)
        self.icon_tile.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if icon_path.exists():
            self.icon_tile.setPixmap(ui_common.svg_pixmap(icon_path, "#4BA7F4", 20))
        layout.addWidget(self.icon_tile)

        # Title & Hint
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setContentsMargins(0, 0, 0, 0)

        lbl_title = QLabel(title, self)
        lbl_title.setObjectName("RowTitle")
        lbl_title.setFont(ui_common.text_font(15, QFont.Weight.Medium))
        text_layout.addWidget(lbl_title)

        lbl_hint = QLabel(hint, self)
        lbl_hint.setObjectName("RowHint")
        lbl_hint.setFont(ui_common.text_font(13, QFont.Weight.Normal))
        text_layout.addWidget(lbl_hint)

        layout.addLayout(text_layout, stretch=1)

        # Switch Checkbox
        self.switch = QCheckBox(self)
        self.switch.setObjectName("Switch")
        self.switch.setChecked(is_checked)
        self.switch.setCursor(Qt.CursorShape.PointingHandCursor)
        if on_toggle:
            self.switch.toggled.connect(on_toggle)
        layout.addWidget(self.switch)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.switch.toggle()
        super().mousePressEvent(event)

    def isChecked(self) -> bool:
        return self.switch.isChecked()

    def setChecked(self, val: bool):
        self.switch.setChecked(val)

# ---------------------------------------------------------------------------
# Stepper Row (Popup duration: - 5 с +)
# ---------------------------------------------------------------------------
class StepperRow(QWidget):
    def __init__(self, icon_path: Path, title: str, hint: str, initial_val: int = 5, on_change=None, parent=None):
        super().__init__(parent)
        self.value = max(1, min(20, initial_val))
        self.on_change = on_change

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(14)

        # Icon Tile (Round, radius 20)
        self.icon_tile = QLabel(self)
        self.icon_tile.setObjectName("IconTile")
        self.icon_tile.setProperty("round", "true")
        self.icon_tile.setFixedSize(40, 40)
        self.icon_tile.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if icon_path.exists():
            self.icon_tile.setPixmap(ui_common.svg_pixmap(icon_path, "#4BA7F4", 20))
        layout.addWidget(self.icon_tile)

        # Title & Hint
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setContentsMargins(0, 0, 0, 0)

        lbl_title = QLabel(title, self)
        lbl_title.setObjectName("RowTitle")
        lbl_title.setFont(ui_common.text_font(15, QFont.Weight.Medium))
        text_layout.addWidget(lbl_title)

        lbl_hint = QLabel(hint, self)
        lbl_hint.setObjectName("RowHint")
        lbl_hint.setFont(ui_common.text_font(13, QFont.Weight.Normal))
        text_layout.addWidget(lbl_hint)

        layout.addLayout(text_layout, stretch=1)

        # Stepper Widget container
        self.stepper_box = QFrame(self)
        self.stepper_box.setObjectName("Stepper")
        stepper_layout = QHBoxLayout(self.stepper_box)
        stepper_layout.setContentsMargins(4, 4, 4, 4)
        stepper_layout.setSpacing(4)

        # Minus button (36x36 circle)
        self.btn_minus = QPushButton("−", self.stepper_box)
        self.btn_minus.setObjectName("StepMinus")
        self.btn_minus.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_minus.clicked.connect(self._step_down)
        stepper_layout.addWidget(self.btn_minus)

        # Value label
        self.lbl_value = QLabel(f"{self.value} с", self.stepper_box)
        self.lbl_value.setObjectName("StepValue")
        self.lbl_value.setFont(ui_common.display_font(17, QFont.Weight.DemiBold))
        self.lbl_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stepper_layout.addWidget(self.lbl_value)

        # Plus button (36x36 rounded square radius 12)
        self.btn_plus = QPushButton("+", self.stepper_box)
        self.btn_plus.setObjectName("StepPlus")
        self.btn_plus.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_plus.clicked.connect(self._step_up)
        stepper_layout.addWidget(self.btn_plus)

        layout.addWidget(self.stepper_box)

    def _step_down(self):
        if self.value > 1:
            self.value -= 1
            self.lbl_value.setText(f"{self.value} с")
            if self.on_change:
                self.on_change(self.value)

    def _step_up(self):
        if self.value < 20:
            self.value += 1
            self.lbl_value.setText(f"{self.value} с")
            if self.on_change:
                self.on_change(self.value)

    def getValue(self) -> int:
        return self.value

    def setValue(self, val: int):
        self.value = max(1, min(20, val))
        self.lbl_value.setText(f"{self.value} с")

# ---------------------------------------------------------------------------
# Hotkey Tile (Expressive Shape + Title + 2-line Hint + Key Chips + Button)
# ---------------------------------------------------------------------------
class HotkeyTile(QFrame):
    def __init__(self, title: str, default_hint: str, shape_name: str, fill_color: str,
                 ink_color: str, icon_name: str, hotkey_data: dict, on_changed_cb=None,
                 request_record_cb=None, parent=None):
        super().__init__(parent)
        self.title = title
        self.default_hint = default_hint
        self.shape_name = shape_name
        self.fill_color = fill_color
        self.ink_color = ink_color
        self.icon_name = icon_name
        self.on_changed_cb = on_changed_cb
        self.request_record_cb = request_record_cb

        self.recorded_modifiers = list(hotkey_data.get("modifiers", []))
        self.recorded_vk = hotkey_data.get("vk", 0)
        self.recorded_display = hotkey_data.get("display", "")

        self.is_recording = False
        self.setObjectName("HotkeyTile")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.init_ui()

    def init_ui(self):
        base_dir = Path(get_resource_path("shapes")).parent
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        # 1. Expressive Shape + Icon (48x48)
        shape_path = base_dir / "shapes" / f"{self.shape_name}.svg"
        icon_path = base_dir / "icons" / f"{self.icon_name}.svg"
        self.icon_label = QLabel(self)
        self.icon_label.setFixedSize(48, 48)
        if shape_path.exists() and icon_path.exists():
            pm = ui_common.shape_with_icon(shape_path, self.fill_color, icon_path, self.ink_color, 48, 22)
            self.icon_label.setPixmap(pm)
        layout.addWidget(self.icon_label)

        # 2. Title
        self.lbl_title = QLabel(self.title, self)
        self.lbl_title.setObjectName("TileTitle")
        self.lbl_title.setFont(ui_common.text_font(15, QFont.Weight.DemiBold))
        layout.addWidget(self.lbl_title)

        # 3. Hint (min-height 34px for consistent 2-row layout)
        self.lbl_hint = QLabel(self.default_hint, self)
        self.lbl_hint.setObjectName("TileHint")
        self.lbl_hint.setFont(ui_common.text_font(12, QFont.Weight.Normal))
        self.lbl_hint.setWordWrap(True)
        self.lbl_hint.setMinimumHeight(34)
        layout.addWidget(self.lbl_hint)

        # 4. Chips Container
        self.chips_widget = QWidget(self)
        self.chips_layout = QHBoxLayout(self.chips_widget)
        self.chips_layout.setContentsMargins(0, 0, 0, 0)
        self.chips_layout.setSpacing(4)
        self.chips_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.chips_widget)
        self.update_chips()

        # 5. Action Button ("Змінити" / "Скасувати")
        self.btn_action = QPushButton("Змінити", self)
        self.btn_action.setProperty("variant", "container")
        self.btn_action.setProperty("size", "small")
        self.btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_action.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_action.clicked.connect(self._toggle_recording)
        layout.addWidget(self.btn_action)

    def _normalize_key_name(self, name: str) -> str:
        s = name.strip()
        lower = s.lower()
        if lower == "ctrl":
            return "Ctrl"
        if lower == "shift":
            return "Shift"
        if lower == "alt":
            return "Alt"
        if lower == "win":
            return "Win"
        return s.upper()

    def update_chips(self):
        # Clear existing chips
        while self.chips_layout.count():
            item = self.chips_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Build keys list
        parts = []
        if self.recorded_display:
            parts = [self._normalize_key_name(k) for k in self.recorded_display.split(" + ") if k.strip()]
        else:
            for m in self.recorded_modifiers:
                parts.append(self._normalize_key_name(m))
            if self.recorded_vk in VK_TO_NAME:
                parts.append(self._normalize_key_name(VK_TO_NAME[self.recorded_vk]))

        if not parts:
            parts = ["Немає"]

        for key_text in parts:
            chip = QLabel(key_text, self.chips_widget)
            chip.setObjectName("KeyChip")
            chip.setFont(ui_common.display_font(13, QFont.Weight.DemiBold))
            chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.chips_layout.addWidget(chip)

    def _toggle_recording(self):
        if self.is_recording:
            self.cancel_recording()
        else:
            if self.request_record_cb:
                self.request_record_cb(self)
            self.start_recording()

    def start_recording(self):
        self.is_recording = True
        self.setProperty("recording", "true")
        self.style().unpolish(self)
        self.style().polish(self)

        self.lbl_hint.setText("Натисніть нову комбінацію · Esc — скасувати")
        self.lbl_hint.style().unpolish(self.lbl_hint)
        self.lbl_hint.style().polish(self.lbl_hint)

        # Dim chips with opacity 0.55
        opacity_effect = QGraphicsOpacityEffect(self.chips_widget)
        opacity_effect.setOpacity(0.55)
        self.chips_widget.setGraphicsEffect(opacity_effect)

        for i in range(self.chips_layout.count()):
            w = self.chips_layout.itemAt(i).widget()
            if w:
                w.style().unpolish(w)
                w.style().polish(w)

        self.btn_action.setText("Скасувати")
        self.btn_action.setProperty("variant", "outline-glow")
        self.btn_action.style().unpolish(self.btn_action)
        self.btn_action.style().polish(self.btn_action)

        self.grabKeyboard()
        self.setFocus()

    def cancel_recording(self):
        if not self.is_recording:
            return

        self.is_recording = False
        self.releaseKeyboard()

        self.setProperty("recording", "false")
        self.style().unpolish(self)
        self.style().polish(self)

        self.lbl_hint.setText(self.default_hint)
        self.lbl_hint.style().unpolish(self.lbl_hint)
        self.lbl_hint.style().polish(self.lbl_hint)

        self.chips_widget.setGraphicsEffect(None)
        self.update_chips()

        self.btn_action.setText("Змінити")
        self.btn_action.setProperty("variant", "container")
        self.btn_action.style().unpolish(self.btn_action)
        self.btn_action.style().polish(self.btn_action)

    def keyPressEvent(self, event):
        if not self.is_recording:
            super().keyPressEvent(event)
            return

        key = event.key()

        # Esc: cancel without changes
        if key == Qt.Key.Key_Escape:
            self.cancel_recording()
            event.accept()
            return

        # Ignore standalone modifier presses
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            event.accept()
            return

        # Parse modifiers
        modifiers = event.modifiers()
        mods = []
        display_parts = []
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            mods.append("ctrl")
            display_parts.append("Ctrl")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            mods.append("alt")
            display_parts.append("Alt")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            mods.append("shift")
            display_parts.append("Shift")
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            mods.append("win")
            display_parts.append("Win")

        # Native Virtual Key
        vk = event.nativeVirtualKey()
        if not vk:
            text = event.text()
            if text and len(text) == 1 and text.isascii():
                vk = ord(text.upper())
            else:
                vk = key

        if vk in VK_TO_NAME:
            key_name = VK_TO_NAME[vk]
        else:
            text = event.text()
            if text and len(text) == 1 and text.isprintable():
                key_name = text.upper()
            else:
                key_name = f"KEY_{vk}"

        if vk:
            self.recorded_modifiers = mods
            self.recorded_vk = vk
            display_parts.append(self._normalize_key_name(key_name))
            self.recorded_display = " + ".join(display_parts)

            logging.info(f"Recorded hotkey for {self.title}: {self.recorded_display}")

            self.cancel_recording()
            if self.on_changed_cb:
                self.on_changed_cb()

        event.accept()

# ---------------------------------------------------------------------------
# Visual Keyboard CharKey (Custom paintEvent: main top-left, translation bottom-right)
# ---------------------------------------------------------------------------
class CharKey(QPushButton):
    def __init__(self, main_char: str, tr_char: str, parent=None):
        super().__init__(parent)
        self.main_char = main_char
        self.tr_char = tr_char
        self.setObjectName("CharKey")
        self.setMinimumWidth(0)
        self.setFixedHeight(44)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        sel = self.property("selected") is True

        # Main character top-left (left 8, top 5)
        p.setFont(ui_common.display_font(16, QFont.Weight.DemiBold))
        p.setPen(QColor("#EDEDF2"))
        p.drawText(self.rect().adjusted(8, 5, 0, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, self.main_char)

        # Translation character bottom-right (right 7, bottom 4)
        # Never draw "?"; highlight color becomes #7FE0F9 when selected
        p.setFont(ui_common.display_font(13, QFont.Weight.DemiBold))
        p.setPen(QColor("#7FE0F9" if sel else "#4BA7F4"))
        p.drawText(self.rect().adjusted(0, 0, -7, -4), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom, self.tr_char)

        p.end()

# ---------------------------------------------------------------------------
# Visual Keyboard ModKey (Non-clickable helper key: Tab, Caps, Enter, Shift, Backspace)
# ---------------------------------------------------------------------------
class ModKey(QLabel):
    def __init__(self, label: str, parent=None):
        super().__init__(label, parent)
        self.setObjectName("ModKey")
        self.setMinimumWidth(0)
        self.setFixedHeight(44)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFont(ui_common.text_font(12, QFont.Weight.Medium))

# ---------------------------------------------------------------------------
# Snackbar Widget (Feedback page bottom banner)
# ---------------------------------------------------------------------------
class Snackbar(QFrame):
    def __init__(self, message: str, parent=None):
        super().__init__(parent)
        self.setObjectName("Snackbar")
        self.setCursor(Qt.CursorShape.ArrowCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 8, 12, 8)
        layout.setSpacing(16)

        lbl = QLabel(message, self)
        lbl.setFont(ui_common.text_font(14, QFont.Weight.Medium))
        layout.addWidget(lbl)

        btn_ok = QPushButton("OK", self)
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setFont(ui_common.text_font(14, QFont.Weight.DemiBold))
        btn_ok.clicked.connect(self.hide)
        layout.addWidget(btn_ok)

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)

    def show_banner(self, duration_ms: int = 4000):
        self.show()
        self.raise_()
        self.hide_timer.start(duration_ms)

# ---------------------------------------------------------------------------
# Main SettingsWindow
# ---------------------------------------------------------------------------
class SettingsWindow(QWidget):
    def __init__(self, config, on_saved_callback=None):
        super().__init__()
        self.config = config
        self.on_saved_callback = on_saved_callback
        self.has_unsaved_changes = False

        # Load local copies of mappings
        (
            self.local_mappings,
            self.local_mappings_shift,
            self.local_mappings_ua_to_en,
            self.local_mappings_ua_to_en_shift
        ) = self.config.get_mappings()

        # Layout mapping editor state
        self.active_edit_kb = None     # 'en' or 'ua'
        self.active_edit_char = None
        self.active_edit_btn = None
        self.is_shift_mode = False

        self.setObjectName("SettingsWindow")
        self.setWindowTitle(f"LayoutCorrector v{APP_VERSION}")
        self.setFixedSize(950, 800)
        self.setWindowFlags(Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowMinimizeButtonHint)

        logo_path = get_resource_path("logo.png")
        self.setWindowIcon(QIcon(logo_path))

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.init_ui()

    def init_ui(self):
        base_dir = Path(get_resource_path("icons")).parent

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ---------------- 1. Navigation Rail (Fixed width 96px) ----------------
        self.nav_rail = QWidget(self)
        self.nav_rail.setObjectName("NavRail")
        self.nav_rail.setFixedWidth(96)

        rail_layout = QVBoxLayout(self.nav_rail)
        rail_layout.setContentsMargins(8, 20, 8, 20)
        rail_layout.setSpacing(6)
        rail_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        # App Logo (44x44, margin-bottom 22px)
        logo_label = QLabel(self.nav_rail)
        logo_label.setFixedSize(44, 44)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_pm = QPixmap(get_resource_path("logo.png"))
        if not logo_pm.isNull():
            logo_label.setPixmap(logo_pm.scaled(44, 44, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        rail_layout.addWidget(logo_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        rail_layout.addSpacing(22)

        # Navigation Buttons Group
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        self.nav_item_hotkeys = NavItem("Клавіші", base_dir / "icons" / "nav_hotkeys.svg", self.nav_rail)
        self.nav_item_layouts = NavItem("Розкладки", base_dir / "icons" / "nav_layouts.svg", self.nav_rail)
        self.nav_item_feedback = NavItem("Відгук", base_dir / "icons" / "nav_feedback.svg", self.nav_rail)

        self.nav_group.addButton(self.nav_item_hotkeys, 0)
        self.nav_group.addButton(self.nav_item_layouts, 1)
        self.nav_group.addButton(self.nav_item_feedback, 2)

        rail_layout.addWidget(self.nav_item_hotkeys, alignment=Qt.AlignmentFlag.AlignHCenter)
        rail_layout.addWidget(self.nav_item_layouts, alignment=Qt.AlignmentFlag.AlignHCenter)
        rail_layout.addWidget(self.nav_item_feedback, alignment=Qt.AlignmentFlag.AlignHCenter)

        rail_layout.addStretch()

        # Version label at bottom
        lbl_version = QLabel(f"v{APP_VERSION}", self.nav_rail)
        lbl_version.setObjectName("NavVersion")
        lbl_version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_version.setFont(ui_common.text_font(11, QFont.Weight.Medium))
        rail_layout.addWidget(lbl_version, alignment=Qt.AlignmentFlag.AlignHCenter)

        root_layout.addWidget(self.nav_rail)

        # ---------------- 2. QStackedWidget (3 Pages) ----------------
        self.stack = QStackedWidget(self)

        self.page_hotkeys = self.create_page_hotkeys()
        self.page_layouts = self.create_page_layouts()
        self.page_feedback = self.create_page_feedback()

        self.stack.addWidget(self.page_hotkeys)
        self.stack.addWidget(self.page_layouts)
        self.stack.addWidget(self.page_feedback)

        self.nav_group.idClicked.connect(self._on_nav_clicked)
        self.nav_item_hotkeys.setChecked(True)

        root_layout.addWidget(self.stack, stretch=1)

    def _on_nav_clicked(self, page_id: int):
        # Cancel any active hotkey recording
        self.tile_fix.cancel_recording()
        self.tile_popup.cancel_recording()
        self.tile_case.cancel_recording()

        self.stack.setCurrentIndex(page_id)

    def _mark_changed(self):
        self.has_unsaved_changes = True
        self._update_save_buttons_state(saved=False)

    def _update_save_buttons_state(self, saved: bool):
        for btn in (self.btn_save_hotkeys, self.btn_save_layouts):
            if saved:
                btn.setText("Збережено")
                btn.setProperty("saved", "true")
            else:
                btn.setText("Зберегти")
                btn.setProperty("saved", "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    # =========================================================================
    # PAGE 1: Hotkeys & Options (screens/01, screens/02)
    # =========================================================================
    def create_page_hotkeys(self) -> QWidget:
        base_dir = Path(get_resource_path("icons")).parent
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 28, 32, 24)
        layout.setSpacing(18)

        # Header
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        lbl_brand = QLabel("LayoutCorrector", page)
        lbl_brand.setObjectName("BrandEyebrow")
        lbl_brand.setFont(ui_common.text_font(13, QFont.Weight.DemiBold))
        title_col.addWidget(lbl_brand)

        lbl_title = QLabel("Гарячі клавіші та опції", page)
        lbl_title.setObjectName("PageTitle")
        lbl_title.setFont(ui_common.display_font(34, QFont.Weight.Bold))
        title_col.addWidget(lbl_title)
        header_layout.addLayout(title_col)

        header_layout.addStretch()

        # Save Button
        self.btn_save_hotkeys = QPushButton("Зберегти", page)
        self.btn_save_hotkeys.setProperty("variant", "primary")
        self.btn_save_hotkeys.setCursor(Qt.CursorShape.PointingHandCursor)
        check_path = base_dir / "icons" / "check.svg"
        if check_path.exists():
            self.btn_save_hotkeys.setIcon(ui_common.svg_icon(check_path, "#03213F", 18))
        self.btn_save_hotkeys.clicked.connect(self.save_settings)
        header_layout.addWidget(self.btn_save_hotkeys)

        layout.addLayout(header_layout)

        # Card 1: GENERAL (ЗАГАЛЬНЕ)
        card_general = QFrame(page)
        card_general.setObjectName("Card")
        cg_layout = QVBoxLayout(card_general)
        cg_layout.setContentsMargins(8, 8, 8, 8)
        cg_layout.setSpacing(0)

        lbl_sec1 = QLabel("ЗАГАЛЬНЕ", card_general)
        lbl_sec1.setObjectName("SectionLabel")
        lbl_sec1.setFont(ui_common.text_font(13, QFont.Weight.DemiBold))
        cg_layout.addWidget(lbl_sec1)

        self.row_autorun = SwitchRow(
            base_dir / "icons" / "opt_autostart.svg",
            "Запускати разом з Windows",
            "Програма стартує у треї після входу в систему",
            self.config.settings.get("autorun", True),
            on_toggle=lambda _: self._mark_changed(),
            parent=card_general
        )
        cg_layout.addWidget(self.row_autorun)

        self.row_select = SwitchRow(
            base_dir / "icons" / "opt_select.svg",
            "Виділяти виправлений текст",
            "Після конвертації текст залишається виділеним",
            self.config.settings.get("select_after_replace", True),
            on_toggle=lambda _: self._mark_changed(),
            parent=card_general
        )
        cg_layout.addWidget(self.row_select)

        self.row_auto_switch = SwitchRow(
            base_dir / "icons" / "opt_language.svg",
            "Перемикати мову введення",
            "Система переходить на розкладку виправленого тексту",
            self.config.settings.get("auto_switch_layout", True),
            on_toggle=lambda _: self._mark_changed(),
            parent=card_general
        )
        cg_layout.addWidget(self.row_auto_switch)

        self.row_duration = StepperRow(
            base_dir / "icons" / "opt_timer.svg",
            "Тривалість попапу",
            "Скільки секунд вікно перекладу видно біля курсора (1–20)",
            self.config.settings.get("popup_duration", 5),
            on_change=lambda _: self._mark_changed(),
            parent=card_general
        )
        cg_layout.addWidget(self.row_duration)

        layout.addWidget(card_general)

        # Card 2: HOTKEYS (ГАРЯЧІ КЛАВІШІ)
        card_hotkeys = QFrame(page)
        card_hotkeys.setObjectName("Card")
        chk_layout = QVBoxLayout(card_hotkeys)
        chk_layout.setContentsMargins(8, 8, 8, 8)
        chk_layout.setSpacing(8)

        lbl_sec2 = QLabel("ГАРЯЧІ КЛАВІШІ", card_hotkeys)
        lbl_sec2.setObjectName("SectionLabel")
        lbl_sec2.setFont(ui_common.text_font(13, QFont.Weight.DemiBold))
        chk_layout.addWidget(lbl_sec2)

        tiles_layout = QHBoxLayout()
        tiles_layout.setContentsMargins(0, 0, 0, 0)
        tiles_layout.setSpacing(8)

        def request_exclusive_record(active_tile):
            for t in (self.tile_fix, self.tile_popup, self.tile_case):
                if t is not active_tile:
                    t.cancel_recording()

        self.tile_fix = HotkeyTile(
            "Виправити на місці",
            "Виділіть текст — він конвертується прямо в редакторі",
            "cookie9", "#173A63", "#D3E7FF", "hk_fix",
            self.config.get_hotkey_replace(),
            on_changed_cb=self._mark_changed,
            request_record_cb=request_exclusive_record,
            parent=card_hotkeys
        )
        tiles_layout.addWidget(self.tile_fix, stretch=1)

        self.tile_popup = HotkeyTile(
            "Переклад у попапі",
            "Правильний варіант з’явиться біля курсора",
            "clover4", "#0F3A44", "#B5EEFC", "hk_popup",
            self.config.get_hotkey_popup(),
            on_changed_cb=self._mark_changed,
            request_record_cb=request_exclusive_record,
            parent=card_hotkeys
        )
        tiles_layout.addWidget(self.tile_popup, stretch=1)

        self.tile_case = HotkeyTile(
            "Циклічна зміна регістру",
            "Кожне Слово → ВСІ ВЕЛИКІ → всі малі",
            "flower6", "#26305A", "#CDD6FF", "hk_case",
            self.config.get_hotkey_case(),
            on_changed_cb=self._mark_changed,
            request_record_cb=request_exclusive_record,
            parent=card_hotkeys
        )
        tiles_layout.addWidget(self.tile_case, stretch=1)

        chk_layout.addLayout(tiles_layout)
        layout.addWidget(card_hotkeys)

        layout.addStretch()
        return page

    # =========================================================================
    # PAGE 2: Layout Editor (screens/03, screens/04, screens/05)
    # =========================================================================
    def create_page_layouts(self) -> QWidget:
        base_dir = Path(get_resource_path("icons")).parent
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 28, 32, 24)
        layout.setSpacing(16)

        # Header
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        lbl_brand = QLabel("LayoutCorrector", page)
        lbl_brand.setObjectName("BrandEyebrow")
        lbl_brand.setFont(ui_common.text_font(13, QFont.Weight.DemiBold))
        title_col.addWidget(lbl_brand)

        lbl_title = QLabel("Редактор розкладок", page)
        lbl_title.setObjectName("PageTitle")
        lbl_title.setFont(ui_common.display_font(34, QFont.Weight.Bold))
        title_col.addWidget(lbl_title)
        header_layout.addLayout(title_col)

        header_layout.addStretch()

        # Action Buttons: Скинути & Зберегти
        self.btn_reset_layouts = QPushButton("Скинути", page)
        self.btn_reset_layouts.setProperty("variant", "tonal")
        self.btn_reset_layouts.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset_layouts.clicked.connect(self.reset_mappings)
        header_layout.addWidget(self.btn_reset_layouts)

        self.btn_save_layouts = QPushButton("Зберегти", page)
        self.btn_save_layouts.setProperty("variant", "primary")
        self.btn_save_layouts.setCursor(Qt.CursorShape.PointingHandCursor)
        check_path = base_dir / "icons" / "check.svg"
        if check_path.exists():
            self.btn_save_layouts.setIcon(ui_common.svg_icon(check_path, "#03213F", 18))
        self.btn_save_layouts.clicked.connect(self.save_settings)
        header_layout.addWidget(self.btn_save_layouts)

        layout.addLayout(header_layout)

        # Subheader Row: Segmented Switch ("Звичайні | ⇧ Shift") + EditorHint
        sub_layout = QHBoxLayout()
        sub_layout.setContentsMargins(0, 0, 0, 0)
        sub_layout.setSpacing(14)

        seg_container = QWidget(page)
        seg_layout = QHBoxLayout(seg_container)
        seg_layout.setContentsMargins(0, 0, 0, 0)
        seg_layout.setSpacing(2)

        self.btn_seg_normal = QPushButton("Звичайні", seg_container)
        self.btn_seg_normal.setObjectName("SegLeft")
        self.btn_seg_normal.setCheckable(True)
        self.btn_seg_normal.setChecked(True)
        self.btn_seg_normal.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_seg_shift = QPushButton("⇧ Shift", seg_container)
        self.btn_seg_shift.setObjectName("SegRight")
        self.btn_seg_shift.setCheckable(True)
        self.btn_seg_shift.setCursor(Qt.CursorShape.PointingHandCursor)

        self.seg_group = QButtonGroup(page)
        self.seg_group.setExclusive(True)
        self.seg_group.addButton(self.btn_seg_normal, 0)
        self.seg_group.addButton(self.btn_seg_shift, 1)
        self.seg_group.idClicked.connect(self._on_shift_segmented_changed)

        seg_layout.addWidget(self.btn_seg_normal)
        seg_layout.addWidget(self.btn_seg_shift)
        sub_layout.addWidget(seg_container)

        self.lbl_editor_hint = QLabel(
            "Клікніть клавішу на екрані, потім натисніть потрібну на фізичній клавіатурі.",
            page
        )
        self.lbl_editor_hint.setObjectName("EditorHint")
        self.lbl_editor_hint.setFont(ui_common.text_font(13, QFont.Weight.Normal))
        sub_layout.addWidget(self.lbl_editor_hint, stretch=1)

        layout.addLayout(sub_layout)

        # Keyboard Cards (Both identical width & styling)
        self.card_en_kb = QFrame(page)
        self.card_en_kb.setObjectName("Card")
        self.layout_en_card = QVBoxLayout(self.card_en_kb)
        self.layout_en_card.setContentsMargins(16, 14, 16, 16)
        self.layout_en_card.setSpacing(10)
        layout.addWidget(self.card_en_kb)

        self.card_ua_kb = QFrame(page)
        self.card_ua_kb.setObjectName("Card")
        self.layout_ua_card = QVBoxLayout(self.card_ua_kb)
        self.layout_ua_card.setContentsMargins(16, 14, 16, 16)
        self.layout_ua_card.setSpacing(10)
        layout.addWidget(self.card_ua_kb)

        self.draw_keyboards()
        layout.addStretch()
        return page

    def _on_shift_segmented_changed(self, idx: int):
        self.is_shift_mode = (idx == 1)
        self._clear_active_key_selection()
        self.draw_keyboards()

    def draw_keyboards(self):
        # 1. Clear previous keyboards
        self._clear_card_content(self.layout_en_card)
        self._clear_card_content(self.layout_ua_card)

        # 2. Setup Headers
        en_header = QHBoxLayout()
        en_header.setSpacing(10)
        chip_en = QLabel("EN → UA", self.card_en_kb)
        chip_en.setObjectName("DirChip")
        chip_en.setAlignment(Qt.AlignmentFlag.AlignCenter)
        en_header.addWidget(chip_en)
        title_en = QLabel("Англійська розкладка", self.card_en_kb)
        title_en.setObjectName("KeyboardTitle")
        title_en.setFont(ui_common.text_font(15, QFont.Weight.Medium))
        en_header.addWidget(title_en)
        en_header.addStretch()
        self.layout_en_card.addLayout(en_header)

        ua_header = QHBoxLayout()
        ua_header.setSpacing(10)
        chip_ua = QLabel("UA → EN", self.card_ua_kb)
        chip_ua.setObjectName("DirChip")
        chip_ua.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ua_header.addWidget(chip_ua)
        title_ua = QLabel("Українська розкладка", self.card_ua_kb)
        title_ua.setObjectName("KeyboardTitle")
        title_ua.setFont(ui_common.text_font(15, QFont.Weight.Medium))
        ua_header.addWidget(title_ua)
        ua_header.addStretch()
        self.layout_ua_card.addLayout(ua_header)

        # 3. Active data based on shift mode
        en_rows_data = EN_SHIFT_ROWS if self.is_shift_mode else EN_ROWS
        ua_rows_data = UA_SHIFT_ROWS if self.is_shift_mode else UA_ROWS
        active_map_en = self.local_mappings_shift if self.is_shift_mode else self.local_mappings
        active_map_ua = self.local_mappings_ua_to_en_shift if self.is_shift_mode else self.local_mappings_ua_to_en

        # 4. Render rows with exact unit ratios (1u = 4)
        self._render_keyboard_grid(self.layout_en_card, en_rows_data, active_map_en, "en", self.card_en_kb)
        self._render_keyboard_grid(self.layout_ua_card, ua_rows_data, active_map_ua, "ua", self.card_ua_kb)

    def _render_keyboard_grid(self, target_layout: QVBoxLayout, rows_data: list, active_map: dict, kb_id: str, parent: QWidget):
        rows_container = QVBoxLayout()
        rows_container.setSpacing(5)
        rows_container.setContentsMargins(0, 0, 0, 0)

        # Row 1: 13x1u symbols + Backspace (2u = stretch 8)
        r1 = QHBoxLayout()
        r1.setSpacing(5)
        for char in rows_data[0]:
            btn = self._create_char_key(char, active_map.get(char, ""), kb_id, parent)
            r1.addWidget(btn, 4)
        r1.addWidget(ModKey("← Backspace", parent), 8)
        rows_container.addLayout(r1)

        # Row 2: Tab (1.5u = 6) + 12x1u symbols + \ (1.5u = 6)
        r2 = QHBoxLayout()
        r2.setSpacing(5)
        r2.addWidget(ModKey("Tab ⇥", parent), 6)
        for char in rows_data[1][:-1]:
            btn = self._create_char_key(char, active_map.get(char, ""), kb_id, parent)
            r2.addWidget(btn, 4)
        # Last symbol on row 2 is backslash
        bs_char = rows_data[1][-1]
        bs_btn = self._create_char_key(bs_char, active_map.get(bs_char, ""), kb_id, parent)
        r2.addWidget(bs_btn, 6)
        rows_container.addLayout(r2)

        # Row 3: Caps Lock (1.75u = 7) + 11x1u symbols + Enter (2.25u = 9)
        r3 = QHBoxLayout()
        r3.setSpacing(5)
        r3.addWidget(ModKey("Caps Lock", parent), 7)
        for char in rows_data[2]:
            btn = self._create_char_key(char, active_map.get(char, ""), kb_id, parent)
            r3.addWidget(btn, 4)
        r3.addWidget(ModKey("Enter ↵", parent), 9)
        rows_container.addLayout(r3)

        # Row 4: Shift (2.25u = 9) + 10x1u symbols + Shift (2.75u = 11)
        r4 = QHBoxLayout()
        r4.setSpacing(5)
        r4.addWidget(ModKey("⇧ Shift", parent), 9)
        for char in rows_data[3]:
            btn = self._create_char_key(char, active_map.get(char, ""), kb_id, parent)
            r4.addWidget(btn, 4)
        r4.addWidget(ModKey("⇧ Shift", parent), 11)
        rows_container.addLayout(r4)

        target_layout.addLayout(rows_container)

    def _create_char_key(self, char: str, tr: str, kb_id: str, parent: QWidget) -> CharKey:
        btn = CharKey(char, tr, parent)
        btn.clicked.connect(lambda _, b=btn, c=char, k=kb_id: self._on_key_clicked(b, c, k))
        return btn

    def _clear_card_content(self, layout: QVBoxLayout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout_recursive(item.layout())

    def _clear_layout_recursive(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout_recursive(item.layout())

    def _on_key_clicked(self, btn: CharKey, char: str, kb_id: str):
        # Re-clicking selected key deselects it
        if self.active_edit_btn is btn:
            self._clear_active_key_selection()
            return

        self._clear_active_key_selection()

        self.active_edit_kb = kb_id
        self.active_edit_char = char
        self.active_edit_btn = btn

        btn.setProperty("selected", True)
        btn.style().unpolish(btn)
        btn.style().polish(btn)
        btn.update()

        # Update hint banner
        self.lbl_editor_hint.setText(f"Вибрано {char} → {btn.tr_char} — натисніть нову клавішу на фізичній клавіатурі")
        self.lbl_editor_hint.setProperty("active", "true")
        self.lbl_editor_hint.style().unpolish(self.lbl_editor_hint)
        self.lbl_editor_hint.style().polish(self.lbl_editor_hint)

        self.setFocus()

    def _clear_active_key_selection(self):
        if self.active_edit_btn:
            self.active_edit_btn.setProperty("selected", False)
            self.active_edit_btn.style().unpolish(self.active_edit_btn)
            self.active_edit_btn.style().polish(self.active_edit_btn)
            self.active_edit_btn.update()

        self.active_edit_kb = None
        self.active_edit_char = None
        self.active_edit_btn = None

        self.lbl_editor_hint.setText("Клікніть клавішу на екрані, потім натисніть потрібну на фізичній клавіатурі.")
        self.lbl_editor_hint.setProperty("active", "false")
        self.lbl_editor_hint.style().unpolish(self.lbl_editor_hint)
        self.lbl_editor_hint.style().polish(self.lbl_editor_hint)

    def keyPressEvent(self, event):
        # If mapping a key on layout page
        if self.active_edit_kb is not None:
            if event.key() == Qt.Key.Key_Escape:
                self._clear_active_key_selection()
                event.accept()
                return

            typed_char = event.text()
            if typed_char and len(typed_char) == 1:
                char_to_map = self.active_edit_char
                is_shift = self.is_shift_mode

                if self.active_edit_kb == 'en':
                    if is_shift:
                        self.local_mappings_shift[char_to_map] = typed_char
                    else:
                        self.local_mappings[char_to_map] = typed_char
                        if char_to_map.isalpha():
                            self.local_mappings_shift[char_to_map.upper()] = typed_char.upper()
                else:
                    if is_shift:
                        self.local_mappings_ua_to_en_shift[char_to_map] = typed_char
                    else:
                        self.local_mappings_ua_to_en[char_to_map] = typed_char
                        if char_to_map.isalpha():
                            self.local_mappings_ua_to_en_shift[char_to_map.upper()] = typed_char.upper()

                logging.info(f"Remapped: {char_to_map} -> {typed_char} (kb: {self.active_edit_kb}, shift: {is_shift})")

                self._clear_active_key_selection()
                self.draw_keyboards()
                self._mark_changed()
                event.accept()
                return

        super().keyPressEvent(event)

    # =========================================================================
    # PAGE 3: Feedback (screens/06, screens/07)
    # =========================================================================
    def create_page_feedback(self) -> QWidget:
        base_dir = Path(get_resource_path("icons")).parent
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 28, 32, 24)
        layout.setSpacing(18)

        # Header (No save/reset buttons)
        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        lbl_brand = QLabel("LayoutCorrector", page)
        lbl_brand.setObjectName("BrandEyebrow")
        lbl_brand.setFont(ui_common.text_font(13, QFont.Weight.DemiBold))
        title_col.addWidget(lbl_brand)

        lbl_title = QLabel("Зворотний зв’язок", page)
        lbl_title.setObjectName("PageTitle")
        lbl_title.setFont(ui_common.display_font(34, QFont.Weight.Bold))
        title_col.addWidget(lbl_title)
        layout.addLayout(title_col)

        # Hero Card
        hero_card = QFrame(page)
        hero_card.setObjectName("Card")
        hero_layout = QHBoxLayout(hero_card)
        hero_layout.setContentsMargins(36, 36, 36, 36)
        hero_layout.setSpacing(32)
        hero_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Left: Shape cookie9 148x148 fill #7FE0F9 + nav_feedback 56px ink #03213F
        hero_icon_lbl = QLabel(hero_card)
        hero_icon_lbl.setFixedSize(148, 148)
        shape_path = base_dir / "shapes" / "cookie9.svg"
        icon_path = base_dir / "icons" / "nav_feedback.svg"
        if shape_path.exists() and icon_path.exists():
            hero_icon_lbl.setPixmap(ui_common.shape_with_icon(shape_path, "#7FE0F9", icon_path, "#03213F", 148, 56))
        hero_layout.addWidget(hero_icon_lbl)

        # Right: HeroTitle + HeroText + CTA Button
        hero_text_col = QVBoxLayout()
        hero_text_col.setSpacing(12)
        hero_text_col.setAlignment(Qt.AlignmentFlag.AlignLeft)

        lbl_htitle = QLabel("Є ідея чи знайшли помилку?", hero_card)
        lbl_htitle.setObjectName("HeroTitle")
        lbl_htitle.setFont(ui_common.display_font(30, QFont.Weight.Bold))
        hero_text_col.addWidget(lbl_htitle)

        lbl_hdesc = QLabel("Коротка Google-форма відкриється у вашому браузері. Займе хвилину.", hero_card)
        lbl_hdesc.setObjectName("HeroText")
        lbl_hdesc.setFont(ui_common.text_font(15, QFont.Weight.Normal))
        lbl_hdesc.setWordWrap(True)
        hero_text_col.addWidget(lbl_hdesc)

        self.btn_feedback_cta = QPushButton("Залишити відгук", hero_card)
        self.btn_feedback_cta.setProperty("variant", "primary")
        self.btn_feedback_cta.setProperty("size", "cta")
        self.btn_feedback_cta.setCursor(Qt.CursorShape.PointingHandCursor)
        ext_path = base_dir / "icons" / "external.svg"
        if ext_path.exists():
            self.btn_feedback_cta.setIcon(ui_common.svg_icon(ext_path, "#03213F", 16))
        self.btn_feedback_cta.clicked.connect(self._on_feedback_cta_clicked)
        hero_text_col.addWidget(self.btn_feedback_cta)

        hero_layout.addLayout(hero_text_col, stretch=1)
        layout.addWidget(hero_card)

        # Steps Card ("ЩОБ МИ ШВИДШЕ РОЗІБРАЛИСЬ, ВКАЖІТЬ")
        steps_card = QFrame(page)
        steps_card.setObjectName("Card")
        sc_layout = QVBoxLayout(steps_card)
        sc_layout.setContentsMargins(24, 20, 24, 24)
        sc_layout.setSpacing(12)

        lbl_sc_title = QLabel("ЩОБ МИ ШВИДШЕ РОЗІБРАЛИСЬ, ВКАЖІТЬ", steps_card)
        lbl_sc_title.setObjectName("SectionLabel")
        lbl_sc_title.setFont(ui_common.text_font(13, QFont.Weight.DemiBold))
        sc_layout.addWidget(lbl_sc_title)

        steps_row = QHBoxLayout()
        steps_row.setSpacing(10)

        # Step 1
        s1 = QFrame(steps_card)
        s1.setObjectName("StepCard")
        s1_layout = QVBoxLayout(s1)
        s1_layout.setContentsMargins(16, 16, 16, 16)
        s1_layout.setSpacing(6)
        s1_num = QLabel("1", s1)
        s1_num.setObjectName("StepNum")
        s1_num.setFont(ui_common.display_font(22, QFont.Weight.Bold))
        s1_layout.addWidget(s1_num)
        s1_text = QLabel("У якій програмі це сталося", s1)
        s1_text.setFont(ui_common.text_font(14, QFont.Weight.Normal))
        s1_text.setWordWrap(True)
        s1_layout.addWidget(s1_text)
        steps_row.addWidget(s1, stretch=1)

        # Step 2
        s2 = QFrame(steps_card)
        s2.setObjectName("StepCard")
        s2_layout = QVBoxLayout(s2)
        s2_layout.setContentsMargins(16, 16, 16, 16)
        s2_layout.setSpacing(6)
        s2_num = QLabel("2", s2)
        s2_num.setObjectName("StepNum")
        s2_num.setFont(ui_common.display_font(22, QFont.Weight.Bold))
        s2_layout.addWidget(s2_num)
        s2_text = QLabel("Що ви набрали і що отримали", s2)
        s2_text.setFont(ui_common.text_font(14, QFont.Weight.Normal))
        s2_text.setWordWrap(True)
        s2_layout.addWidget(s2_text)
        steps_row.addWidget(s2, stretch=1)

        # Step 3
        s3 = QFrame(steps_card)
        s3.setObjectName("StepCard")
        s3_layout = QVBoxLayout(s3)
        s3_layout.setContentsMargins(16, 16, 16, 16)
        s3_layout.setSpacing(6)
        s3_num = QLabel("3", s3)
        s3_num.setObjectName("StepNum")
        s3_num.setFont(ui_common.display_font(22, QFont.Weight.Bold))
        s3_layout.addWidget(s3_num)

        s3_row = QHBoxLayout()
        s3_row.setSpacing(4)
        s3_lbl = QLabel("Версію програми —", s3)
        s3_lbl.setFont(ui_common.text_font(14, QFont.Weight.Normal))
        s3_row.addWidget(s3_lbl)

        self.btn_copy_version = QPushButton(f"v{APP_VERSION} · копіювати", s3)
        self.btn_copy_version.setObjectName("VersionChip")
        self.btn_copy_version.setFont(ui_common.display_font(13, QFont.Weight.DemiBold))
        self.btn_copy_version.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy_version.clicked.connect(self._copy_version)
        s3_row.addWidget(self.btn_copy_version)
        s3_row.addStretch()

        s3_layout.addLayout(s3_row)
        steps_row.addWidget(s3, stretch=1)

        sc_layout.addLayout(steps_row)
        layout.addWidget(steps_card)

        layout.addStretch()

        # Snackbar notification (positioned bottom center)
        self.snackbar = Snackbar("Форму відкрито у браузері", page)
        self.snackbar.hide()
        layout.addWidget(self.snackbar, alignment=Qt.AlignmentFlag.AlignHCenter)

        return page

    def _on_feedback_cta_clicked(self):
        QDesktopServices.openUrl(QUrl(FEEDBACK_URL))
        self.btn_feedback_cta.setText("Відкрити форму ще раз")
        self.snackbar.show_banner(4000)

    def _copy_version(self):
        cb = QApplication.clipboard()
        if cb:
            cb.setText(f"LayoutCorrector v{APP_VERSION}")
        self.btn_copy_version.setText("скопійовано ✓")
        QTimer.singleShot(2000, lambda: self.btn_copy_version.setText(f"v{APP_VERSION} · копіювати"))

    # =========================================================================
    # Synchronization & Persistence
    # =========================================================================
    def sync_from_config(self):
        """Sync UI controls with config in case tray actions changed values."""
        self.row_autorun.setChecked(self.config.settings.get("autorun", True))
        self.row_select.setChecked(self.config.settings.get("select_after_replace", True))
        self.row_auto_switch.setChecked(self.config.settings.get("auto_switch_layout", True))
        self.row_duration.setValue(self.config.settings.get("popup_duration", 5))

    def save_settings(self):
        # 1. Hotkeys
        self.config.set_hotkey_replace(
            self.tile_fix.recorded_modifiers,
            self.tile_fix.recorded_vk,
            self.tile_fix.recorded_display
        )
        self.config.set_hotkey_popup(
            self.tile_popup.recorded_modifiers,
            self.tile_popup.recorded_vk,
            self.tile_popup.recorded_display
        )
        self.config.set_hotkey_case(
            self.tile_case.recorded_modifiers,
            self.tile_case.recorded_vk,
            self.tile_case.recorded_display
        )

        # 2. Options
        autorun_val = self.row_autorun.isChecked()
        self.config.settings["autorun"] = autorun_val
        self.config.settings["select_after_replace"] = self.row_select.isChecked()
        self.config.settings["auto_switch_layout"] = self.row_auto_switch.isChecked()
        self.config.settings["popup_duration"] = self.row_duration.getValue()

        set_windows_autorun(autorun_val)

        # 3. Mappings Overrides (EN -> UA)
        for en, default_ua in DEFAULT_EN_TO_UA.items():
            current_ua = self.local_mappings.get(en, default_ua)
            if current_ua != default_ua:
                self.config.settings["en_to_ua_overrides"][en] = current_ua
            else:
                self.config.settings["en_to_ua_overrides"].pop(en, None)

        for en, default_ua in DEFAULT_EN_TO_UA_SHIFT.items():
            current_ua = self.local_mappings_shift.get(en, default_ua)
            if current_ua != default_ua:
                self.config.settings["en_to_ua_shift_overrides"][en] = current_ua
            else:
                self.config.settings["en_to_ua_shift_overrides"].pop(en, None)

        # 4. Mappings Overrides (UA -> EN)
        default_ua_to_en = {}
        for k, v in DEFAULT_EN_TO_UA.items():
            if v not in default_ua_to_en:
                default_ua_to_en[v] = k
        default_ua_to_en_shift = {}
        for k, v in DEFAULT_EN_TO_UA_SHIFT.items():
            if v not in default_ua_to_en_shift:
                default_ua_to_en_shift[v] = k

        for ua, default_en in default_ua_to_en.items():
            current_en = self.local_mappings_ua_to_en.get(ua, default_en)
            if current_en != default_en:
                self.config.settings["ua_to_en_overrides"][ua] = current_en
            else:
                self.config.settings["ua_to_en_overrides"].pop(ua, None)

        for ua, default_en in default_ua_to_en_shift.items():
            current_en = self.local_mappings_ua_to_en_shift.get(ua, default_en)
            if current_en != default_en:
                self.config.settings["ua_to_en_shift_overrides"][ua] = current_en
            else:
                self.config.settings["ua_to_en_shift_overrides"].pop(ua, None)

        self.config.save()

        if self.on_saved_callback:
            self.on_saved_callback()

        self.has_unsaved_changes = False
        self._update_save_buttons_state(saved=True)
        logging.info("Settings successfully saved.")

    def reset_mappings(self):
        self.config.reset_mappings()
        (
            self.local_mappings,
            self.local_mappings_shift,
            self.local_mappings_ua_to_en,
            self.local_mappings_ua_to_en_shift
        ) = self.config.get_mappings()

        self._clear_active_key_selection()
        self.draw_keyboards()
        self._mark_changed()
        logging.info("Layout mappings reset to defaults.")
