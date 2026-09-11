"""
settings_page.py
Página de Configurações Globais do AutoLink Pinterest:
Credenciais da Shopee Affiliate Open API, Google Gemini AI e Modo do Navegador.
Toda a gestão de contas, cookies e pastas do Pinterest é feita na aba '👥 Multi-Contas'.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QCheckBox, QFrame, QScrollArea, QMessageBox
)
from PySide6.QtCore import Qt, Signal

from src.models.config_manager import ConfigManager
from src.engines.shopee_engine import ShopeeEngine


class SettingsPage(QWidget):
    """Página de credenciais globais e integrações externas."""

    sig_log = Signal(str, str)

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.cfg = config_manager
        self._montar()
        self._carregar_valores()

    def _montar(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(20)

        # 1. CARD: SHOPEE AFFILIATE OPEN API
        card_shopee = self._criar_card("🛍️ Shopee Affiliate Open API (Credenciais Oficiais)")
        grid_shopee = QGridLayout()
        grid_shopee.setSpacing(12)

        grid_shopee.addWidget(QLabel("App ID / Key:"), 0, 0)
        self.input_shopee_app_id = QLineEdit()
        self.input_shopee_app_id.setPlaceholderText("Ex: 18362080140")
        grid_shopee.addWidget(self.input_shopee_app_id, 0, 1)

        grid_shopee.addWidget(QLabel("API Secret:"), 1, 0)
        self.input_shopee_secret = QLineEdit()
        self.input_shopee_secret.setEchoMode(QLineEdit.Password)
        self.input_shopee_secret.setPlaceholderText("Chave secreta oficial fornecida no portal da Shopee")
        grid_shopee.addWidget(self.input_shopee_secret, 1, 1)

        grid_shopee.addWidget(QLabel("País:"), 2, 0)
        self.combo_shopee_country = QComboBox()
        self.combo_shopee_country.addItems(["Brasil (BR)", "Global"])
        grid_shopee.addWidget(self.combo_shopee_country, 2, 1)

        self.btn_test_shopee = QPushButton("⚡ Testar Conexão Shopee")
        self.btn_test_shopee.setCursor(Qt.PointingHandCursor)
        self.btn_test_shopee.setStyleSheet("background-color: #EE4D2D; color: white; font-weight: bold; padding: 8px 18px; border-radius: 6px;")
        self.btn_test_shopee.clicked.connect(self._testar_shopee)
        grid_shopee.addWidget(self.btn_test_shopee, 3, 1, alignment=Qt.AlignLeft)

        card_shopee.layout().addLayout(grid_shopee)
        layout.addWidget(card_shopee)

        # 2. CARD: IA E COPYWRITING (GEMINI)
        card_ai = self._criar_card("🤖 Inteligência Artificial (Google Gemini - Opcional)")
        grid_ai = QGridLayout()
        grid_ai.setSpacing(12)

        self.check_use_gemini = QCheckBox("Habilitar Google Gemini para criar copys estilo review/achadinho humanizado")
        grid_ai.addWidget(self.check_use_gemini, 0, 0, 1, 2)

        grid_ai.addWidget(QLabel("Gemini API Key:"), 1, 0)
        self.input_gemini_key = QLineEdit()
        self.input_gemini_key.setEchoMode(QLineEdit.Password)
        self.input_gemini_key.setPlaceholderText("AIzaSy... (deixe vazio para usar templates automáticos gratuitos)")
        grid_ai.addWidget(self.input_gemini_key, 1, 1)

        card_ai.layout().addLayout(grid_ai)
        layout.addWidget(card_ai)

        # 3. CARD: NAVEGADOR & AUTOMAÇÃO
        card_browser = self._criar_card("🌐 Motor do Navegador (Automação Stealth)")
        layout_browser = QVBoxLayout()
        layout_browser.setSpacing(10)

        self.check_headless = QCheckBox("Executar navegador em segundo plano sem janela visível (Modo Oculto / Headless)")
        self.check_headless.setStyleSheet("color: #E5E7EB; font-size: 13px;")
        layout_browser.addWidget(self.check_headless)

        lbl_browser_info = QLabel(
            "💡 Dica: No modo Headless, as postagens acontecem de forma 100% invisível sem interromper seu uso do computador.\n"
            "As contas, sessões de cookies e pastas do Pinterest são gerenciadas exclusivamente na aba '👥 Multi-Contas'."
        )
        lbl_browser_info.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        layout_browser.addWidget(lbl_browser_info)

        card_browser.layout().addLayout(layout_browser)
        layout.addWidget(card_browser)

        # BOTÃO SALVAR GERAL
        self.btn_salvar = QPushButton("💾 Salvar Configurações Globais")
        self.btn_salvar.setCursor(Qt.PointingHandCursor)
        self.btn_salvar.setStyleSheet("background-color: #10B981; color: white; font-size: 14px; font-weight: bold; padding: 12px 24px; border-radius: 8px;")
        self.btn_salvar.clicked.connect(self._salvar_tudo)
        layout.addWidget(self.btn_salvar, alignment=Qt.AlignRight)

        layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _criar_card(self, titulo: str) -> QFrame:
        card = QFrame()
        card.setObjectName("cardPanel")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(12)

        lbl = QLabel(titulo)
        lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #F3F4F6;")
        card_layout.addWidget(lbl)
        return card

    def _carregar_valores(self):
        self.input_shopee_app_id.setText(str(self.cfg.get("shopee_app_id", "")))
        self.input_shopee_secret.setText(str(self.cfg.get("shopee_secret", "")))
        country = self.cfg.get("shopee_country", "BR")
        self.combo_shopee_country.setCurrentIndex(0 if country == "BR" else 1)

        self.check_use_gemini.setChecked(bool(self.cfg.get("use_gemini", True)))
        self.input_gemini_key.setText(str(self.cfg.get("gemini_key", "") or self.cfg.get("gemini_api_key", "")))
        self.check_headless.setChecked(bool(self.cfg.get("browser_headless", True)))

    def _salvar_tudo(self):
        data = {
            "shopee_app_id": self.input_shopee_app_id.text().strip(),
            "shopee_secret": self.input_shopee_secret.text().strip(),
            "shopee_country": "BR" if self.combo_shopee_country.currentIndex() == 0 else "GLOBAL",
            "use_gemini": self.check_use_gemini.isChecked(),
            "gemini_api_key": self.input_gemini_key.text().strip(),
            "gemini_key": self.input_gemini_key.text().strip(),
            "browser_headless": self.check_headless.isChecked(),
        }
        self.cfg.update(data)
        self.sig_log.emit("Configurações globais salvas com sucesso!", "success")
        QMessageBox.information(self, "Sucesso", "Configurações salvas com sucesso!")

    def _testar_shopee(self):
        app_id = self.input_shopee_app_id.text().strip()
        secret = self.input_shopee_secret.text().strip()
        country = "BR" if self.combo_shopee_country.currentIndex() == 0 else "GLOBAL"

        if not app_id or not secret:
            QMessageBox.warning(self, "Atenção", "Preencha o App ID e o Secret da Shopee antes de testar.")
            return

        self.btn_test_shopee.setEnabled(False)
        self.btn_test_shopee.setText("Conectando...")
        try:
            engine = ShopeeEngine(app_id=app_id, secret=secret, country=country)
            res = engine.test_connection()
            if res.get("success"):
                QMessageBox.information(self, "Conexão Shopee", res.get("message"))
                self.sig_log.emit("Conexão com Shopee realizada com sucesso!", "success")
            else:
                QMessageBox.critical(self, "Erro Shopee", res.get("message"))
                self.sig_log.emit(f"Falha ao conectar com Shopee: {res.get('message')}", "error")
        except Exception as e:
            QMessageBox.critical(self, "Erro Shopee", str(e))
            self.sig_log.emit(f"Exceção ao testar Shopee: {e}", "error")
        finally:
            self.btn_test_shopee.setEnabled(True)
            self.btn_test_shopee.setText("⚡ Testar Conexão Shopee")
