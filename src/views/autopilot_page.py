"""
autopilot_page.py
Tela do Piloto Automático (Automação Contínua Anti-Spam):
Monitoramento de execução, controle de início/parada, contagem regressiva,
resumo de postagens do dia e card do último Pin publicado.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QFrame, QProgressBar, QMessageBox, QComboBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QDesktopServices
from PySide6.QtCore import QUrl

from src.models.config_manager import ConfigManager
from src.models.database import Database
from src.workers.worker_autopilot import WorkerAutopilot


class AutopilotPage(QWidget):
    """Página de controle e telemetria da automação autônoma."""

    sig_log = Signal(str, str)

    def __init__(self, config_manager: ConfigManager, database: Database, parent=None):
        super().__init__(parent)
        self.cfg = config_manager
        self.db = database
        self._worker: WorkerAutopilot = None

        self._montar()
        self.atualizar_estatisticas()

    def _montar(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 1. CARDS DE MÉTRICAS (TOPO)
        box_metrics = QHBoxLayout()
        box_metrics.setSpacing(15)

        self.card_status = self._criar_metric_card("STATUS DO ROBÔ", "PARADO", "#EF4444")
        self.card_today = self._criar_metric_card("PINS HOJE", "0 / 12", "#3B82F6")
        self.card_total = self._criar_metric_card("TOTAL PUBLICADOS", "0", "#10B981")
        self.card_timer = self._criar_metric_card("PRÓXIMO DISPARO", "--:--", "#F59E0B")

        box_metrics.addWidget(self.card_status)
        box_metrics.addWidget(self.card_today)
        box_metrics.addWidget(self.card_total)
        box_metrics.addWidget(self.card_timer)
        layout.addLayout(box_metrics)

        # 2. PAINEL DE CONTROLE CENTRAL
        panel_ctrl = QFrame()
        panel_ctrl.setObjectName("cardPanel")
        layout_ctrl = QVBoxLayout(panel_ctrl)
        layout_ctrl.setContentsMargins(20, 20, 20, 20)
        layout_ctrl.setSpacing(15)

        lbl_ctrl = QLabel("⚙️ Controle da Esteira Autônoma")
        lbl_ctrl.setStyleSheet("font-size: 15px; font-weight: bold; color: #F3F4F6;")
        layout_ctrl.addWidget(lbl_ctrl)

        # Seletor de Gerenciamento de Pastas
        box_board_mode = QHBoxLayout()
        box_board_mode.setSpacing(10)
        lbl_bm = QLabel("📁 Distribuição de Pastas:")
        lbl_bm.setStyleSheet("color: #E5E7EB; font-size: 13px; font-weight: 500;")
        box_board_mode.addWidget(lbl_bm)

        self.combo_board_mode = QComboBox()
        self.combo_board_mode.addItem("🔄 Rotacionar Pastas Automaticamente (Recomendado)", "rotate")
        self.combo_board_mode.addItem("🧠 Correspondência Inteligente (Nicho compatível do produto)", "smart")
        self.combo_board_mode.addItem("📌 Pasta Fixa Padrão (Usar somente a selecionada)", "single")
        self.combo_board_mode.setStyleSheet("""
            QComboBox {
                background-color: #1F2937;
                color: #F9FAFB;
                border: 1px solid #4B5563;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
                min-width: 320px;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox QAbstractItemView {
                background-color: #1F2937;
                color: #F9FAFB;
                selection-background-color: #EE4D2D;
            }
        """)

        # Carrega modo salvo no config
        cur_mode = self.cfg.get("board_mode", "rotate")
        for i in range(self.combo_board_mode.count()):
            if self.combo_board_mode.itemData(i) == cur_mode:
                self.combo_board_mode.setCurrentIndex(i)
                break
        self.combo_board_mode.currentIndexChanged.connect(self._on_board_mode_changed)
        box_board_mode.addWidget(self.combo_board_mode)
        box_board_mode.addStretch()
        layout_ctrl.addLayout(box_board_mode)

        self.lbl_info_params = QLabel()
        self.lbl_info_params.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        layout_ctrl.addWidget(self.lbl_info_params)

        box_botoes = QHBoxLayout()
        box_botoes.setSpacing(15)

        self.btn_iniciar = QPushButton("▶ INICIAR PILOTO AUTOMÁTICO")
        self.btn_iniciar.setCursor(Qt.PointingHandCursor)
        self.btn_iniciar.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: white;
                font-size: 15px;
                font-weight: bold;
                padding: 14px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        self.btn_iniciar.clicked.connect(self._iniciar_autopilot)
        box_botoes.addWidget(self.btn_iniciar)

        self.btn_parar = QPushButton("⏹ PARAR AUTOMAÇÃO")
        self.btn_parar.setEnabled(False)
        self.btn_parar.setCursor(Qt.PointingHandCursor)
        self.btn_parar.setStyleSheet("""
            QPushButton {
                background-color: #EF4444;
                color: white;
                font-size: 15px;
                font-weight: bold;
                padding: 14px;
                border-radius: 8px;
            }
            QPushButton:disabled {
                background-color: #374151;
                color: #6B7280;
            }
        """)
        self.btn_parar.clicked.connect(self._parar_autopilot)
        box_botoes.addWidget(self.btn_parar)

        layout_ctrl.addLayout(box_botoes)
        layout.addWidget(panel_ctrl)

        # 3. CARD DO ÚLTIMO PIN PUBLICADO
        self.card_ultimo_pin = QFrame()
        self.card_ultimo_pin.setObjectName("cardPanel")
        layout_up = QHBoxLayout(self.card_ultimo_pin)
        layout_up.setContentsMargins(20, 20, 20, 20)
        layout_up.setSpacing(20)

        self.lbl_last_img = QLabel()
        self.lbl_last_img.setFixedSize(140, 210)
        self.lbl_last_img.setStyleSheet("background: #0B0F19; border: 1px solid #1F2937; border-radius: 8px;")
        self.lbl_last_img.setAlignment(Qt.AlignCenter)
        self.lbl_last_img.setText("Sem imagem")
        layout_up.addWidget(self.lbl_last_img)

        box_last_info = QVBoxLayout()
        box_last_info.setSpacing(10)

        lbl_last_header = QLabel("📌 Último Pin Publicado pelo Robô:")
        lbl_last_header.setStyleSheet("font-size: 14px; font-weight: bold; color: #F3F4F6;")
        box_last_info.addWidget(lbl_last_header)

        self.lbl_last_title = QLabel("Nenhuma postagem realizada nesta sessão.")
        self.lbl_last_title.setWordWrap(True)
        self.lbl_last_title.setStyleSheet("font-size: 13px; color: #E5E7EB;")
        box_last_info.addWidget(self.lbl_last_title)

        self.lbl_last_link = QLabel("")
        self.lbl_last_link.setStyleSheet("color: #3B82F6; font-size: 12px; text-decoration: underline;")
        self.lbl_last_link.setCursor(Qt.PointingHandCursor)
        self.lbl_last_link.mousePressEvent = self._abrir_link_ultimo_pin
        box_last_info.addWidget(self.lbl_last_link)
        box_last_info.addStretch()

        layout_up.addLayout(box_last_info, 1)
        layout.addWidget(self.card_ultimo_pin)
        layout.addStretch()

    def _criar_metric_card(self, titulo: str, valor: str, cor_valor: str) -> QFrame:
        card = QFrame()
        card.setObjectName("cardPanel")
        clayout = QVBoxLayout(card)
        clayout.setContentsMargins(15, 12, 15, 12)
        clayout.setSpacing(4)

        lbl_t = QLabel(titulo)
        lbl_t.setStyleSheet("font-size: 11px; font-weight: bold; color: #9CA3AF;")
        clayout.addWidget(lbl_t)

        lbl_v = QLabel(valor)
        lbl_v.setObjectName(f"val_{titulo}")
        lbl_v.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {cor_valor};")
        clayout.addWidget(lbl_v)
        return card

    def atualizar_estatisticas(self):
        pins_today = self.db.get_pins_posted_today_count()
        max_daily = self.cfg.get("max_pins_per_day", 12)
        total_pins = self.db.get_total_pins_count()

        lbl_today = self.card_today.findChild(QLabel, "val_PINS HOJE")
        if lbl_today:
            lbl_today.setText(f"{pins_today} / {max_daily}")

        lbl_tot = self.card_total.findChild(QLabel, "val_TOTAL PUBLICADOS")
        if lbl_tot:
            lbl_tot.setText(str(total_pins))

        interval = self.cfg.get("auto_interval_minutes", 45)
        jitter = self.cfg.get("auto_jitter_minutes", 15)
        keywords = self.cfg.get("search_keywords", "geral")
        board_name = self.cfg.get("pinterest_board_name", "Nenhum board configurado")
        board_mode = self.cfg.get("board_mode", "rotate")

        mode_labels = {
            "rotate": "🔄 Rotação Automática (Todas as Pastas)",
            "smart": "🧠 Nicho Inteligente",
            "single": f"📌 Pasta Fixa ({board_name})"
        }
        mode_desc = mode_labels.get(board_mode, "🔄 Rotação Automática")

        self.lbl_info_params.setText(
            f"📁 Distribuição: <b>{mode_desc}</b> | ⏱ Intervalo: <b>{interval} min (±{jitter} min)</b> | 🏷 Termos: <b>{keywords}</b>"
        )

    def _on_board_mode_changed(self, index: int):
        new_mode = self.combo_board_mode.itemData(index)
        self.cfg.set("board_mode", new_mode)
        self.cfg.save()
        self.atualizar_estatisticas()
        self.sig_log.emit(f"⚙️ Modo de distribuição de pastas atualizado para: '{new_mode}'", "info")

    def _iniciar_autopilot(self):
        # Validações antes de iniciar
        board_id = self.cfg.get("pinterest_board_id", "")
        token = self.cfg.get("pinterest_access_token", "")
        if not board_id or not token:
            QMessageBox.warning(self, "Atenção", "Configure o Access Token e a Pasta do Pinterest nas Configurações antes de ligar o robô.")
            return

        self.btn_iniciar.setEnabled(False)
        self.btn_parar.setEnabled(True)

        lbl_st = self.card_status.findChild(QLabel, "val_STATUS DO ROBÔ")
        if lbl_st:
            lbl_st.setText("ATIVO")
            lbl_st.setStyleSheet("font-size: 20px; font-weight: bold; color: #10B981;")

        self._worker = WorkerAutopilot(self.cfg, self.db)
        self._worker.sig_log.connect(self.sig_log.emit)
        self._worker.sig_pin_published.connect(self._on_pin_published)
        self._worker.sig_status.connect(self._on_worker_status)
        self._worker.sig_finished.connect(self._on_worker_finished)
        self._worker.start()

    def _parar_autopilot(self):
        if self._worker:
            self._worker.stop()
        self.btn_parar.setEnabled(False)
        self.btn_iniciar.setEnabled(True)

    def _on_worker_status(self, status_text: str):
        lbl_tim = self.card_timer.findChild(QLabel, "val_PRÓXIMO DISPARO")
        if lbl_tim:
            lbl_tim.setText(status_text)

    def _on_worker_finished(self):
        self.btn_parar.setEnabled(False)
        self.btn_iniciar.setEnabled(True)
        lbl_st = self.card_status.findChild(QLabel, "val_STATUS DO ROBÔ")
        if lbl_st:
            lbl_st.setText("PARADO")
            lbl_st.setStyleSheet("font-size: 20px; font-weight: bold; color: #EF4444;")
        self.atualizar_estatisticas()

    def _on_pin_published(self, data: dict):
        self.atualizar_estatisticas()
        title = data.get("title", "")
        url = data.get("url", "")
        img_path = data.get("image_path", "")

        self.lbl_last_title.setText(title)
        self.lbl_last_link.setText(url)
        self._last_pin_url = url

        if img_path and Path(img_path).exists():
            pix = QPixmap(img_path)
            self.lbl_last_img.setPixmap(pix.scaled(
                self.lbl_last_img.width(),
                self.lbl_last_img.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            ))

    def _abrir_link_ultimo_pin(self, event):
        url = getattr(self, "_last_pin_url", "")
        if url:
            QDesktopServices.openUrl(QUrl(url))