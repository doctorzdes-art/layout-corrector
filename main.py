import sys
import os
import datetime
import html
import re

# Redirect stdout/stderr in windowless mode to prevent crashes
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

import logging
import pyperclip
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtCore import Qt, QObject, pyqtSlot, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont

# Importing config also sets up logging (rotating file in %LOCALAPPDATA%)
from config import (
    AppConfig, set_windows_autorun, get_resource_path,
    APP_VERSION, FEEDBACK_URL, UPDATE_FOLDER_URL
)
from translator import LayoutTranslator
from hotkey_listener import HotkeyListener
from ui_settings import SettingsWindow
from ui_popup import TextPopup

def exception_hook(exctype, value, traceback):
    logging.error("Uncaught exception:", exc_info=(exctype, value, traceback))
    sys.__excepthook__(exctype, value, traceback)

sys.excepthook = exception_hook

class AppController(QObject):
    update_available_signal = pyqtSignal(str)

    def __init__(self, app):
        super().__init__()
        logging.info("Initializing AppController...")
        self.app = app
        self.config = AppConfig()
        
        # Sync Windows autorun on startup
        set_windows_autorun(self.config.settings.get("autorun", True))
        
        self.translator = LayoutTranslator(self.config)
        self.listener = HotkeyListener(self.config)
        self.settings_window = None
        self.popups = [] 
        self.is_active = True

        # Connect signals
        self.listener.signals.replace_trigger.connect(self.on_replace_triggered)
        self.listener.signals.popup_trigger.connect(self.on_popup_triggered)
        self.listener.signals.case_trigger.connect(self.on_case_triggered)

        self.logo_path = get_resource_path("logo.png")
        
        # Create Tray Icon
        self.tray_icon = QSystemTrayIcon(self)
        logo_icon = QIcon(self.logo_path)
        if not logo_icon.isNull():
            self.tray_icon.setIcon(logo_icon)
        else:
            self.tray_icon.setIcon(self.create_tray_icon())
        self.tray_icon.setToolTip("Автоматичне виправлення розкладки (Активно)")
        
        # Build Tray Menu
        self.tray_menu = QMenu()
        
        self.act_toggle = self.tray_menu.addAction("Увімкнено")
        self.act_toggle.setCheckable(True)
        self.act_toggle.setChecked(True)
        self.act_toggle.triggered.connect(self.toggle_active)
        
        self.act_select = self.tray_menu.addAction("Виділяти виправлений текст")
        self.act_select.setCheckable(True)
        self.act_select.setChecked(self.config.settings.get("select_after_replace", True))
        self.act_select.triggered.connect(self.toggle_select_after_replace)
        
        self.act_auto_switch = self.tray_menu.addAction("Змінювати мову введення")
        self.act_auto_switch.setCheckable(True)
        self.act_auto_switch.setChecked(self.config.settings.get("auto_switch_layout", True))
        self.act_auto_switch.triggered.connect(self.toggle_auto_switch_layout)
        
        self.tray_menu.addSeparator()
        
        self.act_settings = self.tray_menu.addAction("Налаштування...")
        self.act_settings.triggered.connect(self.open_settings)
        
        self.act_feedback = self.tray_menu.addAction("Зворотній зв'язок...")
        self.act_feedback.triggered.connect(self.open_feedback)
        
        self.tray_menu.addSeparator()
        
        self.act_exit = self.tray_menu.addAction("Вихід")
        self.act_exit.triggered.connect(self.quit_app)
        
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        
        self.tray_icon.show()
        logging.info("Tray icon displayed.")
        
        # Start background hotkey listener
        self.listener.start()

        # Connect update signal and start timer
        self.update_available_signal.connect(self.show_update_dialog)
        
        # Setup update check timer (10 mins)
        from PyQt6.QtCore import QTimer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.check_scheduled_update)
        self.update_timer.start(600000)
        
        # Trigger initial check 5 seconds after startup
        QTimer.singleShot(5000, self.run_update_check)

    def create_tray_icon(self):
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor("transparent"))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Outer circle
        painter.setBrush(QColor("#00ADB5"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, 28, 28)
        
        # Keyboard symbol
        painter.setPen(QColor("#FFFFFF"))
        font = QFont("Segoe UI", 16, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "⌨")
        painter.end()
        
        return QIcon(pixmap)

    def toggle_active(self, checked):
        self.is_active = checked
        if self.is_active:
            self.listener.start()
            self.tray_icon.setToolTip("Автоматичне виправлення розкладки (Активно)")
            logging.info("Application enabled.")
        else:
            self.listener.stop()
            self.tray_icon.setToolTip("Автоматичне виправлення розкладки (Вимкнено)")
            logging.info("Application disabled.")

    def toggle_select_after_replace(self, checked):
        self.config.settings["select_after_replace"] = checked
        self.config.save()
        logging.info(f"Select after replace set to: {checked}")

    def toggle_auto_switch_layout(self, checked):
        self.config.settings["auto_switch_layout"] = checked
        self.config.save()
        logging.info(f"Auto switch layout set to: {checked}")

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.open_settings()

    def open_settings(self):
        logging.info("Opening settings window...")
        if not self.settings_window:
            self.settings_window = SettingsWindow(self.config, on_saved_callback=self.on_settings_saved)
        else:
            self.settings_window.sync_from_config()
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def on_settings_saved(self):
        logging.info("Settings saved callback triggered. Reloading configs...")
        self.translator.reload()
        self.act_select.setChecked(self.config.settings.get("select_after_replace", True))
        self.act_auto_switch.setChecked(self.config.settings.get("auto_switch_layout", True))
        if self.is_active:
            self.listener.reload()

    def _get_global_capslock(self):
        import ctypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        
        fg_hwnd = user32.GetForegroundWindow()
        if fg_hwnd:
            fg_thread = user32.GetWindowThreadProcessId(fg_hwnd, None)
            current_thread = kernel32.GetCurrentThreadId()
            if fg_thread and fg_thread != current_thread:
                user32.AttachThreadInput(current_thread, fg_thread, True)
                caps = (user32.GetKeyState(0x14) & 1) != 0
                user32.AttachThreadInput(current_thread, fg_thread, False)
                return caps
        return (user32.GetKeyState(0x14) & 1) != 0

    @pyqtSlot()
    def on_replace_triggered(self):
        try:
            if not self.is_active:
                return
                
            logging.info("Replace triggered in main thread.")
            # Capture accurate Caps Lock state globally
            current_caps = self._get_global_capslock()
            
            # Grab text
            selected_text, old_clipboard = self.listener.grab_selected_text()
            
            if not selected_text:
                logging.info("No text selected to replace.")
                self.listener.restore_clipboard(old_clipboard)
                return

            # Translate (pass modifier state captured at hotkey trigger time)
            translated = self.translator.translate(
                selected_text,
                trigger_shift=self.listener.trigger_shift,
                trigger_caps=current_caps,
            )
            logging.info(f"Translated {len(selected_text)} chars.")

            # Paste back
            if translated and translated != selected_text:
                select_text = self.config.settings.get("select_after_replace", True)
                self.listener.paste_text(translated, old_clipboard, select_text=select_text)
                
                # Auto switch system keyboard layout if enabled
                if self.config.settings.get("auto_switch_layout", True):
                    source_lang = self.translator.detect_layout(selected_text)
                    target_lang = 'ua' if source_lang == 'en' else 'en'
                    self.listener.switch_system_layout(target_lang)
            else:
                self.listener.restore_clipboard(old_clipboard)
        finally:
            self.listener.is_processing = False

    @pyqtSlot()
    def on_popup_triggered(self):
        try:
            if not self.is_active:
                return

            logging.info("Popup triggered in main thread.")
            # Capture accurate Caps Lock state globally
            current_caps = self._get_global_capslock()
            
            # Grab text
            selected_text, old_clipboard = self.listener.grab_selected_text()

            # Restore clipboard immediately
            self.listener.restore_clipboard(old_clipboard)

            if not selected_text:
                logging.info("No text selected to display in popup.")
                return

            # Translate
            translated = self.translator.translate(
                selected_text,
                trigger_shift=self.listener.trigger_shift,
                trigger_caps=current_caps,
            )
            logging.info(f"Translated popup text ({len(selected_text)} chars).")
            
            if translated and translated != selected_text:
                self.popups = [p for p in self.popups if p.isVisible()]
                
                duration = self.config.settings.get("popup_duration", 5)
                popup = TextPopup(translated, duration=duration)
                popup.show()
                self.popups.append(popup)
                logging.info("Popup window shown near cursor.")
        finally:
            self.listener.is_processing = False

    @pyqtSlot()
    def on_case_triggered(self):
        try:
            if not self.is_active:
                return
                
            logging.info("Case toggle triggered.")
            selected_text, old_clipboard = self.listener.grab_selected_text()
            if not selected_text:
                logging.info("No text selected to toggle case.")
                self.listener.restore_clipboard(old_clipboard)
                return
                
            def custom_title(s):
                # Gboard style: capitalize first letter of each word across spaces, tabs, and newlines
                tokens = re.split(r'(\s+)', s)
                return "".join(
                    t[0].upper() + t[1:].lower() if t and not t.isspace() else t
                    for t in tokens
                )
                
            lower_version = selected_text.lower()
            upper_version = selected_text.upper()
            title_version = custom_title(selected_text)
            
            # Stateless cycle: Title -> UPPER -> lower -> Title
            if selected_text == title_version:
                new_text = upper_version
            elif selected_text == upper_version:
                new_text = lower_version
            else:
                new_text = title_version
                
            logging.info(f"Toggled case ({len(selected_text)} chars).")
            if new_text != selected_text:
                select_text = self.config.settings.get("select_after_replace", True)
                self.listener.paste_text(new_text, old_clipboard, select_text=select_text)
            else:
                self.listener.restore_clipboard(old_clipboard)
        finally:
            self.listener.is_processing = False

    def quit_app(self):
        logging.info("Quitting application...")
        self.listener.stop()
        self.tray_icon.hide()
        self.app.quit()

    def open_feedback(self):
        import webbrowser
        webbrowser.open(FEEDBACK_URL)

    def show_update_dialog(self, new_version):
        from PyQt6.QtWidgets import QMessageBox
        logging.info(f"Showing update dialog for version {new_version}")
        
        msg_box = QMessageBox()
        logo_icon = QIcon(self.logo_path)
        if not logo_icon.isNull():
            msg_box.setWindowIcon(logo_icon)
            pixmap = QPixmap(self.logo_path)
            if not pixmap.isNull():
                msg_box.setIconPixmap(pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        
        safe_new_ver = html.escape(str(new_version))
        safe_curr_ver = html.escape(str(APP_VERSION))
        msg_box.setWindowTitle("LayoutCorrector — Доступне оновлення")
        msg_box.setText("<h3><b>Доступне оновлення LayoutCorrector</b></h3>")
        msg_box.setInformativeText(
            f"Знайдено новішу версію програми: <b>v{safe_new_ver}</b> (поточна версія: v{safe_curr_ver}).<br><br>"
            "Бажаєте відкрити папку завантаження на Google Диску, щоб завантажити оновлення?"
        )
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.Yes)
        
        # Apply dark theme styling matching the settings window
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #0F0F11;
                color: #EEEEEE;
                font-family: "Google Sans", "Segoe UI", sans-serif;
            }
            QLabel {
                color: #EEEEEE;
            }
            QPushButton {
                background-color: #1E1E22;
                color: #EEEEEE;
                border: 1px solid #3F3F46;
                border-radius: 8px;
                padding: 6px 18px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #2D2D34;
                border-color: #3B82F6;
            }
            QPushButton:default {
                background-color: #3B82F6;
                color: #FFFFFF;
                border: none;
            }
            QPushButton:default:hover {
                background-color: #60A5FA;
            }
        """)
        
        reply = msg_box.exec()
        if reply == QMessageBox.StandardButton.Yes:
            import webbrowser
            webbrowser.open(UPDATE_FOLDER_URL)

    def run_update_check(self):
        logging.info("Starting update check in background thread...")
        import threading
        thread = threading.Thread(target=self._async_update_check, daemon=True)
        thread.start()

    def _async_update_check(self):
        import gdown
        try:
            # Use skip_download=True to list the files in the public folder without downloading
            files = gdown.download_folder(url=UPDATE_FOLDER_URL, skip_download=True, quiet=True)
            if not files:
                return

            current_version = tuple(map(int, APP_VERSION.split('.')))
            
            latest_version_str = None
            latest_version = None
            
            for f in files:
                if not hasattr(f, 'path') or not f.path:
                    continue
                filename = f.path
                # Search for version pattern in filename like LayoutCorrector v1.2.exe
                match = re.search(r'v?\.?\s*(\d+(?:\.\d+)+)', filename, re.IGNORECASE)
                if match:
                    ver_str = match.group(1)
                    try:
                        ver_val = tuple(map(int, ver_str.split('.')))
                        if latest_version is None or ver_val > latest_version:
                            latest_version = ver_val
                            latest_version_str = ver_str
                    except Exception:
                        pass
            
            if latest_version and latest_version > current_version:
                logging.info(f"New version found on Google Drive: {latest_version_str}")
                self.update_available_signal.emit(latest_version_str)
            else:
                logging.info("Application is up to date.")
        except Exception as e:
            logging.error(f"Error during Google Drive update check: {e}")

    def check_scheduled_update(self):
        now = datetime.datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        last_checked_str = self.config.settings.get("last_scheduled_update_check", "")
        if last_checked_str == today_str:
            return

        should_check = (now.weekday() == 0)  # Check on Mondays at any hour
        if not should_check and last_checked_str:
            try:
                last_dt = datetime.datetime.strptime(last_checked_str, "%Y-%m-%d").date()
                if (now.date() - last_dt).days >= 7:
                    should_check = True
            except ValueError:
                should_check = True

        if should_check:
            self.config.settings["last_scheduled_update_check"] = today_str
            self.config.save()
            self.run_update_check()

_single_instance_mutex = None

def check_single_instance():
    global _single_instance_mutex
    import ctypes
    ERROR_ALREADY_EXISTS = 183
    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32
    
    mutex_name = "Local\\LayoutCorrector_SingleInstance_Mutex"
    _single_instance_mutex = kernel32.CreateMutexW(None, True, mutex_name)
    last_error = kernel32.GetLastError()
    
    if last_error == ERROR_ALREADY_EXISTS:
        if _single_instance_mutex:
            kernel32.CloseHandle(_single_instance_mutex)
            _single_instance_mutex = None
        user32.MessageBoxW(
            0,
            "LayoutCorrector вже запущений і працює в системному треї (біля годинника).",
            "Програма вже працює",
            0x00000040 | 0x00000000
        )
        sys.exit(0)

def main():
    check_single_instance()
    logging.info("--- Starting Keyboard Layout Corrector ---")
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    controller = AppController(app)
    app.aboutToQuit.connect(controller.listener.stop)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
