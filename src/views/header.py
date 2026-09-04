"""
header.py
Cabeçalho da área de conteúdo: título/subtítulo da página atual e botão de tema.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt, Signal


class Header(QWidget):
    """Emite `alternar_tema()` quando o botão de tema é clicado."""

    alternar_tema = Signal()
    abrir_instrucoes = Signal()
    abrir_instrucoes = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._montar()

    def _montar(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 6)
        layout.setSpacing(4)

        box_titulos = QVBoxLayout()
        box_titulos.setSpacing(2)
        self.lbl_titulo = QLabel()
        self.lbl_titulo.setObjectName("headerTitle")
        self.lbl_subtitulo = QLabel()
        self.lbl_subtitulo.setObjectName("headerSubtitle")
        box_titulos.addWidget(self.lbl_titulo)
        box_titulos.addWidget(self.lbl_subtitulo)

        layout.addLayout(box_titulos)
        layout.addStretch()

        self.btn_instrucoes = QPushButton("📖 Instruções")
        self.btn_instrucoes.setObjectName("btnPrimary")
        self.btn_instrucoes.setCursor(Qt.PointingHandCursor)
        self.btn_instrucoes.setFixedWidth(130)
        self.btn_instrucoes.clicked.connect(self.abrir_instrucoes.emit)

        self.btn_theme = QPushButton()
        self.btn_theme.setObjectName("btnTheme")
        self.btn_theme.setCursor(Qt.PointingHandCursor)
        self.btn_theme.setFixedWidth(110)
        self.btn_theme.clicked.connect(self.alternar_tema.emit)

        box_buttons = QHBoxLayout()
        box_buttons.setSpacing(10)
        box_buttons.addWidget(self.btn_instrucoes)
        box_buttons.addWidget(self.btn_theme)

        layout.addLayout(box_buttons)

    def definir_titulos(self, titulo: str, subtitulo: str):
        self.lbl_titulo.setText(titulo)
        self.lbl_subtitulo.setText(subtitulo)

    def definir_texto_tema(self, texto: str):
        self.btn_theme.setText(texto)