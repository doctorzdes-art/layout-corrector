from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, pyqtProperty
from PyQt6.QtGui import QColor, QCursor, QFont, QClipboard
from PyQt6.QtWidgets import QApplication

class TextPopup(QWidget):
    def __init__(self, text, duration=5, parent=None):
        super().__init__(parent)
        self.text = text
        self.fade_anim = None
        
        # Configure window attributes
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.init_ui()
        self.position_near_cursor()
        
        # Auto close timer (custom duration)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.fade_out)
        self.timer.start(duration * 1000)

    def init_ui(self):
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Container widget with border and background
        self.container = QWidget(self)
        self.container.setObjectName("Container")
        self.container.setStyleSheet("""
            QWidget#Container {
                background-color: rgba(30, 30, 30, 235);
                border: 1px solid rgba(80, 80, 80, 150);
                border-radius: 12px;
            }
        """)
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(15, 12, 15, 12)
        container_layout.setSpacing(8)
        
        # Header layout (title & buttons)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("Розкладку виправлено", self.container)
        title_font = QFont("Segoe UI", 9)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #00ADB5; background: transparent;")
        
        btn_close = QPushButton("×", self.container)
        btn_close.setFixedSize(18, 18)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                color: #888888;
                border: none;
                border-radius: 9px;
                background-color: rgba(255, 255, 255, 15);
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #FFFFFF;
                background-color: rgba(255, 50, 50, 150);
            }
        """)
        btn_close.clicked.connect(self.close)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(btn_close)
        
        # Text display
        self.text_label = QLabel(self.text, self.container)
        self.text_label.setWordWrap(True)
        self.text_label.setFont(QFont("Segoe UI", 10))
        self.text_label.setStyleSheet("color: #EEEEEE; background: transparent;")
        # Allow selecting/copying text manually if desired
        self.text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        # Copy button helper
        btn_copy = QPushButton("Копіювати в буфер", self.container)
        btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #00ADB5;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00FFF5;
                color: #222831;
            }
        """)
        btn_copy.clicked.connect(self.copy_to_clipboard)
        
        container_layout.addLayout(header_layout)
        container_layout.addWidget(self.text_label)
        container_layout.addWidget(btn_copy)
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(shadow)
        
        layout.addWidget(self.container)
        
        # Adjust sizing based on content
        self.adjustSize()
        self.setFixedWidth(min(max(self.sizeHint().width() + 20, 250), 400))
        self.adjustSize()

    def position_near_cursor(self):
        cursor_pos = QCursor.pos()
        screen = QApplication.primaryScreen().geometry()
        
        # Position popup slightly offset from cursor (15px down, 15px right)
        x = cursor_pos.x() + 15
        y = cursor_pos.y() + 15
        
        # Prevent window from going off-screen
        if x + self.width() > screen.width():
            x = cursor_pos.x() - self.width() - 15
        if y + self.height() > screen.height():
            y = cursor_pos.y() - self.height() - 15
            
        self.move(max(0, x), max(0, y))

    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.text)
        self.fade_out()

    def fade_out(self):
        if self.fade_anim:
            return
            
        self.fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self.fade_anim.setDuration(400)
        self.fade_anim.setStartValue(1.0)
        self.fade_anim.setEndValue(0.0)
        self.fade_anim.finished.connect(self.close)
        self.fade_anim.start()
