"""
cookie_dialog.py
Diálogo visual para importação rápida de cookies do Pinterest via JSON (Cookie-Editor).
Permite ao usuário conectar instantaneamente sua conta do Pinterest sem precisar de 2FA.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QMessageBox
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices

from src.engines.pinterest_browser_engine import PinterestBrowserEngine


class CookieImportDialog(QDialog):
    """Janela modal para colar e validar cookies do Pinterest."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔑 Importar Sessão do Pinterest via Cookies")
        self.setMinimumSize(550, 420)
        self.setStyleSheet("""
            QDialog {
                background-color: #111827;
                color: #F9FAFB;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        lbl_title = QLabel("🔑 Conectar Sessão Ativa do Pinterest (Zero 2FA)")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #EE4D2D;")
        layout.addWidget(lbl_title)

        lbl_desc = QLabel(
            "Se você já está logado no Pinterest no seu navegador normal, pode transferir sua sessão "
            "em 5 segundos sem precisar digitar senha nem confirmação de dois fatores (2FA):"
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #D1D5DB; font-size: 13px;")
        layout.addWidget(lbl_desc)

        # Passos
        lbl_steps = QLabel(
            "<b>1.</b> No seu Chrome, abra a aba do <b>Pinterest</b> onde você já está logado.<br>"
            "<b>2.</b> Abra a extensão <b>Cookie-Editor</b> e clique em <b>Export ➔ Export as JSON</b>.<br>"
            "<b>3.</b> Cole o código JSON copiado na caixa abaixo e clique em <b>Salvar e Validar</b>."
        )
        lbl_steps.setWordWrap(True)
        lbl_steps.setStyleSheet("color: #9CA3AF; font-size: 12px; background: #1F2937; padding: 10px; border-radius: 6px;")
        layout.addWidget(lbl_steps)

        # Botão para abrir o link da extensão se não tiver
        btn_ext = QPushButton("🌐 Abrir Cookie-Editor na Chrome Web Store (Se ainda não tiver)")
        btn_ext.setCursor(Qt.PointingHandCursor)
        btn_ext.setStyleSheet("background-color: #374151; color: #93C5FD; padding: 6px; border-radius: 4px; font-size: 11px;")
        btn_ext.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm")))
        layout.addWidget(btn_ext)

        self.txt_cookies = QTextEdit()
        self.txt_cookies.setPlaceholderText("Cole aqui o JSON dos cookies exportados pelo Cookie-Editor (começa com '[' e termina com ']')...")
        self.txt_cookies.setStyleSheet("""
            QTextEdit {
                background-color: #1F2937;
                color: #F9FAFB;
                border: 1px solid #374151;
                border-radius: 6px;
                padding: 8px;
                font-family: Consolas, monospace;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.txt_cookies, 1)

        # Botões de Ação
        box_buttons = QHBoxLayout()
        box_buttons.setSpacing(10)

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setStyleSheet("background-color: #374151; color: white; padding: 10px 18px; border-radius: 6px;")
        self.btn_cancel.clicked.connect(self.reject)
        box_buttons.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("💾 Salvar e Validar Sessão")
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setStyleSheet("background-color: #10B981; color: white; font-weight: bold; padding: 10px 22px; border-radius: 6px;")
        self.btn_save.clicked.connect(self._salvar_e_validar)
        box_buttons.addWidget(self.btn_save)

        layout.addLayout(box_buttons)

    def _salvar_e_validar(self):
        raw_text = self.txt_cookies.toPlainText().strip()
        if not raw_text:
            QMessageBox.warning(self, "Atenção", "Cole o JSON dos cookies exportados antes de continuar.")
            return

        self.btn_save.setEnabled(False)
        self.btn_save.setText("Validando cookies...")

        try:
            engine = PinterestBrowserEngine()
            res = engine.import_cookies(raw_text)

            if res.get("success"):
                QMessageBox.information(self, "Sucesso!", res.get("message"))
                self.accept()
            else:
                QMessageBox.warning(self, "Aviso", res.get("message", "Falha ao validar cookies."))
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Formato inválido de cookies:\n{e}")
        finally:
            self.btn_save.setEnabled(True)
            self.btn_save.setText("💾 Salvar e Validar Sessão")

