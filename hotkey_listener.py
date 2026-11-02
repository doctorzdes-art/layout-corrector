import time
import logging
import ctypes
import unicodedata
from ctypes import wintypes
from PyQt6.QtCore import pyqtSignal, QObject
import pyperclip

# Maximum number of Shift+Left caret steps to simulate when re-selecting pasted text
MAX_RESELECT_STEPS = 2000

# Standard Win32 HGLOBAL clipboard formats safe to snapshot & restore byte-for-byte:
# 1=CF_TEXT, 8=CF_DIB, 13=CF_UNICODETEXT, 15=CF_HDROP (files), 16=CF_LOCALE, 17=CF_DIBV5 (screenshots)
SAFE_STD_CLIPBOARD_FORMATS = {1, 8, 13, 15, 16, 17}

# Registered named clipboard formats safe to snapshot & restore byte-for-byte
SAFE_NAMED_CLIPBOARD_FORMATS = {
    "PNG",
    "JFIF",
    "GIF",
    "HTML Format",
    "Rich Text Format",
    "CF_HTML",
    "Csv",
    "Preferred DropEffect",
    "FileName",
    "FileNameW",
    "UniformResourceLocator",
    "UniformResourceLocatorW",
}

# Windows 10/11 Clipboard History & Cloud Clipboard exclusion format names
CLIPBOARD_EXCLUSION_FORMATS = (
    "ExcludeClipboardContentFromMonitorProcessing",
    "CanIncludeInClipboardHistory",
    "CanUploadToCloudClipboard",
)

kernel32_dll = ctypes.windll.kernel32
kernel32_dll.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32_dll.GlobalAlloc.restype = wintypes.HGLOBAL
kernel32_dll.GlobalFree.argtypes = [wintypes.HGLOBAL]
kernel32_dll.GlobalFree.restype = wintypes.HGLOBAL
kernel32_dll.GlobalSize.argtypes = [wintypes.HGLOBAL]
kernel32_dll.GlobalSize.restype = ctypes.c_size_t
kernel32_dll.GlobalLock.argtypes = [wintypes.HGLOBAL]
kernel32_dll.GlobalLock.restype = ctypes.c_void_p
kernel32_dll.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
kernel32_dll.GlobalUnlock.restype = wintypes.BOOL

user32_cb = ctypes.windll.user32
user32_cb.OpenClipboard.argtypes = [wintypes.HWND]
user32_cb.OpenClipboard.restype = wintypes.BOOL
user32_cb.CloseClipboard.argtypes = []
user32_cb.CloseClipboard.restype = wintypes.BOOL
user32_cb.EmptyClipboard.argtypes = []
user32_cb.EmptyClipboard.restype = wintypes.BOOL
user32_cb.EnumClipboardFormats.argtypes = [wintypes.UINT]
user32_cb.EnumClipboardFormats.restype = wintypes.UINT
user32_cb.GetClipboardData.argtypes = [wintypes.UINT]
user32_cb.GetClipboardData.restype = wintypes.HANDLE
user32_cb.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
user32_cb.SetClipboardData.restype = wintypes.HANDLE
user32_cb.GetClipboardFormatNameW.argtypes = [wintypes.UINT, wintypes.LPWSTR, ctypes.c_int]
user32_cb.GetClipboardFormatNameW.restype = ctypes.c_int
user32_cb.RegisterClipboardFormatW.argtypes = [wintypes.LPCWSTR]
user32_cb.RegisterClipboardFormatW.restype = wintypes.UINT


def _caret_steps(text):
    """
    Approximate number of Left-arrow presses needed to cross `text`.
    Combining marks, variation selectors, ZWJ emoji sequences and flag
    pairs move as a single caret step in most Windows controls.
    """
    steps = 0
    skip_next = False
    prev_was_ri = False
    for ch in text:
        if skip_next:
            skip_next = False
            prev_was_ri = False
            continue
        cp = ord(ch)
        if cp == 0x200D:  # zero-width joiner glues prev and next chars into one glyph
            skip_next = True
            continue
        if 0xFE00 <= cp <= 0xFE0F or unicodedata.combining(ch):
            continue
        if 0x1F1E6 <= cp <= 0x1F1FF:  # regional indicators: flags come in pairs
            if prev_was_ri:
                prev_was_ri = False
                continue
            prev_was_ri = True
        else:
            prev_was_ri = False
        steps += 1
    return steps


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_size_t),
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_size_t),
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_ulong),
        ("wParamL", ctypes.c_ushort),
        ("wParamH", ctypes.c_ushort),
    ]

class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("union", INPUT_UNION),
    ]

def make_keyboard_input(vk, is_key_up=False, extended=False, hardware_scancode=False):
    ki = KEYBDINPUT()
    if hardware_scancode:
        ki.wVk = 0
        ki.wScan = ctypes.windll.user32.MapVirtualKeyW(vk, 0)
        flags = 0x0008  # KEYEVENTF_SCANCODE
    else:
        ki.wVk = vk
        ki.wScan = ctypes.windll.user32.MapVirtualKeyW(vk, 0)
        flags = 0
        
    if is_key_up:
        flags |= 0x0002  # KEYEVENTF_KEYUP
    if extended:
        flags |= 0x0001  # KEYEVENTF_EXTENDEDKEY
        
    ki.dwFlags = flags
    ki.time = 0
    ki.dwExtraInfo = 0

    union = INPUT_UNION()
    union.ki = ki

    inp = INPUT()
    inp.type = 1
    inp.union = union
    return inp

user32_dll = ctypes.windll.user32
user32_dll.SendInput.argtypes = [ctypes.c_uint, ctypes.POINTER(INPUT), ctypes.c_int]
user32_dll.SendInput.restype = ctypes.c_uint

class GUITHREADINFO(ctypes.Structure):
    """Used to get the truly focused child control in any process."""
    _fields_ = [
        ("cbSize",       wintypes.DWORD),
        ("flags",        wintypes.DWORD),
        ("hwndActive",   wintypes.HWND),
        ("hwndFocus",    wintypes.HWND),
        ("hwndCapture",  wintypes.HWND),
        ("hwndMenuOwner",wintypes.HWND),
        ("hwndMoveSize", wintypes.HWND),
        ("hwndCaret",    wintypes.HWND),
        ("rcCaret",      wintypes.RECT),
    ]




class HotkeySignals(QObject):
    replace_trigger = pyqtSignal()
    popup_trigger = pyqtSignal()
    case_trigger = pyqtSignal()

def _parse_modifiers(modifiers_list):
    # fsModifiers flags for Windows RegisterHotKey:
    # MOD_ALT = 0x0001
    # MOD_CONTROL = 0x0002
    # MOD_SHIFT = 0x0004
    # MOD_WIN = 0x0008
    # MOD_NOREPEAT = 0x4000 (prevents repeat messages when holding key down)
    fsModifiers = 0x4000
    for mod in modifiers_list:
        m = mod.lower()
        if m == "ctrl":
            fsModifiers |= 0x0002
        elif m == "alt":
            fsModifiers |= 0x0001
        elif m == "shift":
            fsModifiers |= 0x0004
        elif m == "win":
            fsModifiers |= 0x0008
    return fsModifiers

class HotkeyListener(QObject):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.signals = HotkeySignals()
        self.is_running = False
        self.thread_id = None
        self.thread = None
        self.is_processing = False
        self._processing_started_at = 0.0
        # Modifier state captured exactly when the hotkey fires (background thread)
        self.trigger_shift = False
        self.trigger_caps  = False
        logging.info("HotkeyListener (QObject) ініціалізовано.")

    def start(self):
        if self.is_running:
            return
            
        self.is_running = True
        import threading
        self.thread = threading.Thread(target=self._run_listener, daemon=True)
        self.thread.start()
        logging.info("HotkeyListener потік запущено.")

    def stop(self):
        if not self.is_running:
            return
            
        self.is_running = False
        self.is_processing = False
        if self.thread_id:
            # Send WM_QUIT (0x0012) to wake up and terminate the GetMessage loop in the background thread
            ctypes.windll.user32.PostThreadMessageW(self.thread_id, 0x0012, 0, 0)
            self.thread_id = None
            
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
            
        logging.info("HotkeyListener зупинено.")

    def reload(self):
        self.stop()
        time.sleep(0.1)
        self.start()

    def _run_listener(self):
        user32 = ctypes.windll.user32
        self.thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        logging.info(f"Потік глобальних гарячих клавіш запущено. ID потоку: {self.thread_id}")
        
        # Register replace hotkey (ID = 1)
        replace_cfg = self.config.get_hotkey_replace()
        mods_replace = _parse_modifiers(replace_cfg.get("modifiers", []))
        vk_replace = replace_cfg.get("vk", 0)
        
        # Register popup hotkey (ID = 2)
        popup_cfg = self.config.get_hotkey_popup()
        mods_popup = _parse_modifiers(popup_cfg.get("modifiers", []))
        vk_popup = popup_cfg.get("vk", 0)
        
        # Register case hotkey (ID = 3)
        case_cfg = self.config.get_hotkey_case()
        mods_case = _parse_modifiers(case_cfg.get("modifiers", []))
        vk_case = case_cfg.get("vk", 0)
        
        res1 = user32.RegisterHotKey(None, 1, mods_replace, vk_replace)
        res2 = user32.RegisterHotKey(None, 2, mods_popup, vk_popup)
        res3 = user32.RegisterHotKey(None, 3, mods_case, vk_case)
        
        logging.info(
            f"Реєстрація гарячих клавіш у потоці: "
            f"Виправлення ID=1 (успішно={res1}, mods={mods_replace}, vk={vk_replace}); "
            f"Попап ID=2 (успішно={res2}, mods={mods_popup}, vk={vk_popup}); "
            f"Регістр ID=3 (успішно={res3}, mods={mods_case}, vk={vk_case})"
        )
        
        if not res1 or not res2 or not res3:
            logging.warning("Не вдалося зареєструвати одну з гарячих клавіш у потоці. Можливо, вона вже зайнята.")
            
        msg = wintypes.MSG()
        while self.is_running:
            ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret == 0 or ret == -1:
                break
                
            if msg.message == 0x0312:  # WM_HOTKEY
                if self.is_processing:
                    if time.time() - self._processing_started_at < 5.0:
                        logging.info("WM_HOTKEY ignored (already processing another hotkey).")
                        continue
                    logging.warning("WM_HOTKEY processing lock timed out (>5s), resetting.")
                hotkey_id = msg.wParam
                # Capture modifier state HERE — before any processing delays
                self.trigger_shift = (user32.GetAsyncKeyState(0x10) & 0x8000) != 0
                self.trigger_caps  = (user32.GetKeyState(0x14) & 0x0001) != 0
                logging.info(f"WM_HOTKEY перехоплено в потоці: id={hotkey_id}, shift={self.trigger_shift}, caps={self.trigger_caps}")
                self.is_processing = True
                self._processing_started_at = time.time()
                try:
                    if hotkey_id == 1:
                        self.signals.replace_trigger.emit()
                    elif hotkey_id == 2:
                        self.signals.popup_trigger.emit()
                    elif hotkey_id == 3:
                        self.signals.case_trigger.emit()
                    else:
                        self.is_processing = False
                except Exception:
                    self.is_processing = False
                    raise
                    
        # Unregister hotkeys before thread exits
        user32.UnregisterHotKey(None, 1)
        user32.UnregisterHotKey(None, 2)
        user32.UnregisterHotKey(None, 3)
        logging.info("Потік глобальних гарячих клавіш завершив роботу.")

    def _simulate_ctrl_key(self, vk_key):
        user32 = ctypes.windll.user32
        
        # Check current physical state of modifier keys
        ctrl_held = (user32.GetAsyncKeyState(0x11) & 0x8000) != 0
        alt_held = (user32.GetAsyncKeyState(0x12) & 0x8000) != 0
        shift_held = (user32.GetAsyncKeyState(0x10) & 0x8000) != 0
        win_held = ((user32.GetAsyncKeyState(0x5B) & 0x8000) != 0 or 
                    (user32.GetAsyncKeyState(0x5C) & 0x8000) != 0)
        
        # 1. Temporarily release modifiers to prevent combo collision
        if ctrl_held:
            user32.keybd_event(0x11, 0, 2, 0) # Ctrl UP
        if alt_held:
            user32.keybd_event(0x12, 0, 2, 0) # Alt UP
        if shift_held:
            user32.keybd_event(0x10, 0, 2, 0) # Shift UP
        if win_held:
            user32.keybd_event(0x5B, 0, 2, 0) # LWin UP
            user32.keybd_event(0x5C, 0, 2, 0) # RWin UP
            
        time.sleep(0.01) # Give the OS time to process key releases
        
        # 2. Press Ctrl
        user32.keybd_event(0x11, 0, 0, 0) # Ctrl DOWN
        
        # 3. Press and release the character key
        user32.keybd_event(vk_key, 0, 0, 0) # Key DOWN
        time.sleep(0.01)
        user32.keybd_event(vk_key, 0, 2, 0) # Key UP
        
        # 4. Release Ctrl
        user32.keybd_event(0x11, 0, 2, 0) # Ctrl UP
        
        time.sleep(0.01) # Wait for simulation to finish
        
        # 5. Restore modifier states only if physically still held
        if ctrl_held and (user32.GetAsyncKeyState(0x11) & 0x8000) != 0:
            user32.keybd_event(0x11, 0, 0, 0) # Ctrl DOWN
        if alt_held and (user32.GetAsyncKeyState(0x12) & 0x8000) != 0:
            user32.keybd_event(0x12, 0, 0, 0) # Alt DOWN
        if shift_held and (user32.GetAsyncKeyState(0x10) & 0x8000) != 0:
            user32.keybd_event(0x10, 0, 0, 0) # Shift DOWN
        if win_held:
            if (user32.GetAsyncKeyState(0x5B) & 0x8000) != 0:
                user32.keybd_event(0x5B, 0, 0, 0) # LWin DOWN
            if (user32.GetAsyncKeyState(0x5C) & 0x8000) != 0:
                user32.keybd_event(0x5C, 0, 0, 0) # RWin DOWN

    def release_all_modifiers(self):
        """Emergency cleanup to guarantee no Ctrl/Alt/Shift/Win keys remain stuck in DOWN state."""
        user32 = ctypes.windll.user32
        vks = [0x10, 0x11, 0x12, 0x5B, 0x5C, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5]
        for vk in vks:
            if (user32.GetAsyncKeyState(vk) & 0x8000) == 0:
                inp = make_keyboard_input(vk, is_key_up=True, hardware_scancode=True)
                user32_dll.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def switch_system_layout(self, target_lang):
        """
        Switches the system input language / keyboard layout of the foreground window
        by selecting from the user's ALREADY INSTALLED keyboard layouts.
        target_lang: 'ua' or 'en'
        """
        try:
            user32 = ctypes.windll.user32
            target_lang_id = 0x0422 if target_lang.lower() == "ua" else 0x0409
            
            fg_hwnd = user32.GetForegroundWindow()
            if not fg_hwnd:
                return
            fg_tid = user32.GetWindowThreadProcessId(fg_hwnd, None)
            
            curr_hkl = user32.GetKeyboardLayout(fg_tid)
            if (curr_hkl & 0xFFFF) == target_lang_id:
                logging.info(f"Already in {target_lang.upper()} layout ({hex(curr_hkl & 0xFFFFFFFF)}).")
                return

            # Check how many installed layouts the user has
            num_layouts = user32.GetKeyboardLayoutList(0, None)
            max_attempts = max(num_layouts, 4) if num_layouts > 0 else 4
            
            # Cycle forward through installed input languages (INPUTLANGCHANGE_FORWARD = 2)
            for attempt in range(max_attempts):
                user32.PostMessageW(fg_hwnd, 0x0050, 2, 0) # 0x0050 = WM_INPUTLANGCHANGEREQUEST, 2 = INPUTLANGCHANGE_FORWARD
                
                # Also post to focused child control if any
                gi = GUITHREADINFO()
                gi.cbSize = ctypes.sizeof(GUITHREADINFO)
                if user32.GetGUIThreadInfo(fg_tid, ctypes.byref(gi)) and gi.hwndFocus:
                    user32.PostMessageW(gi.hwndFocus, 0x0050, 2, 0)

                time.sleep(0.03)
                new_hkl = user32.GetKeyboardLayout(fg_tid) & 0xFFFFFFFF
                if (new_hkl & 0xFFFF) == target_lang_id:
                    logging.info(f"Smart-switched to installed {target_lang.upper()} layout (hkl: {hex(new_hkl)}) on attempt {attempt+1}")
                    return

            # Fallback if window didn't process WM_INPUTLANGCHANGEREQUEST: simulate Alt+Shift key event
            if (user32.GetKeyboardLayout(fg_tid) & 0xFFFF) != target_lang_id:
                logging.info("Fallback: simulating Alt+Shift to toggle system layout...")
                user32.keybd_event(0x12, 0, 0, 0) # Alt down
                user32.keybd_event(0x10, 0, 0, 0) # Shift down
                user32.keybd_event(0x10, 0, 2, 0) # Shift up
                user32.keybd_event(0x12, 0, 2, 0) # Alt up
        except Exception as e:
            logging.error(f"Error switching system layout: {e}")

    def _open_clipboard_retry(self, retries=10, delay=0.01):
        """Open Win32 clipboard with NULL owner so we never create an OLE lock on the main thread."""
        for _ in range(retries):
            if user32_cb.OpenClipboard(None):
                return True
            time.sleep(delay)
        return False

    def _set_win32_exclusion_flags_locked(self):
        """Must be called while clipboard is open. Prevents Win+V and Cloud Clipboard from logging internal writes."""
        GMEM_MOVEABLE = 0x0002
        for fmt_name in CLIPBOARD_EXCLUSION_FORMATS:
            fmt_id = user32_cb.RegisterClipboardFormatW(fmt_name)
            if fmt_id:
                h_mem = kernel32_dll.GlobalAlloc(GMEM_MOVEABLE, 4)
                if h_mem:
                    ptr = kernel32_dll.GlobalLock(h_mem)
                    if ptr:
                        ctypes.memset(ptr, 0, 4)
                        kernel32_dll.GlobalUnlock(h_mem)
                        if not user32_cb.SetClipboardData(fmt_id, h_mem):
                            kernel32_dll.GlobalFree(h_mem)
                    else:
                        kernel32_dll.GlobalFree(h_mem)

    def _set_temp_clipboard_text(self, text):
        """Write temporary text (or empty string) to Win32 clipboard without OLE lock and without polluting Win+V."""
        GMEM_MOVEABLE = 0x0002
        CF_UNICODETEXT = 13
        if self._open_clipboard_retry():
            try:
                user32_cb.EmptyClipboard()
                self._set_win32_exclusion_flags_locked()
                if text:
                    raw = (text + "\0").encode("utf-16-le")
                    h_mem = kernel32_dll.GlobalAlloc(GMEM_MOVEABLE, len(raw))
                    if h_mem:
                        ptr = kernel32_dll.GlobalLock(h_mem)
                        if ptr:
                            ctypes.memmove(ptr, raw, len(raw))
                            kernel32_dll.GlobalUnlock(h_mem)
                            if not user32_cb.SetClipboardData(CF_UNICODETEXT, h_mem):
                                kernel32_dll.GlobalFree(h_mem)
                        else:
                            kernel32_dll.GlobalFree(h_mem)
                return
            finally:
                user32_cb.CloseClipboard()
        pyperclip.copy(text or "")

    def snapshot_clipboard(self):
        """
        Capture all safe Win32 clipboard formats (screenshots CF_DIB/CF_DIBV5/PNG,
        copied files CF_HDROP, HTML, RTF, Unicode text, etc.) into memory without OLE locks.
        """
        snap = []
        if not self._open_clipboard_retry():
            try:
                txt = pyperclip.paste()
                if txt:
                    snap.append((13, (txt + "\0").encode("utf-16-le")))
            except Exception:
                pass
            return snap

        try:
            fmt = 0
            name_buf = ctypes.create_unicode_buffer(256)
            while True:
                fmt = user32_cb.EnumClipboardFormats(fmt)
                if not fmt:
                    break
                is_safe = fmt in SAFE_STD_CLIPBOARD_FORMATS
                if not is_safe and fmt >= 0xC000:
                    length = user32_cb.GetClipboardFormatNameW(fmt, name_buf, 255)
                    if length > 0 and name_buf.value in SAFE_NAMED_CLIPBOARD_FORMATS:
                        is_safe = True
                if not is_safe:
                    continue

                handle = user32_cb.GetClipboardData(fmt)
                if not handle:
                    continue
                size = kernel32_dll.GlobalSize(handle)
                if size <= 0 or size > 100 * 1024 * 1024:  # 100 MB safety cap
                    continue
                ptr = kernel32_dll.GlobalLock(handle)
                if not ptr:
                    continue
                try:
                    raw_bytes = ctypes.string_at(ptr, size)
                    snap.append((fmt, raw_bytes))
                finally:
                    kernel32_dll.GlobalUnlock(handle)
        except Exception as e:
            logging.error(f"Помилка збереження стану буфера обміну: {e}")
        finally:
            user32_cb.CloseClipboard()
        return snap

    def restore_clipboard(self, snap):
        """Restore previously captured Win32 clipboard formats (screenshots, files, text, etc.)."""
        try:
            if isinstance(snap, str):
                self._set_temp_clipboard_text(snap)
                return
            if not isinstance(snap, list):
                return

            GMEM_MOVEABLE = 0x0002
            if self._open_clipboard_retry():
                try:
                    user32_cb.EmptyClipboard()
                    if snap:
                        self._set_win32_exclusion_flags_locked()
                    for fmt, raw_bytes in snap:
                        if not raw_bytes:
                            continue
                        h_mem = kernel32_dll.GlobalAlloc(GMEM_MOVEABLE, len(raw_bytes))
                        if h_mem:
                            ptr = kernel32_dll.GlobalLock(h_mem)
                            if ptr:
                                ctypes.memmove(ptr, raw_bytes, len(raw_bytes))
                                kernel32_dll.GlobalUnlock(h_mem)
                                if not user32_cb.SetClipboardData(fmt, h_mem):
                                    kernel32_dll.GlobalFree(h_mem)
                            else:
                                kernel32_dll.GlobalFree(h_mem)
                finally:
                    user32_cb.CloseClipboard()
        except Exception as e:
            logging.error(f"Помилка відновлення буфера обміну: {e}")

    def grab_selected_text(self):
        logging.info("Копіювання виділеного тексту через чистий Ctrl+C...")
        user32 = ctypes.windll.user32
        old_clipboard = self.snapshot_clipboard()
        pyperclip.copy("")
        seq_before = user32.GetClipboardSequenceNumber()

        time.sleep(0.02)
        self._simulate_ctrl_key(0x43) # VK_C = 0x43

        selected_text = ""
        # Wait until the clipboard actually changes instead of fixed sleeps (up to 500ms)
        deadline = time.time() + 0.5
        while time.time() < deadline:
            if user32.GetClipboardSequenceNumber() != seq_before:
                text = pyperclip.paste()
                if text:
                    selected_text = text
                    break
            time.sleep(0.02)

        logging.info(f"Зчитано з буфера: {len(selected_text)} символів.")
        return selected_text, old_clipboard

    def _get_focused_hwnd(self):
        """
        Returns the HWND of the truly focused control in the foreground process.
        GetFocus() only works for our own thread — this works cross-process.
        """
        user32 = ctypes.windll.user32
        fg = user32.GetForegroundWindow()
        if not fg:
            return None
        tid = user32.GetWindowThreadProcessId(fg, None)
        gi = GUITHREADINFO()
        gi.cbSize = ctypes.sizeof(GUITHREADINFO)
        if user32.GetGUIThreadInfo(tid, ctypes.byref(gi)) and gi.hwndFocus:
            return gi.hwndFocus
        return fg

    def _try_em_setsel(self, hwnd, text_len):
        """
        Instant selection via EM_GETSEL / EM_SETSEL (standard Edit / RichEdit controls).
        Uses return-value form of EM_GETSEL — no pointers, safe cross-process.
        Returns True on success.
        """
        try:
            user32 = ctypes.windll.user32
            # EM_GETSEL with NULL args: LOWORD=start, HIWORD=end (16-bit positions).
            # Positions at/after 0xFFFF are ambiguous in this form — bail out to strategy B.
            r = user32.SendMessageW(hwnd, 0x00B0, 0, 0) & 0xFFFFFFFF
            end_pos = (r >> 16) & 0xFFFF
            if end_pos < 0xFFFF and end_pos >= text_len > 0:
                new_start = end_pos - text_len
                user32.SendMessageW(hwnd, 0x00B1, new_start, end_pos)  # EM_SETSEL
                # Verify
                r2 = user32.SendMessageW(hwnd, 0x00B0, 0, 0) & 0xFFFFFFFF
                if (r2 & 0xFFFF) == new_start and ((r2 >> 16) & 0xFFFF) == end_pos:
                    logging.info(f"EM_SETSEL: [{new_start}, {end_pos}] ✓")
                    return True
        except Exception as e:
            logging.debug(f"EM_SETSEL: {e}")
        return False

    def paste_text(self, text, old_clipboard, select_text=True):
        logging.info(f"Вставка виправленого тексту...")
        user32 = ctypes.windll.user32

        # ── 1. Snapshot which modifier keys are physically held ──────────────
        vks_to_check = [
            0xA2, 0xA3,  # LCtrl, RCtrl
            0xA4, 0xA5,  # LAlt, RAlt
            0xA0, 0xA1,  # LShift, RShift
            0x5B, 0x5C,  # LWin, RWin
        ]
        held = []
        for vk in vks_to_check:
            if (user32.GetAsyncKeyState(vk) & 0x8000) != 0:
                held.append(vk)

        # ── 2. Release held modifiers so they don't interfere ────────────────
        for vk in held:
            inp = make_keyboard_input(vk, is_key_up=True, hardware_scancode=True)
            user32_dll.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        time.sleep(0.01)

        # ── 3. Put translated text in clipboard and paste ────────────────────
        pyperclip.copy(text)
        # Wait until the clipboard actually holds our text (up to 200ms)
        deadline = time.time() + 0.2
        while time.time() < deadline:
            try:
                if pyperclip.paste() == text:
                    break
            except Exception:
                pass
            time.sleep(0.01)


        arr = (INPUT * 4)()
        arr[0] = make_keyboard_input(0x11, is_key_up=False) # Ctrl DOWN
        arr[1] = make_keyboard_input(0x56, is_key_up=False) # V DOWN
        arr[2] = make_keyboard_input(0x56, is_key_up=True)  # V UP
        arr[3] = make_keyboard_input(0x11, is_key_up=True)  # Ctrl UP
        user32_dll.SendInput(4, arr, ctypes.sizeof(INPUT))
        time.sleep(0.04)                         # wait briefly for app to process paste

        # ── 4. Re-select the pasted text ─────────────────────────────────────
        if text and select_text:
            normalized = text.replace("\r\n", "\n")
            # Edit controls address characters in UTF-16 code units (emoji take two)
            utf16_len = len(normalized.encode("utf-16-le")) // 2

            # Strategy A: instant via EM_SETSEL (Notepad, WinForms, MFC…)
            hwnd = self._get_focused_hwnd()
            selected = hwnd and self._try_em_setsel(hwnd, utf16_len)

            if not selected:
                # Arrow keys move by grapheme, not by code unit
                text_len = _caret_steps(normalized)
                if 0 < text_len <= MAX_RESELECT_STEPS:
                    # Strategy B: SendInput Shift+Left × N with hardware_scancode (Batched for instant selection)
                    shift_down = make_keyboard_input(0x10, is_key_up=False, hardware_scancode=True)
                    user32_dll.SendInput(1, ctypes.byref(shift_down), ctypes.sizeof(INPUT))
                    time.sleep(0.01)

                    MAX_BATCH_STEPS = 500  # 1000 INPUT events per batch
                    remaining = text_len
                    while remaining > 0:
                        steps_in_batch = min(MAX_BATCH_STEPS, remaining)
                        chunk_size = steps_in_batch * 2
                        chunk_arr = (INPUT * chunk_size)()
                        for i in range(steps_in_batch):
                            chunk_arr[i * 2] = make_keyboard_input(0x25, is_key_up=False, extended=True, hardware_scancode=True)
                            chunk_arr[i * 2 + 1] = make_keyboard_input(0x25, is_key_up=True, extended=True, hardware_scancode=True)
                        user32_dll.SendInput(chunk_size, chunk_arr, ctypes.sizeof(INPUT))
                        remaining -= steps_in_batch

                    time.sleep(0.01)
                    shift_up = make_keyboard_input(0x10, is_key_up=True, hardware_scancode=True)
                    user32_dll.SendInput(1, ctypes.byref(shift_up), ctypes.sizeof(INPUT))
                    logging.info(f"Batched SendInput Shift+Left × {text_len}")
                elif text_len > MAX_RESELECT_STEPS:
                    logging.info(f"Skipped Shift+Left re-selection: text too long ({text_len} > {MAX_RESELECT_STEPS} steps).")

        time.sleep(0.01)

        # ── 5. Restore originally-held modifiers (if still physically held) ──
        for vk in held:
            if (user32.GetAsyncKeyState(vk) & 0x8000) != 0:
                inp = make_keyboard_input(vk, is_key_up=False, hardware_scancode=True)
                user32_dll.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
            else:
                inp = make_keyboard_input(vk, is_key_up=True, hardware_scancode=True)
                user32_dll.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

        # Always do safety cleanup to ensure no key is stuck down
        self.release_all_modifiers()

        # ── 6. Restore clipboard ─────────────────────────────────────────────
        self.restore_clipboard(old_clipboard)
        logging.info("Буфер обміну відновлено.")
