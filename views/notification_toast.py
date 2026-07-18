from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QPropertyAnimation, QTimer, QEvent

class NotificationToast(QFrame):
    def __init__(self, parent, message, duration=2000):
        # Cerrar cualquier notificación previa en el mismo padre para evitar superposición
        if parent:
            for child in parent.findChildren(NotificationToast):
                child.close_immediately()

        super().__init__(parent)
        self.duration = duration
        
        # Diseño responsivo y estética de tema oscuro
        self.setStyleSheet("""
            NotificationToast {
                background-color: #1e1e1e;
                border: 2px solid #2a82da;
                border-radius: 8px;
            }
            QLabel {
                color: #ffffff;
                font-size: 13px;
                font-weight: bold;
                background: transparent;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)
        
        self.label = QLabel(message)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        
        # Efecto de opacidad para animación de fade
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0.0)
        
        self.show()
        self.adjustSize()
        self.reposition()
        
        if self.parent():
            self.parent().installEventFilter(self)
        
        # Animación de entrada (Fade-in)
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(250)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.fade_out)
        
        self.anim.finished.connect(self.on_fade_in_finished)
        self.anim.start()

    def close_immediately(self):
        # Detener todo y eliminar inmediatamente
        if hasattr(self, 'timer'):
            self.timer.stop()
        if hasattr(self, 'anim'):
            self.anim.stop()
        self.deleteLater()

    def reposition(self):
        if self.parent():
            parent_rect = self.parent().rect()
            x = (parent_rect.width() - self.width()) // 2
            # Posicionarla en el tercio inferior del widget padre
            y = parent_rect.height() - self.height() - 60
            self.move(x, y)

    def eventFilter(self, watched, event):
        if watched == self.parent() and event.type() == QEvent.Type.Resize:
            self.reposition()
        return super().eventFilter(watched, event)

    def on_fade_in_finished(self):
        self.timer.start(self.duration)

    def fade_out(self):
        # Desconectar callbacks anteriores para evitar ciclos y realizar fade-out
        try:
            self.anim.disconnect()
        except Exception:
            pass
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.finished.connect(self.deleteLater)
        self.anim.start()
