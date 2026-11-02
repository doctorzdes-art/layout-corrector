import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTabWidget, QMessageBox, QCheckBox, QFrame, QSpinBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QIcon, QPixmap
import os
import tempfile

from config import (
    DEFAULT_EN_TO_UA, DEFAULT_EN_TO_UA_SHIFT, VK_TO_NAME,
    DEFAULT_HOTKEY_REPLACE, DEFAULT_HOTKEY_POPUP, DEFAULT_HOTKEY_CASE,
    get_resource_path, APP_VERSION, FEEDBACK_URL
)

# Shared styles for the visual keyboard keys
KEY_BTN_STYLE = """
    QPushButton {{
        background-color: #1E1E22;
        border: 1px solid #3F3F46;
        border-radius: 8px;
        color: {color};
        font-weight: bold;
        font-size: 11px;
        padding: 0px;
        text-align: center;
    }}
    QPushButton:hover {{
        border-color: #3B82F6;
        background-color: #2D2D34;
    }}
"""

ACTIVE_KEY_BTN_STYLE = """
    QPushButton {
        background-color: #121214;
        border: 2px solid #3B82F6;
        border-radius: 8px;
        color: #60A5FA;
        font-weight: bold;
        font-size: 11px;
        padding: 0px;
        text-align: center;
    }
"""

KEY_COLORS = {'en': "#EEEEEE", 'ua': "#60A5FA"}

EDITOR_HINT_DEFAULT = "👉 Клікніть на будь-яку клавішу на клавіатурі, а потім натисніть кнопку на фізичній клавіатурі."

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

class KeySequenceEdit(QLineEdit):
    def __init__(self, default_cfg, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.recorded_modifiers = default_cfg.get("modifiers", [])
        self.recorded_vk = default_cfg.get("vk", 0)
        self.recorded_display = default_cfg.get("display", "")
        self.setText(self.recorded_display)
        self.setStyleSheet("""
            QLineEdit {
                background-color: #1E1E22;
                color: #EEEEEE;
                border: 1px solid #3F3F46;
                border-radius: 8px;
                padding: 10px;
                font-size: 13px;
                font-weight: bold;
            }
            QLineEdit:focus {
                border: 1px solid #3B82F6;
                background-color: #121214;
            }
        """)

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            super().keyPressEvent(event)
            return

        modifiers = event.modifiers()
        mods = []
        display_parts = []
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            mods.append("ctrl")
            display_parts.append("CTRL")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            mods.append("alt")
            display_parts.append("ALT")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            mods.append("shift")
            display_parts.append("SHIFT")
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            mods.append("win")
            display_parts.append("WIN")

        # nativeVirtualKey() returns the real Windows VK code of the physical key,
        # so recording works no matter which layout (EN/UA) is active at the moment
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
            display_parts.append(key_name)
            self.recorded_display = " + ".join(display_parts)
            self.setText(self.recorded_display)
            logging.info(f"Записано гарячу клавішу: {self.recorded_display}")
            
        event.accept()

class SettingsWindow(QWidget):
    def __init__(self, config, on_saved_callback=None):
        super().__init__()
        self.config = config
        self.on_saved_callback = on_saved_callback
        
        # Mapping edit states
        self.active_edit_kb = None # 'en' or 'ua'
        self.active_edit_char = None
        self.active_edit_btn = None
        
        # Load independent mappings
        self.local_mappings, self.local_mappings_shift, self.local_mappings_ua_to_en, self.local_mappings_ua_to_en_shift = self.config.get_mappings()
        
        self.logo_path = get_resource_path("logo.png")
        self.setWindowIcon(QIcon(self.logo_path))
        
        self.setWindowTitle(f"LayoutCorrector v{APP_VERSION}")
        self.resize(950, 800)
        self.setWindowFlags(Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowMinimizeButtonHint)

        # Set focus policy so we can capture physical key presses
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        arrow_dir = tempfile.gettempdir()
        self.up_arrow_path = os.path.join(arrow_dir, "lc_up_arrow.png").replace("\\", "/")
        self.down_arrow_path = os.path.join(arrow_dir, "lc_down_arrow.png").replace("\\", "/")
        self.generate_arrow_images()

        self.setStyleSheet(f"""
            QWidget {{
                background-color: #0F0F11;
                color: #EEEEEE;
                font-family: "Google Sans", "Montserrat", "Segoe UI", sans-serif;
            }}
            QTabWidget::panel {{
                border: 1px solid #232329;
                background-color: #18181C;
                border-radius: 12px;
            }}
            QTabBar::tab {{
                background-color: #18181C;
                color: #9CA3AF;
                border: 1px solid #232329;
                border-bottom-color: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 13px;
            }}
            QTabBar::tab:selected {{
                background-color: #18181C;
                color: #3B82F6;
                border: 1px solid #3B82F6;
                border-bottom-color: #18181C;
            }}
            QPushButton {{
                background-color: #1E1E22;
                color: #EEEEEE;
                border: 1px solid #3F3F46;
                border-radius: 8px;
                padding: 8px 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #2D2D34;
                border-color: #3B82F6;
            }}
            QPushButton#SaveBtn {{
                background-color: #3B82F6;
                color: #FFFFFF;
                border: none;
            }}
            QPushButton#SaveBtn:hover {{
                background-color: #60A5FA;
            }}
            QCheckBox {{
                spacing: 8px;
                font-weight: bold;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #3F3F46;
                background: #1E1E22;
            }}
            QCheckBox::indicator:checked {{
                background: #3B82F6;
                border-color: #3B82F6;
            }}
            QSpinBox {{
                background-color: #1E1E22;
                color: #EEEEEE;
                border: 1px solid #3F3F46;
                border-radius: 8px;
                padding-left: 10px;
                padding-right: 28px;
                font-weight: bold;
                height: 32px;
                min-height: 32px;
                max-height: 32px;
            }}
            QSpinBox:focus {{
                border-color: #3B82F6;
            }}
            QSpinBox::up-button {{
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 22px;
                height: 16px;
                border-left: 1px solid #3F3F46;
                border-bottom: 1px solid #3F3F46;
                background-color: #1E1E22;
                border-top-right-radius: 7px;
            }}
            QSpinBox::up-button:hover {{
                background-color: #2D2D34;
            }}
            QSpinBox::up-button:pressed {{
                background-color: #3B82F6;
            }}
            QSpinBox::up-arrow {{
                image: url({self.up_arrow_path});
                subcontrol-origin: margin;
                subcontrol-position: center;
                width: 10px;
                height: 10px;
            }}
            QSpinBox::down-button {{
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 22px;
                height: 16px;
                border-left: 1px solid #3F3F46;
                background-color: #1E1E22;
                border-bottom-right-radius: 7px;
            }}
            QSpinBox::down-button:hover {{
                background-color: #2D2D34;
            }}
            QSpinBox::down-button:pressed {{
                background-color: #3B82F6;
            }}
            QSpinBox::down-arrow {{
                image: url({self.down_arrow_path});
                subcontrol-origin: margin;
                subcontrol-position: center;
                width: 10px;
                height: 10px;
            }}
        """)

        self.init_ui()

    def generate_arrow_images(self):
        from PyQt6.QtGui import QPixmap, QPainter, QColor, QPolygon
        from PyQt6.QtCore import QPoint, Qt
        
        # Up arrow (triangle pointing up, color #EEEEEE)
        pixmap_up = QPixmap(10, 10)
        pixmap_up.fill(QColor("transparent"))
        painter = QPainter(pixmap_up)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#EEEEEE"))
        painter.setPen(Qt.PenStyle.NoPen)
        points_up = QPolygon([
            QPoint(5, 1),
            QPoint(1, 8),
            QPoint(9, 8)
        ])
        painter.drawPolygon(points_up)
        painter.end()
        pixmap_up.save(self.up_arrow_path)
        
        # Down arrow (triangle pointing down, color #EEEEEE)
        pixmap_down = QPixmap(10, 10)
        pixmap_down.fill(QColor("transparent"))
        painter = QPainter(pixmap_down)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#EEEEEE"))
        painter.setPen(Qt.PenStyle.NoPen)
        points_down = QPolygon([
            QPoint(5, 8),
            QPoint(1, 1),
            QPoint(9, 1)
        ])
        painter.drawPolygon(points_down)
        painter.end()
        pixmap_down.save(self.down_arrow_path)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Header Layout (Logo + Title)
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)
        
        logo_label = QLabel()
        logo_pixmap = QPixmap(self.logo_path)
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        header_layout.addWidget(logo_label)
        
        header = QLabel(f"LayoutCorrector v{APP_VERSION}")
        header.setFont(QFont("Google Sans", 18, QFont.Weight.Bold))
        header.setStyleSheet("color: #3B82F6;")
        header_layout.addWidget(header)
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)

        # Tab Widget
        self.tabs = QTabWidget(self)
        
        # Tab 1: Hotkeys & Options
        self.tab_hotkeys = QWidget()
        self.init_hotkeys_tab()
        self.tabs.addTab(self.tab_hotkeys, "Гарячі клавіші та Опції")
        
        # Tab 2: Visual Keyboard Mapper
        self.tab_mappings = QWidget()
        self.init_mappings_tab()
        self.tabs.addTab(self.tab_mappings, "Редактор розкладок")
        
        # Tab 3: Feedback
        self.tab_feedback = QWidget()
        self.init_feedback_tab()
        self.tabs.addTab(self.tab_feedback, "Зворотній зв'язок")
        
        main_layout.addWidget(self.tabs)

        # Bottom Buttons
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 5, 0, 0)
        
        self.btn_reset = QPushButton("Скинути налаштування клавіш")
        self.btn_reset.clicked.connect(self.reset_mappings)
        
        self.btn_save = QPushButton("Зберегти зміни")
        self.btn_save.setObjectName("SaveBtn")
        self.btn_save.clicked.connect(self.save_settings)
        
        bottom_layout.addWidget(self.btn_reset)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btn_save)
        
        main_layout.addLayout(bottom_layout)

    def init_hotkeys_tab(self):
        layout = QVBoxLayout(self.tab_hotkeys)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Autorun Checkbox
        self.chk_autorun = QCheckBox("Запускати разом з Windows")
        self.chk_autorun.setChecked(self.config.settings.get("autorun", True))
        layout.addWidget(self.chk_autorun)

        # Select modified text Checkbox
        self.chk_select_after_replace = QCheckBox("Виділяти виправлений текст після конвертації")
        self.chk_select_after_replace.setChecked(self.config.settings.get("select_after_replace", True))
        layout.addWidget(self.chk_select_after_replace)

        # Auto switch layout Checkbox
        self.chk_auto_switch = QCheckBox("Автоматично змінювати мову введення в системі після конвертації")
        self.chk_auto_switch.setChecked(self.config.settings.get("auto_switch_layout", True))
        layout.addWidget(self.chk_auto_switch)

        # Divider line
        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setStyleSheet("background-color: #232329;")
        layout.addWidget(line1)

        # Popup Duration Slider
        duration_layout = QHBoxLayout()
        duration_label = QLabel("<b>Тривалість відображення попапу (секунд):</b>")
        self.spin_popup_duration = QSpinBox()
        self.spin_popup_duration.setRange(1, 20)
        self.spin_popup_duration.setFixedWidth(80)
        self.spin_popup_duration.setValue(self.config.settings.get("popup_duration", 5))
        duration_layout.addWidget(duration_label)
        duration_layout.addWidget(self.spin_popup_duration)
        duration_layout.addStretch()
        layout.addLayout(duration_layout)

        # Divider line
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setStyleSheet("background-color: #232329;")
        layout.addWidget(line2)

        # Replace Hotkey section
        layout.addWidget(QLabel("<b>Гаряча клавіша: Виправлення тексту на місці</b><br>Виділіть текст та натисніть комбінацію клавіш, щоб конвертувати його прямо у редакторі"))
        self.edit_hk_replace = KeySequenceEdit(self.config.get_hotkey_replace(), self.tab_hotkeys)
        layout.addWidget(self.edit_hk_replace)

        # Popup Hotkey section
        layout.addWidget(QLabel("<b>Гаряча клавіша: Переклад у спливаючому вікні</b><br>Виділіть текст та натисніть комбінацію, щоб побачити правильний варіант біля курсора"))
        self.edit_hk_popup = KeySequenceEdit(self.config.get_hotkey_popup(), self.tab_hotkeys)
        layout.addWidget(self.edit_hk_popup)

        # Case Hotkey section
        layout.addWidget(QLabel("<b>Гаряча клавіша: Циклічна зміна регістру (Gboard style)</b><br>Виділіть текст та натисніть комбінацію, щоб перемикати регістр: Кожне Слово Велике -> ВСІ ВЕЛИКІ -> всі малі"))
        self.edit_hk_case = KeySequenceEdit(self.config.get_hotkey_case(), self.tab_hotkeys)
        layout.addWidget(self.edit_hk_case)

        # Instructions / Help
        help_lbl = QLabel(
            "💡 <b>Інструкція щодо гарячих клавіш:</b><br>"
            "1. Клікніть мишкою всередині поля введення гарячої клавіші.<br>"
            "2. Натисніть нову комбінацію клавіш на клавіатурі (наприклад, CTRL + SHIFT + Z).<br>"
            "3. Натисніть кнопку 'Зберегти зміни' внизу вікна, щоб застосувати налаштування."
        )
        help_lbl.setStyleSheet("color: #888888; line-height: 1.4; background-color: rgba(255, 255, 255, 5); border-radius: 8px; padding: 12px;")
        layout.addWidget(help_lbl)
        layout.addStretch()

    def init_mappings_tab(self):
        self.mappings_layout = QVBoxLayout(self.tab_mappings)
        self.mappings_layout.setContentsMargins(15, 15, 15, 15)
        self.mappings_layout.setSpacing(10)

        # Top Control Layout
        controls_layout = QHBoxLayout()
        self.chk_shift = QCheckBox("Режим SHIFT (налаштування великих літер та спецсимволів ;:?@ тощо)")
        self.chk_shift.stateChanged.connect(self.on_shift_mode_changed)
        controls_layout.addWidget(self.chk_shift)
        controls_layout.addStretch()
        
        self.mappings_layout.addLayout(controls_layout)

        # Help Instructions
        self.lbl_editor_status = QLabel("👉 <b>Інструкція:</b> Клікніть по будь-якій клавіші на клавіатурі (вона підсвітиться), а потім натисніть відповідну клавішу на своїй <b>фізичній клавіатурі</b>.")
        self.lbl_editor_status.setStyleSheet("color: #60A5FA; font-size: 13px; background-color: rgba(59, 130, 246, 20); padding: 10px; border-radius: 6px; font-weight: bold;")
        self.mappings_layout.addWidget(self.lbl_editor_status)

        # 1. English Keyboard Grid Wrapper
        self.en_kb_container = QWidget()
        self.en_kb_layout = QVBoxLayout(self.en_kb_container)
        self.en_kb_layout.setContentsMargins(0, 0, 0, 0)
        self.en_kb_layout.setSpacing(5)
        
        self.mappings_layout.addWidget(QLabel("<b>АНГЛІЙСЬКА КЛАВІАТУРА (Переклад в Українську)</b>"))
        self.mappings_layout.addWidget(self.en_kb_container)

        # Divider line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #232329;")
        self.mappings_layout.addWidget(line)

        # 2. Ukrainian Keyboard Grid Wrapper
        self.ua_kb_container = QWidget()
        self.ua_kb_layout = QVBoxLayout(self.ua_kb_container)
        self.ua_kb_layout.setContentsMargins(0, 0, 0, 0)
        self.ua_kb_layout.setSpacing(5)
        
        self.mappings_layout.addWidget(QLabel("<b>УКРАЇНСЬКА КЛАВІАТУРА (Переклад в Англійську)</b>"))
        self.mappings_layout.addWidget(self.ua_kb_container)

        # Draw keyboards
        self.draw_keyboards()

    def get_helper_style(self):
        return """
            QPushButton:disabled {
                background-color: #121214;
                color: #6B7280;
                border: 1px solid #232329;
                border-radius: 8px;
                font-weight: bold;
                font-size: 11px;
                text-align: center;
            }
        """

    # Key sizes and helper (disabled) keys for both visual keyboards
    KB_LAYOUTS = {
        'en': {
            "key_h": 48, "key_w": 54, "wide_w": 81,
            "left": {1: ("Tab ↹", 81), 2: ("Caps Lock", 94), 3: ("Shift ⇧", 121)},
            "right": {0: ("← Backspace", 108), 2: ("Enter ↵", 126), 3: ("Shift ⇧", 157)},
        },
        'ua': {
            "key_h": 42, "key_w": 48, "wide_w": 72,
            "left": {1: ("Tab ↹", 72), 2: ("Caps Lock", 84), 3: ("Shift ⇧", 108)},
            "right": {0: ("← Backspace", 84), 2: ("Enter ↵", 98), 3: ("Shift ⇧", 123)},
        },
    }

    def _make_helper_key(self, label, width, height):
        btn = QPushButton(label)
        btn.setFixedSize(width, height)
        btn.setEnabled(False)
        btn.setStyleSheet(self.get_helper_style())
        return btn

    def _draw_keyboard(self, target_layout, rows_data, active_map, kb_id):
        cfg = self.KB_LAYOUTS[kb_id]
        buttons = {}
        for row_idx, row in enumerate(rows_data):
            row_layout = QHBoxLayout()
            row_layout.setSpacing(4)
            row_layout.addStretch()

            if row_idx in cfg["left"]:
                label, width = cfg["left"][row_idx]
                row_layout.addWidget(self._make_helper_key(label, width, cfg["key_h"]))

            for col_idx, char in enumerate(row):
                is_wide = (row_idx == 1 and col_idx == len(row) - 1)
                btn = QPushButton()
                btn.setFixedSize(cfg["wide_w"] if is_wide else cfg["key_w"], cfg["key_h"])
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setText(f"{char}\n→ {active_map.get(char, '')}")
                btn.setStyleSheet(KEY_BTN_STYLE.format(color=KEY_COLORS[kb_id]))
                btn.clicked.connect(lambda checked, k=kb_id, c=char, b=btn: self.on_key_clicked(k, c, b))
                row_layout.addWidget(btn)
                buttons[char] = btn

            if row_idx in cfg["right"]:
                label, width = cfg["right"][row_idx]
                row_layout.addWidget(self._make_helper_key(label, width, cfg["key_h"]))

            row_layout.addStretch()
            target_layout.addLayout(row_layout)
        return buttons

    def draw_keyboards(self):
        self.clear_layout(self.en_kb_layout)
        self.clear_layout(self.ua_kb_layout)

        is_shift = self.chk_shift.isChecked()
        en_rows_data = EN_SHIFT_ROWS if is_shift else EN_ROWS
        ua_rows_data = UA_SHIFT_ROWS if is_shift else UA_ROWS

        active_map_en = self.local_mappings_shift if is_shift else self.local_mappings
        active_map_ua = self.local_mappings_ua_to_en_shift if is_shift else self.local_mappings_ua_to_en

        self.en_buttons = self._draw_keyboard(self.en_kb_layout, en_rows_data, active_map_en, 'en')
        self.ua_buttons = self._draw_keyboard(self.ua_kb_layout, ua_rows_data, active_map_ua, 'ua')

    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
                elif child.layout():
                    self.clear_layout(child.layout())

    def reset_active_edit_button(self):
        if self.active_edit_btn:
            is_shift = self.chk_shift.isChecked()
            active_map = self.local_mappings_shift if is_shift else self.local_mappings
            if self.active_edit_kb == 'ua':
                active_map = self.local_mappings_ua_to_en_shift if is_shift else self.local_mappings_ua_to_en

            mapped_char = active_map.get(self.active_edit_char, "")
            self.active_edit_btn.setText(f"{self.active_edit_char}\n→ {mapped_char}")
            self.active_edit_btn.setStyleSheet(KEY_BTN_STYLE.format(color=KEY_COLORS[self.active_edit_kb]))

    def _clear_active_edit(self):
        self.active_edit_kb = None
        self.active_edit_char = None
        self.active_edit_btn = None
        self.lbl_editor_status.setText(EDITOR_HINT_DEFAULT)

    def on_key_clicked(self, kb_id, char, button):
        self.reset_active_edit_button()

        self.active_edit_kb = kb_id
        self.active_edit_char = char
        self.active_edit_btn = button

        button.setText(f"{char}\n→ ?")
        button.setStyleSheet(ACTIVE_KEY_BTN_STYLE)

        self.lbl_editor_status.setText(f"🎯 <b>Мапування клавіші '{char}':</b> Натисніть нову кнопку на фізичній клавіатурі (або ESC для скасування).")
        self.setFocus()

    def keyPressEvent(self, event):
        if self.active_edit_kb is not None:
            if event.key() == Qt.Key.Key_Escape:
                self.reset_active_edit_button()
                self._clear_active_edit()
                event.accept()
                return

            typed_char = event.text()
            if typed_char and len(typed_char) == 1:
                is_shift = self.chk_shift.isChecked()
                char_to_map = self.active_edit_char
                
                if self.active_edit_kb == 'en':
                    # Update local EN -> UA mappings
                    if is_shift:
                        self.local_mappings_shift[char_to_map] = typed_char
                    else:
                        self.local_mappings[char_to_map] = typed_char
                        if char_to_map.isalpha():
                            self.local_mappings_shift[char_to_map.upper()] = typed_char.upper()
                            logging.info(f"Синхронізовано Shift літери: {char_to_map.upper()} -> {typed_char.upper()}")
                else:
                    # Update local UA -> EN mappings
                    if is_shift:
                        self.local_mappings_ua_to_en_shift[char_to_map] = typed_char
                    else:
                        self.local_mappings_ua_to_en[char_to_map] = typed_char
                        if char_to_map.isalpha():
                            self.local_mappings_ua_to_en_shift[char_to_map.upper()] = typed_char.upper()
                            logging.info(f"Синхронізовано Shift літери (UA->EN): {char_to_map.upper()} -> {typed_char.upper()}")
                
                logging.info(f"Прив'язано: {char_to_map} -> {typed_char} ({self.active_edit_kb.upper()} layout, Shift={is_shift})")

                self._clear_active_edit()
                self.draw_keyboards()
                event.accept()
                return

        super().keyPressEvent(event)

    def on_shift_mode_changed(self, state):
        self.reset_active_edit_button()
        self._clear_active_edit()
        self.draw_keyboards()

    def sync_from_config(self):
        """Sync UI checkboxes and spinbox with current config settings (e.g. if toggled via tray menu)."""
        self.chk_autorun.setChecked(self.config.settings.get("autorun", True))
        self.chk_select_after_replace.setChecked(self.config.settings.get("select_after_replace", True))
        self.chk_auto_switch.setChecked(self.config.settings.get("auto_switch_layout", True))
        self.spin_popup_duration.setValue(self.config.settings.get("popup_duration", 5))

    def save_settings(self):
        # 1. Save Hotkeys
        self.config.set_hotkey_replace(
            self.edit_hk_replace.recorded_modifiers,
            self.edit_hk_replace.recorded_vk,
            self.edit_hk_replace.recorded_display
        )
        self.config.set_hotkey_popup(
            self.edit_hk_popup.recorded_modifiers,
            self.edit_hk_popup.recorded_vk,
            self.edit_hk_popup.recorded_display
        )
        self.config.set_hotkey_case(
            self.edit_hk_case.recorded_modifiers,
            self.edit_hk_case.recorded_vk,
            self.edit_hk_case.recorded_display
        )
        
        # 2. Save options
        self.config.settings["popup_duration"] = self.spin_popup_duration.value()
        self.config.settings["autorun"] = self.chk_autorun.isChecked()
        self.config.settings["select_after_replace"] = self.chk_select_after_replace.isChecked()
        self.config.settings["auto_switch_layout"] = self.chk_auto_switch.isChecked()
        
        # 3. Save Mappings Overrides (EN -> UA)
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
                
        # 4. Save Mappings Overrides (UA -> EN)
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
            
        QMessageBox.information(self, "Збережено", "Налаштування успішно збережено! Автозапуск, гарячі клавіші та розкладку оновлено.")
        self.close()

    def reset_mappings(self):
        reply = QMessageBox.question(
            self, "Скинути налаштування", 
            "Ви впевнені, що хочете повернути стандартні налаштування розкладки клавіш?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.config.reset_mappings()
            self.local_mappings, self.local_mappings_shift, self.local_mappings_ua_to_en, self.local_mappings_ua_to_en_shift = self.config.get_mappings()
            self.draw_keyboards()
            QMessageBox.information(self, "Скинуто", "Розкладку скинуто до стандартної (натисніть 'Зберегти зміни' для застосування).")

    def init_feedback_tab(self):
        layout = QVBoxLayout(self.tab_feedback)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Icon/Illustration
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setText("💬")
        icon_label.setStyleSheet("font-size: 72px; margin-bottom: 10px;")
        layout.addWidget(icon_label)

        # Heading
        heading = QLabel("Допоможіть нам покращити LayoutCorrector!")
        heading.setFont(QFont("Google Sans", 16, QFont.Weight.Bold))
        heading.setStyleSheet("color: #3B82F6;")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(heading)

        # Description
        description = QLabel(
            "Ваш відгук є надзвичайно важливим для розвитку проекту.\n"
            "Знайшли помилку? Маєте пропозицію щодо нових функцій?\n"
            "Будь ласка, поділіться своєю думкою через нашу швидку гугл-форму."
        )
        description.setFont(QFont("Segoe UI", 11))
        description.setStyleSheet("color: #9CA3AF; line-height: 1.6;")
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(description)

        # Extra spacing
        layout.addSpacing(10)

        # Feedback Button
        btn_feedback = QPushButton("Залишити зворотній зв'язок")
        btn_feedback.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_feedback.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3B82F6, stop:1 #2563EB);
                color: #FFFFFF;
                border: none;
                border-radius: 12px;
                padding: 14px 28px;
                font-size: 14px;
                font-weight: bold;
                min-width: 250px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #60A5FA, stop:1 #3B82F6);
                border: none;
            }
            QPushButton:pressed {
                background: #1D4ED8;
            }
        """)
        btn_feedback.clicked.connect(self.open_feedback_link)
        layout.addWidget(btn_feedback)
        
        layout.addStretch()

    def open_feedback_link(self):
        import webbrowser
        webbrowser.open(FEEDBACK_URL)
