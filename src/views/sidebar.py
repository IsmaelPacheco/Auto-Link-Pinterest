"""
sidebar.py
Menu lateral do AutoLink Pinterest:
Marca, navegação entre abas, terminal de logs em tempo real e status do sistema.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame, QTextEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTextCursor


class Sidebar(QWidget):
    navegar = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(270)
        self._botoes_nav = []
        self._montar()

    def _montar(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 24, 0, 16)
        layout.setSpacing(12)

        # MARCA / LOGO
        layout.addLayout(self._montar_marca())
        layout.addSpacing(15)

        # BOTÕES DE NAVEGAÇÃO
        self.btn_nav_dashboard = self._criar_botao_nav("🛍️   Criador Rápido", ativo=True)
        self.btn_nav_autopilot = self._criar_botao_nav("⚡   Piloto Automático", ativo=False)
        self.btn_nav_accounts = self._criar_botao_nav("👥   Multi-Contas", ativo=False)
        self.btn_nav_historico = self._criar_botao_nav("📊   Histórico de Pins", ativo=False)
        self.btn_nav_settings = self._criar_botao_nav("⚙️   Configurações", ativo=False)

        self.btn_nav_dashboard.clicked.connect(lambda: self._selecionar(0))
        self.btn_nav_autopilot.clicked.connect(lambda: self._selecionar(1))
        self.btn_nav_accounts.clicked.connect(lambda: self._selecionar(2))
        self.btn_nav_historico.clicked.connect(lambda: self._selecionar(3))
        self.btn_nav_settings.clicked.connect(lambda: self._selecionar(4))

        layout.addWidget(self.btn_nav_dashboard)
        layout.addWidget(self.btn_nav_autopilot)
        layout.addWidget(self.btn_nav_accounts)
        layout.addWidget(self.btn_nav_historico)
        layout.addWidget(self.btn_nav_settings)

        # TERMINAL DE LOGS INTEGRADO
        layout.addSpacing(15)
        box_term_header = QHBoxLayout()
        box_term_header.setContentsMargins(18, 0, 18, 0)
        lbl_log = QLabel("TERMINAL EM TEMPO REAL")
        lbl_log.setStyleSheet("color: #6B7280; font-size: 11px; font-weight: bold;")
        box_term_header.addWidget(lbl_log)
        box_term_header.addStretch()

        btn_limpar = QPushButton("Limpar")
        btn_limpar.setCursor(Qt.PointingHandCursor)
        btn_limpar.setStyleSheet("color: #9CA3AF; font-size: 10px; background: transparent; border: none;")
        btn_limpar.clicked.connect(self.limpar_terminal)
        box_term_header.addWidget(btn_limpar)
        layout.addLayout(box_term_header)

        self.txt_terminal = QTextEdit()
        self.txt_terminal.setReadOnly(True)
        self.txt_terminal.setStyleSheet("""
            QTextEdit {
                background-color: #0B0F19;
                border: 1px solid #1F2937;
                border-radius: 8px;
                color: #D1D5DB;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                margin: 0px 14px;
                padding: 6px;
            }
        """)
        layout.addWidget(self.txt_terminal, 1)

        # RODAPÉ DE VERSÃO
        lbl_versao = QLabel("AutoLink Pinterest v1.0 • Oficial")
        lbl_versao.setAlignment(Qt.AlignCenter)
        lbl_versao.setStyleSheet("color: #4B5563; font-size: 10px; padding-top: 6px;")
        layout.addWidget(lbl_versao)

    def _montar_marca(self) -> QHBoxLayout:
        box = QHBoxLayout()
        box.setContentsMargins(20, 0, 20, 0)
        box.setSpacing(10)

        lbl_icone = QLabel("📌")
        lbl_icone.setStyleSheet("font-size: 26px;")
        box.addWidget(lbl_icone)

        box_texto = QVBoxLayout()
        box_texto.setSpacing(1)

        lbl_nome = QLabel("AutoLink")
        lbl_nome.setStyleSheet("color: #F3F4F6; font-size: 18px; font-weight: bold;")
        lbl_sub = QLabel("Shopee ➔ Pinterest")
        lbl_sub.setStyleSheet("color: #EE4D2D; font-size: 11px; font-weight: bold;")

        box_texto.addWidget(lbl_nome)
        box_texto.addWidget(lbl_sub)
        box.addLayout(box_texto)
        box.addStretch()
        return box

    def _criar_botao_nav(self, texto: str, ativo: bool = False) -> QPushButton:
        btn = QPushButton(texto)
        btn.setObjectName("btnNavAtivo" if ativo else "btnNav")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(42)
        self._botoes_nav.append(btn)
        return btn

    def _selecionar(self, index: int):
        for i, btn in enumerate(self._botoes_nav):
            btn.setObjectName("btnNavAtivo" if i == index else "btnNav")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.navegar.emit(index)

    def append_log(self, mensagem: str, nivel: str = "info"):
        """Adiciona log estilizado no terminal com cores apropriadas."""
        cor = "#9CA3AF"  # Info / Cinza claro
        prefixo = "•"
        if nivel == "success":
            cor = "#10B981"
            prefixo = "✓"
        elif nivel == "error":
            cor = "#EF4444"
            prefixo = "✗"
        elif nivel == "warning":
            cor = "#F59E0B"
            prefixo = "!"

        html = f'<div style="color: {cor}; margin-bottom: 3px;"><b>{prefixo}</b> {mensagem}</div>'
        self.txt_terminal.append(html)
        self.txt_terminal.moveCursor(QTextCursor.End)

    def limpar_terminal(self):
        self.txt_terminal.clear()