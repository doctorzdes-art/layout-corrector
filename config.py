import os
import json
import logging
import re
import sys
import winreg
from logging.handlers import RotatingFileHandler

APP_VERSION = "1.14"

FEEDBACK_URL = "https://forms.gle/VQy4R6t1m7qyAhfz5"
UPDATE_FOLDER_URL = "https://drive.google.com/drive/folders/1LaJfRgYqFViFj--gEk_rvvvVS399sKZF"

def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

APP_DIR = get_app_dir()

# Log lives in %LOCALAPPDATA% so the app also works from read-only folders (e.g. Program Files)
LOG_DIR = os.path.join(os.getenv("LOCALAPPDATA") or APP_DIR, "LayoutCorrector")
LOG_FILE = os.path.join(LOG_DIR, "app.log")

def _setup_logging():
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=1, encoding="utf-8")
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.basicConfig(level=logging.INFO, handlers=[handler])
    except Exception:
        # Never crash the app because the log file is unavailable
        logging.basicConfig(level=logging.INFO)

_setup_logging()

# Standard default configurations
DEFAULT_HOTKEY_REPLACE = {
    "modifiers": ["ctrl", "alt"],
    "vk": 90, # 'Z' key
    "display": "CTRL + ALT + Z"
}

DEFAULT_HOTKEY_POPUP = {
    "modifiers": ["ctrl", "alt"],
    "vk": 88, # 'X' key
    "display": "CTRL + ALT + X"
}

DEFAULT_HOTKEY_CASE = {
    "modifiers": ["ctrl", "alt"],
    "vk": 67, # 'C' key
    "display": "CTRL + ALT + C"
}

# Windows Virtual Key codes to friendly names
VK_TO_NAME = {
    8: "BACKSPACE", 9: "TAB", 13: "ENTER", 19: "PAUSE", 27: "ESC", 32: "SPACE",
    45: "INSERT", 46: "DELETE",
    48: "0", 49: "1", 50: "2", 51: "3", 52: "4", 53: "5", 54: "6", 55: "7", 56: "8", 57: "9",
    65: "A", 66: "B", 67: "C", 68: "D", 69: "E", 70: "F", 71: "G", 72: "H", 73: "I", 74: "J",
    75: "K", 76: "L", 77: "M", 78: "N", 79: "O", 80: "P", 81: "Q", 82: "R", 83: "S", 84: "T",
    85: "U", 86: "V", 87: "W", 88: "X", 89: "Y", 90: "Z",
    112: "F1", 113: "F2", 114: "F3", 115: "F4", 116: "F5", 117: "F6",
    118: "F7", 119: "F8", 120: "F9", 121: "F10", 122: "F11", 123: "F12",
    186: ";", 187: "=", 188: ",", 189: "-", 190: ".", 191: "/", 192: "`",
    219: "[", 220: "\\", 221: "]", 222: "'"
}

NAME_TO_VK = {v: k for k, v in VK_TO_NAME.items()}

# Default mappings
DEFAULT_EN_TO_UA = {
    "`": "'", "1": "1", "2": "2", "3": "3", "4": "4", "5": "5", "6": "6", "7": "7", "8": "8", "9": "9", "0": "0", "-": "-", "=": "=",
    "q": "й", "w": "ц", "e": "у", "r": "к", "t": "е", "y": "н", "u": "г", "i": "ш", "o": "щ", "p": "з", "[": "х", "]": "ї", "\\": "\\",
    "a": "ф", "s": "і", "d": "в", "f": "а", "g": "п", "h": "р", "j": "о", "k": "л", "l": "д", ";": "ж", "'": "є",
    "z": "я", "x": "ч", "c": "с", "v": "м", "b": "и", "n": "т", "m": "ь", ",": "б", ".": "ю", "/": "."
}

DEFAULT_EN_TO_UA_SHIFT = {
    "~": "\"", "!": "!", "@": "\"", "#": "№", "$": ";", "%": "%", "^": ":", "&": "?", "*": "*", "(": "(", ")": ")", "_": "_", "+": "+",
    "Q": "Й", "W": "Ц", "E": "У", "R": "К", "T": "Е", "Y": "Н", "U": "Г", "I": "Ш", "O": "Щ", "P": "З", "{": "Х", "}": "Ї", "|": "/",
    "A": "Ф", "S": "І", "D": "В", "F": "А", "G": "П", "H": "Р", "J": "О", "K": "Л", "L": "Д", ":": "Ж", "\"": "Є",
    "Z": "Я", "X": "Ч", "C": "С", "V": "М", "B": "И", "N": "Т", "M": "Ь", "<": "Б", ">": "Ю", "?": ","
}

def _version_tuple(ver_str):
    try:
        return tuple(map(int, ver_str.split(".")))
    except (ValueError, AttributeError):
        return None

def _version_from_filename(path):
    match = re.search(r'v?\.?\s*(\d+(?:\.\d+)+)', os.path.basename(path), re.IGNORECASE)
    return _version_tuple(match.group(1)) if match else None

def set_windows_autorun(enabled):
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0,
                             winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE)
        if enabled:
            if getattr(sys, 'frozen', False):
                app_path = f'"{sys.executable}"'
                # Don't clobber the entry if it points to an existing NEWER version:
                # the latest installed version must stay in autorun
                try:
                    existing, _ = winreg.QueryValueEx(key, "LayoutCorrector")
                except FileNotFoundError:
                    existing = None
                if existing:
                    existing_path = existing.strip().strip('"')
                    if '"' not in existing_path and os.path.exists(existing_path):
                        existing_ver = _version_from_filename(existing_path)
                        my_ver = _version_tuple(APP_VERSION)
                        if existing_ver and my_ver and existing_ver > my_ver:
                            logging.info(f"Автозапуск не змінено: там уже новіша версія ({existing_path})")
                            winreg.CloseKey(key)
                            return
            else:
                script_path = os.path.abspath(sys.argv[0])
                if script_path.endswith("main.py"):
                    pythonw_path = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
                    app_path = f'"{pythonw_path}" "{script_path}"'
                else:
                    app_path = f'"{sys.executable}"'
            winreg.SetValueEx(key, "LayoutCorrector", 0, winreg.REG_SZ, app_path)
            logging.info(f"Додано в автозапуск реєстру: {app_path}")
        else:
            try:
                winreg.DeleteValue(key, "LayoutCorrector")
                logging.info("Вилучено з автозапуску реєстру.")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception as e:
        logging.error(f"Помилка налаштування автозапуску: {e}")

class AppConfig:
    def __init__(self):
        self.filepath = os.path.join(os.path.expanduser("~"), ".layout_corrector_settings.json")
        self.settings = {
            "hotkey_replace": DEFAULT_HOTKEY_REPLACE.copy(),
            "hotkey_popup": DEFAULT_HOTKEY_POPUP.copy(),
            "hotkey_case": DEFAULT_HOTKEY_CASE.copy(),
            "popup_duration": 5,
            "autorun": True,
            "select_after_replace": True,
            "auto_switch_layout": True,
            "en_to_ua_overrides": {},
            "en_to_ua_shift_overrides": {},
            "ua_to_en_overrides": {},
            "ua_to_en_shift_overrides": {}
        }
        self.load()

    def _migrate_hotkey(self, old_val):
        try:
            parts = old_val.lower().split("+")
            mods = [p.replace("<", "").replace(">", "") for p in parts[:-1]]
            key_char = parts[-1].replace("<", "").replace(">", "")
            vk = ord(key_char.upper()) if len(key_char) == 1 else NAME_TO_VK.get(key_char.upper(), 0)
            display = " + ".join([m.upper() for m in mods] + [key_char.upper()])
            return {
                "modifiers": mods,
                "vk": vk,
                "display": display
            }
        except Exception as e:
            logging.error(f"Failed to migrate hotkey string '{old_val}': {e}")
            return None

    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if not isinstance(loaded, dict):
                    raise ValueError("Settings root must be a JSON object")

                # Safe load hotkeys with type validation
                for key in ["hotkey_replace", "hotkey_popup", "hotkey_case"]:
                    if key in loaded:
                        val = loaded[key]
                        if isinstance(val, dict):
                            mods = val.get("modifiers")
                            vk = val.get("vk")
                            display = val.get("display")
                            if (
                                isinstance(mods, list)
                                and all(isinstance(m, str) for m in mods)
                                and isinstance(vk, int) and not isinstance(vk, bool)
                                and isinstance(display, str)
                            ):
                                self.settings[key] = {
                                    "modifiers": mods,
                                    "vk": vk,
                                    "display": display,
                                }
                        elif isinstance(val, str) and key != "hotkey_case":
                            migrated = self._migrate_hotkey(val)
                            if migrated:
                                self.settings[key] = migrated

                raw_duration = loaded.get("popup_duration", 5)
                if isinstance(raw_duration, int) and not isinstance(raw_duration, bool):
                    self.settings["popup_duration"] = max(1, min(20, raw_duration))
                else:
                    self.settings["popup_duration"] = 5

                for bool_key in ("autorun", "select_after_replace", "auto_switch_layout"):
                    raw_bool = loaded.get(bool_key, True)
                    self.settings[bool_key] = raw_bool if isinstance(raw_bool, bool) else True

                raw_last_check = loaded.get("last_scheduled_update_check", "")
                if isinstance(raw_last_check, str):
                    self.settings["last_scheduled_update_check"] = raw_last_check

                # Safe load overrides (must be dict of str -> str)
                for ov_key in (
                    "en_to_ua_overrides",
                    "en_to_ua_shift_overrides",
                    "ua_to_en_overrides",
                    "ua_to_en_shift_overrides",
                ):
                    raw_ov = loaded.get(ov_key, {})
                    if isinstance(raw_ov, dict):
                        self.settings[ov_key] = {
                            k: v for k, v in raw_ov.items()
                            if isinstance(k, str) and isinstance(v, str)
                        }
                    else:
                        self.settings[ov_key] = {}

                logging.info("Налаштування успішно завантажено.")
            except Exception as e:
                logging.error(f"Помилка завантаження налаштувань: {e}")
                
    def save(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=4)
            logging.info("Налаштування успішно збережено.")
            
            # Sync autorun in registry
            set_windows_autorun(self.settings.get("autorun", True))
        except Exception as e:
            logging.error(f"Помилка збереження налаштувань: {e}")

    def get_hotkey_replace(self):
        return self.settings.get("hotkey_replace", DEFAULT_HOTKEY_REPLACE)

    def set_hotkey_replace(self, modifiers, vk, display):
        self.settings["hotkey_replace"] = {
            "modifiers": modifiers,
            "vk": vk,
            "display": display
        }
        self.save()

    def get_hotkey_popup(self):
        return self.settings.get("hotkey_popup", DEFAULT_HOTKEY_POPUP)

    def set_hotkey_popup(self, modifiers, vk, display):
        self.settings["hotkey_popup"] = {
            "modifiers": modifiers,
            "vk": vk,
            "display": display
        }
        self.save()

    def get_hotkey_case(self):
        return self.settings.get("hotkey_case", DEFAULT_HOTKEY_CASE)

    def set_hotkey_case(self, modifiers, vk, display):
        self.settings["hotkey_case"] = {
            "modifiers": modifiers,
            "vk": vk,
            "display": display
        }
        self.save()

    def get_mappings(self):
        en_to_ua = DEFAULT_EN_TO_UA.copy()
        en_to_ua_shift = DEFAULT_EN_TO_UA_SHIFT.copy()
        
        # Apply standard EN -> UA overrides
        overrides = self.settings.get("en_to_ua_overrides", {})
        for k, v in overrides.items():
            en_to_ua[k] = v
            
        shift_overrides = self.settings.get("en_to_ua_shift_overrides", {})
        for k, v in shift_overrides.items():
            en_to_ua_shift[k] = v
            
        # Build reverse mappings (default UA -> EN)
        ua_to_en = {}
        for k, v in en_to_ua.items():
            if v not in ua_to_en:
                ua_to_en[v] = k
        ua_to_en_shift = {}
        for k, v in en_to_ua_shift.items():
            if v not in ua_to_en_shift:
                ua_to_en_shift[v] = k
                
        # Apply custom UA -> EN overrides
        ua_overrides = self.settings.get("ua_to_en_overrides", {})
        for k, v in ua_overrides.items():
            ua_to_en[k] = v
            
        ua_shift_overrides = self.settings.get("ua_to_en_shift_overrides", {})
        for k, v in ua_shift_overrides.items():
            ua_to_en_shift[k] = v
            
        return en_to_ua, en_to_ua_shift, ua_to_en, ua_to_en_shift

    def set_mapping_override(self, en_char, ua_char, is_shift=False):
        if is_shift:
            overrides = self.settings.get("en_to_ua_shift_overrides", {})
            overrides[en_char] = ua_char
            self.settings["en_to_ua_shift_overrides"] = overrides
        else:
            overrides = self.settings.get("en_to_ua_overrides", {})
            overrides[en_char] = ua_char
            self.settings["en_to_ua_overrides"] = overrides
        self.save()

    def set_ua_to_en_override(self, ua_char, en_char, is_shift=False):
        if is_shift:
            overrides = self.settings.get("ua_to_en_shift_overrides", {})
            overrides[ua_char] = en_char
            self.settings["ua_to_en_shift_overrides"] = overrides
        else:
            overrides = self.settings.get("ua_to_en_overrides", {})
            overrides[ua_char] = en_char
            self.settings["ua_to_en_overrides"] = overrides
        self.save()

    def reset_mappings(self):
        self.settings["en_to_ua_overrides"] = {}
        self.settings["en_to_ua_shift_overrides"] = {}
        self.settings["ua_to_en_overrides"] = {}
        self.settings["ua_to_en_shift_overrides"] = {}
        self.save()
