"""
settings_page.py
Página de Configurações do AutoLink Pinterest:
Credenciais da Shopee Open Platform, Pinterest API v5, Google Gemini,
seleção de Board padrão e parâmetros anti-spam.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QSpinBox, QCheckBox, QFrame, QScrollArea, QMessageBox
)
from PySide6.QtCore import Qt, Signal

from src.models.config_manager import ConfigManager
from src.engines.shopee_engine import ShopeeEngine
from src.engines.pinterest_engine import PinterestEngine
from src.workers.worker_manual import WorkerBrowserLogin


class SettingsPage(QWidget):
    """Página de credenciais e parâmetros operacionais."""

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
        card_shopee = self._criar_card("🛍️ Shopee Affiliate Open API (Oficial)")
        grid_shopee = QGridLayout()
        grid_shopee.setSpacing(12)

        grid_shopee.addWidget(QLabel("App ID / Key:"), 0, 0)
        self.input_shopee_app_id = QLineEdit()
        self.input_shopee_app_id.setPlaceholderText("Ex: 123456789")
        grid_shopee.addWidget(self.input_shopee_app_id, 0, 1)

        grid_shopee.addWidget(QLabel("API Secret:"), 1, 0)
        self.input_shopee_secret = QLineEdit()
        self.input_shopee_secret.setEchoMode(QLineEdit.Password)
        self.input_shopee_secret.setPlaceholderText("Chave secreta oficial fornecida pela Shopee")
        grid_shopee.addWidget(self.input_shopee_secret, 1, 1)

        grid_shopee.addWidget(QLabel("País:"), 2, 0)
        self.combo_shopee_country = QComboBox()
        self.combo_shopee_country.addItems(["Brasil (BR)", "Global"])
        grid_shopee.addWidget(self.combo_shopee_country, 2, 1)

        self.btn_test_shopee = QPushButton("⚡ Testar Conexão Shopee")
        self.btn_test_shopee.setCursor(Qt.PointingHandCursor)
        self.btn_test_shopee.setStyleSheet("background-color: #EE4D2D; color: white; font-weight: bold; padding: 8px 16px; border-radius: 6px;")
        self.btn_test_shopee.clicked.connect(self._testar_shopee)
        grid_shopee.addWidget(self.btn_test_shopee, 3, 1, alignment=Qt.AlignLeft)

        card_shopee.layout().addLayout(grid_shopee)
        layout.addWidget(card_shopee)

        # 2. CARD: PINTEREST (NAVEGADOR OU API v5)
        card_pin = self._criar_card("📌 Configurações de Postagem no Pinterest")
        grid_pin = QGridLayout()
        grid_pin.setSpacing(12)

        grid_pin.addWidget(QLabel("Método de Publicação:"), 0, 0)
        self.combo_post_method = QComboBox()
        self.combo_post_method.addItem("🌐 Navegador Automatizado Playwright (Sem aprovação - Imediato)", "browser")
        self.combo_post_method.addItem("⚡ API Oficial v5 (Requer Standard Access aprovado)", "api")
        self.combo_post_method.setStyleSheet("background-color: #1F2937; color: white; padding: 6px; border-radius: 4px;")
        grid_pin.addWidget(self.combo_post_method, 0, 1)

        self.btn_browser_login = QPushButton("🔑 Conectar Conta / Fazer Login no Pinterest (Abrir Navegador)")
        self.btn_browser_login.setCursor(Qt.PointingHandCursor)
        self.btn_browser_login.setStyleSheet("background-color: #E60023; color: white; font-weight: bold; padding: 10px 18px; border-radius: 6px;")
        self.btn_browser_login.clicked.connect(self._abrir_login_navegador)
        grid_pin.addWidget(self.btn_browser_login, 1, 1, alignment=Qt.AlignLeft)

        self.check_headless = QCheckBox("Executar navegador em segundo plano sem janela visível (Headless)")
        grid_pin.addWidget(self.check_headless, 2, 1)

        grid_pin.addWidget(QLabel("Access Token (API v5):"), 3, 0)
        self.input_pin_token = QLineEdit()
        self.input_pin_token.setEchoMode(QLineEdit.Password)
        self.input_pin_token.setPlaceholderText("pina_... (necessário apenas para modo API)")
        grid_pin.addWidget(self.input_pin_token, 3, 1)

        grid_pin.addWidget(QLabel("Pasta do Pinterest (Board):"), 4, 0)
        box_board = QHBoxLayout()
        self.combo_pin_board = QComboBox()
        self.combo_pin_board.setEditable(True)
        self.combo_pin_board.setMinimumWidth(260)
        box_board.addWidget(self.combo_pin_board)

        self.btn_carregar_boards = QPushButton("🔄 Atualizar Pastas (API)")
        self.btn_carregar_boards.setCursor(Qt.PointingHandCursor)
        self.btn_carregar_boards.clicked.connect(self._carregar_boards_pinterest)
        box_board.addWidget(self.btn_carregar_boards)
        grid_pin.addLayout(box_board, 4, 1)

        self.btn_test_pin = QPushButton("⚡ Testar Token da API")
        self.btn_test_pin.setCursor(Qt.PointingHandCursor)
        self.btn_test_pin.setStyleSheet("background-color: #374151; color: white; font-weight: bold; padding: 8px 16px; border-radius: 6px;")
        self.btn_test_pin.clicked.connect(self._testar_pinterest)
        grid_pin.addWidget(self.btn_test_pin, 5, 1, alignment=Qt.AlignLeft)

        card_pin.layout().addLayout(grid_pin)
        layout.addWidget(card_pin)

        # 3. CARD: IA E COPYWRITING (GEMINI)
        card_ai = self._criar_card("🤖 Inteligência Artificial (Google Gemini - Opcional)")
        grid_ai = QGridLayout()
        grid_ai.setSpacing(12)

        self.check_use_gemini = QCheckBox("Habilitar Google Gemini para criar copys estilo review/achadinho")
        grid_ai.addWidget(self.check_use_gemini, 0, 0, 1, 2)

        grid_ai.addWidget(QLabel("Gemini API Key:"), 1, 0)
        self.input_gemini_key = QLineEdit()
        self.input_gemini_key.setEchoMode(QLineEdit.Password)
        self.input_gemini_key.setPlaceholderText("AIzaSy...")
        grid_ai.addWidget(self.input_gemini_key, 1, 1)

        card_ai.layout().addLayout(grid_ai)
        layout.addWidget(card_ai)

        # 4. CARD: PARÂMETROS ANTI-SPAM & PILOTO AUTOMÁTICO
        card_anti_spam = self._criar_card("🛡️ Política Anti-Spam & Parâmetros do Autopilot")
        grid_spam = QGridLayout()
        grid_spam.setSpacing(12)

        grid_spam.addWidget(QLabel("Intervalo Médio (Minutos):"), 0, 0)
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(10, 360)
        self.spin_interval.setValue(45)
        self.spin_interval.setSuffix(" min")
        grid_spam.addWidget(self.spin_interval, 0, 1)

        grid_spam.addWidget(QLabel("Variação Randômica (Jitter):"), 1, 0)
        self.spin_jitter = QSpinBox()
        self.spin_jitter.setRange(0, 60)
        self.spin_jitter.setValue(15)
        self.spin_jitter.setSuffix(" min (+/-)")
        grid_spam.addWidget(self.spin_jitter, 1, 1)

        grid_spam.addWidget(QLabel("Limite Máximo Diário de Pins:"), 2, 0)
        self.spin_max_daily = QSpinBox()
        self.spin_max_daily.setRange(1, 50)
        self.spin_max_daily.setValue(12)
        self.spin_max_daily.setSuffix(" pins/dia")
        grid_spam.addWidget(self.spin_max_daily, 2, 1)

        grid_spam.addWidget(QLabel("Palavras-chave de busca:"), 3, 0)
        self.input_keywords = QLineEdit()
        self.input_keywords.setPlaceholderText("achadinhos, organizador, cozinha, utilidades, decoracao")
        grid_spam.addWidget(self.input_keywords, 3, 1)

        card_anti_spam.layout().addLayout(grid_spam)
        layout.addWidget(card_anti_spam)

        # BOTÃO SALVAR GERAL
        self.btn_salvar = QPushButton("💾 Salvar Todas as Configurações")
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

        cur_post_method = self.cfg.get("post_method", "browser")
        self.combo_post_method.setCurrentIndex(0 if cur_post_method == "browser" else 1)
        self.check_headless.setChecked(bool(self.cfg.get("browser_headless", False)))

        self.input_pin_token.setText(str(self.cfg.get("pinterest_access_token", "")))
        saved_board_id = str(self.cfg.get("pinterest_board_id", ""))
        saved_board_name = str(self.cfg.get("pinterest_board_name", "Pasta Padrão"))
        if saved_board_id or saved_board_name:
            self.combo_pin_board.addItem(saved_board_name, saved_board_id)
            self.combo_pin_board.setEditText(saved_board_name)

        self.check_use_gemini.setChecked(bool(self.cfg.get("use_gemini", True)))
        self.input_gemini_key.setText(str(self.cfg.get("gemini_key", "") or self.cfg.get("gemini_api_key", "")))

        self.spin_interval.setValue(int(self.cfg.get("auto_interval_minutes", 45)))
        self.spin_jitter.setValue(int(self.cfg.get("auto_jitter_minutes", 15)))
        self.spin_max_daily.setValue(int(self.cfg.get("max_pins_per_day", 12)))
        self.input_keywords.setText(str(self.cfg.get("search_keywords", "achadinhos, organizador, cozinha, decoracao")))

    def _abrir_login_navegador(self):
        self.btn_browser_login.setEnabled(False)
        self.btn_browser_login.setText("Aguardando login no navegador aberto...")
        self.sig_log.emit("Abrindo janela do Chromium para login no Pinterest...", "info")

        self._worker_login = WorkerBrowserLogin()
        self._worker_login.sig_result.connect(self._on_browser_login_finished)
        self._worker_login.start()

    def _on_browser_login_finished(self, res: dict):
        self.btn_browser_login.setEnabled(True)
        self.btn_browser_login.setText("🔑 Conectar Conta / Fazer Login no Pinterest (Abrir Navegador)")
        if res.get("success"):
            QMessageBox.information(self, "Login Pinterest", res.get("message"))
            self.sig_log.emit("Sessão do Pinterest no navegador salva com sucesso!", "success")
        else:
            QMessageBox.warning(self, "Aviso", res.get("message", "Login não concluído."))
            self.sig_log.emit(f"Aviso no login do navegador: {res.get('message')}", "warning")

    def _salvar_tudo(self):
        board_id = self.combo_pin_board.currentData() or ""
        board_name = self.combo_pin_board.currentText() or ""

        data = {
            "shopee_app_id": self.input_shopee_app_id.text().strip(),
            "shopee_secret": self.input_shopee_secret.text().strip(),
            "shopee_country": "BR" if self.combo_shopee_country.currentIndex() == 0 else "GLOBAL",
            "post_method": self.combo_post_method.currentData() or "browser",
            "browser_headless": self.check_headless.isChecked(),
            "pinterest_access_token": self.input_pin_token.text().strip(),
            "pinterest_board_id": board_id,
            "pinterest_board_name": board_name,
            "use_gemini": self.check_use_gemini.isChecked(),
            "gemini_api_key": self.input_gemini_key.text().strip(),
            "gemini_key": self.input_gemini_key.text().strip(),
            "auto_interval_minutes": self.spin_interval.value(),
            "auto_jitter_minutes": self.spin_jitter.value(),
            "max_pins_per_day": self.spin_max_daily.value(),
            "search_keywords": self.input_keywords.text().strip()
        }
        self.cfg.update(data)
        self.sig_log.emit("Configurações salvas com sucesso!", "success")
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

    def _testar_pinterest(self):
        token = self.input_pin_token.text().strip()
        if not token:
            QMessageBox.warning(self, "Atenção", "Preencha o Access Token do Pinterest antes de testar.")
            return

        self.btn_test_pin.setEnabled(False)
        self.btn_test_pin.setText("Verificando...")
        try:
            engine = PinterestEngine(access_token=token)
            res = engine.test_connection()
            if res.get("success"):
                QMessageBox.information(self, "Pinterest Conectado", res.get("message"))
                self.sig_log.emit(f"Pinterest: {res.get('message')}", "success")
                self._carregar_boards_pinterest()
            else:
                QMessageBox.critical(self, "Erro Pinterest", res.get("message"))
                self.sig_log.emit(f"Pinterest: {res.get('message')}", "error")
        except Exception as e:
            QMessageBox.critical(self, "Erro Pinterest", str(e))
        finally:
            self.btn_test_pin.setEnabled(True)
            self.btn_test_pin.setText("⚡ Testar Conexão Pinterest")

    def _carregar_boards_pinterest(self):
        token = self.input_pin_token.text().strip()
        if not token:
            return
        engine = PinterestEngine(access_token=token)
        boards = engine.get_boards()
        if boards:
            current_id = self.combo_pin_board.currentData()
            self.combo_pin_board.clear()
            selected_idx = 0
            for idx, b in enumerate(boards):
                self.combo_pin_board.addItem(b["name"], b["id"])
                if b["id"] == current_id:
                    selected_idx = idx
            self.combo_pin_board.setCurrentIndex(selected_idx)
            self.sig_log.emit(f"{len(boards)} pasta(s) do Pinterest carregadas.", "info")
        else:
            self.sig_log.emit("Nenhuma pasta encontrada no Pinterest ou token inválido.", "warning")

