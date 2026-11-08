"""
Common UI utilities and styling helpers for LayoutCorrector v2.
Handles font loading, SVG tinting, shape compositing, and theme application.
"""

from pathlib import Path
from PyQt6.QtCore import Qt, QByteArray, QRectF
from PyQt6.QtGui import QFontDatabase, QFont, QIcon, QPixmap, QPainter, QColor
from PyQt6.QtSvg import QSvgRenderer
from config import get_resource_path

FONT_FILES = [
    "FixelDisplay-Bold.ttf",
    "FixelDisplay-SemiBold.ttf",
    "FixelDisplay-Medium.ttf",
    "FixelText-Regular.ttf",
    "FixelText-Medium.ttf",
    "FixelText-SemiBold.ttf",
]

_FONTS_LOADED = False

def load_fonts(base_dir: Path = None) -> None:
    """Load bundled MacPaw Fixel fonts into QFontDatabase."""
    global _FONTS_LOADED
    if _FONTS_LOADED:
        return

    if base_dir is None:
        base_dir = Path(get_resource_path("fonts")).parent

    fonts_dir = base_dir / "fonts"
    for f in FONT_FILES:
        font_path = fonts_dir / f
        if font_path.exists():
            fid = QFontDatabase.addApplicationFont(str(font_path))
            if fid == -1:
                print(f"[UI] Warning: Failed to load font: {f}")
        else:
            print(f"[UI] Warning: Font file missing: {font_path}")

    _FONTS_LOADED = True

def display_font(px: int, weight: QFont.Weight = QFont.Weight.Bold) -> QFont:
    """Return Fixel Display font at given pixel size and weight."""
    f = QFont("Fixel Display")
    f.setPixelSize(px)
    f.setWeight(weight)
    return f

def text_font(px: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    """Return Fixel Text font at given pixel size and weight."""
    f = QFont("Fixel Text")
    f.setPixelSize(px)
    f.setWeight(weight)
    return f

def svg_pixmap(path: Path, color: str, size: int) -> QPixmap:
    """
    Render SVG icon to high-DPI QPixmap with replaced stroke/fill color.
    Expects source SVG with default stroke/fill #EDEDF2.
    """
    text_data = path.read_text(encoding="utf-8")
    tinted = text_data.replace("#EDEDF2", color).replace("#ededf2", color)
    renderer = QSvgRenderer(QByteArray(tinted.encode("utf-8")))

    pm = QPixmap(size * 2, size * 2)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(p)
    p.end()
    pm.setDevicePixelRatio(2.0)
    return pm

def svg_icon(path: Path, color: str, size: int) -> QIcon:
    """Return QIcon from tinted SVG."""
    return QIcon(svg_pixmap(path, color, size))

def shape_with_icon(shape_path: Path, fill_color: str, icon_path: Path, ink_color: str, box_size: int, icon_size: int) -> QPixmap:
    """
    Render an expressive shape background (replacing #173A63 with fill_color)
    with a centered icon (replacing #EDEDF2 with ink_color).
    """
    pm = QPixmap(box_size * 2, box_size * 2)
    pm.fill(Qt.GlobalColor.transparent)

    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Render shape
    shape_raw = shape_path.read_text(encoding="utf-8").replace("#173A63", fill_color)
    shape_renderer = QSvgRenderer(QByteArray(shape_raw.encode("utf-8")))
    shape_renderer.render(p, QRectF(0, 0, box_size * 2, box_size * 2))

    # Render centered icon
    icon_raw = icon_path.read_text(encoding="utf-8").replace("#EDEDF2", ink_color).replace("#ededf2", ink_color)
    icon_renderer = QSvgRenderer(QByteArray(icon_raw.encode("utf-8")))
    offset = float(box_size - icon_size)  # in 2x pixels: (box*2 - icon*2)/2 == (box - icon)
    icon_rect = QRectF(offset, offset, float(icon_size * 2), float(icon_size * 2))
    icon_renderer.render(p, icon_rect)

    p.end()
    pm.setDevicePixelRatio(2.0)
    return pm

def load_theme(app, base_dir: Path = None) -> None:
    """
    Load theme.qss and apply to QApplication, substituting relative icon paths
    with absolute posix paths.
    """
    if base_dir is None:
        base_dir = Path(get_resource_path("theme.qss")).parent

    qss_path = base_dir / "theme.qss"
    if not qss_path.exists():
        print(f"[UI] Warning: theme.qss not found at {qss_path}")
        return

    qss_content = qss_path.read_text(encoding="utf-8")

    # Replace relative icons/ with absolute posix url
    icons_dir = (base_dir / "icons").as_posix()
    qss_content = qss_content.replace("url(icons/", f"url({icons_dir}/")

    app.setStyleSheet(qss_content)
