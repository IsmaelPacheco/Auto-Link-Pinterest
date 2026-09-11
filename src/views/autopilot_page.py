"""
autopilot_page.py
Tela do Piloto Automático (Automação Contínua Anti-Spam):
Monitoramento de execução, controle de início/parada, contagem regressiva,
parâmetros operacionais (janela de horários, formato de mídia e distribuição de pastas)
e card do último Pin publicado.
"""
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QFrame, QProgressBar, QMessageBox, QComboBox, QSpinBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QDesktopServices
from PySide6.QtCore import QUrl

from src.models.config_manager import ConfigManager
from src.models.database import Database
from src.models.account_manager import AccountManager
from src.workers.worker_autopilot import WorkerAutopilot


class AutopilotPage(QWidget):
    """Página de controle operacional e telemetria da automação autônoma."""

    sig_log = Signal(str, str)

    def __init__(self, config_manager: ConfigManager, database: Database, parent=None):
        super().__init__(parent)
        self.cfg = config_manager
        self.db = database
        self.am = AccountManager()
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
        self.card_today = self._criar_metric_card("PINS HOJE", "0 / 0", "#3B82F6")
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
        layout_ctrl.setSpacing(14)

        lbl_ctrl = QLabel("⚙️ Controle da Esteira Autônoma")
        lbl_ctrl.setStyleSheet("font-size: 15px; font-weight: bold; color: #F3F4F6;")
        layout_ctrl.addWidget(lbl_ctrl)

        # Linha 1: Pastas e Formato de Mídia
        row_settings_1 = QHBoxLayout()
        row_settings_1.setSpacing(15)

        # Distribuição de Pastas
        box_bm = QHBoxLayout()
        box_bm.setSpacing(8)
        lbl_bm = QLabel("📁 Pastas:")
        lbl_bm.setStyleSheet("color: #E5E7EB; font-size: 13px; font-weight: bold;")
        box_bm.addWidget(lbl_bm)

        self.combo_board_mode = QComboBox()
        self.combo_board_mode.addItem("🔄 Rotacionar Pastas Automaticamente", "rotate")
        self.combo_board_mode.addItem("🧠 Correspondência Inteligente de Nicho", "smart")
        self.combo_board_mode.addItem("📌 Pasta Fixa Padrão", "single")
        self.combo_board_mode.setStyleSheet("""
            QComboBox {
                background-color: #1F2937; color: #F9FAFB; border: 1px solid #4B5563;
                border-radius: 6px; padding: 6px 10px; font-size: 12px; min-width: 250px;
            }
        """)
        cur_mode = self.cfg.get("board_mode", "rotate")
        for i in range(self.combo_board_mode.count()):
            if self.combo_board_mode.itemData(i) == cur_mode:
                self.combo_board_mode.setCurrentIndex(i)
                break
        self.combo_board_mode.currentIndexChanged.connect(self._on_board_mode_changed)
        box_bm.addWidget(self.combo_board_mode)
        row_settings_1.addLayout(box_bm)

        # Formato de Mídia
        box_fmt = QHBoxLayout()
        box_fmt.setSpacing(8)
        lbl_fmt = QLabel("🎬 Mídia:")
        lbl_fmt.setStyleSheet("color: #E5E7EB; font-size: 13px; font-weight: bold;")
        box_fmt.addWidget(lbl_fmt)

        self.combo_post_format = QComboBox()
        self.combo_post_format.addItem("🎲 Híbrido: 50% Vídeos & 50% Imagens", "hybrid")
        self.combo_post_format.addItem("🎬 Apenas Vídeos Animados (.MP4)", "video")
        self.combo_post_format.addItem("📌 Apenas Imagens Estáticas (1000x1500)", "image")
        self.combo_post_format.setStyleSheet("""
            QComboBox {
                background-color: #1F2937; color: #F9FAFB; border: 1px solid #4B5563;
                border-radius: 6px; padding: 6px 10px; font-size: 12px; min-width: 240px;
            }
        """)
        cur_fmt = self.cfg.get("post_format", "hybrid")
        for i in range(self.combo_post_format.count()):
            if self.combo_post_format.itemData(i) == cur_fmt:
                self.combo_post_format.setCurrentIndex(i)
                break
        self.combo_post_format.currentIndexChanged.connect(self._on_post_format_changed)
        box_fmt.addWidget(self.combo_post_format)
        row_settings_1.addLayout(box_fmt)
        row_settings_1.addStretch()
        layout_ctrl.addLayout(row_settings_1)

        # Linha 2: Janela de Atividade Diária
        row_settings_2 = QHBoxLayout()
        row_settings_2.setSpacing(12)

        lbl_janela = QLabel("⏰ Janela Diária:")
        lbl_janela.setStyleSheet("color: #E5E7EB; font-size: 13px; font-weight: bold;")
        row_settings_2.addWidget(lbl_janela)

        lbl_de = QLabel("Das")
        lbl_de.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        row_settings_2.addWidget(lbl_de)

        self.spin_start_hour = QSpinBox()
        self.spin_start_hour.setRange(0, 23)
        self.spin_start_hour.setValue(int(self.cfg.get("day_start_hour", 8)))
        self.spin_start_hour.setSuffix(":00 h")
        self.spin_start_hour.setStyleSheet("background-color: #1F2937; color: white; padding: 5px; border-radius: 4px;")
        self.spin_start_hour.valueChanged.connect(self._on_hours_changed)
        row_settings_2.addWidget(self.spin_start_hour)

        lbl_ate = QLabel("às")
        lbl_ate.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        row_settings_2.addWidget(lbl_ate)

        self.spin_end_hour = QSpinBox()
        self.spin_end_hour.setRange(1, 24)
        self.spin_end_hour.setValue(int(self.cfg.get("day_end_hour", 22)))
        self.spin_end_hour.setSuffix(":00 h")
        self.spin_end_hour.setStyleSheet("background-color: #1F2937; color: white; padding: 5px; border-radius: 4px;")
        self.spin_end_hour.valueChanged.connect(self._on_hours_changed)
        row_settings_2.addWidget(self.spin_end_hour)

        lbl_madrugada = QLabel("(Pausa automática na madrugada para proteção anti-spam)")
        lbl_madrugada.setStyleSheet("color: #6B7280; font-size: 11px;")
        row_settings_2.addWidget(lbl_madrugada)
        row_settings_2.addStretch()
        layout_ctrl.addLayout(row_settings_2)

        # Linha 3: Resumo Informativo Dinâmico
        self.lbl_info_params = QLabel()
        self.lbl_info_params.setStyleSheet("""
            QLabel {
                background-color: #0F172A;
                border: 1px solid #1E293B;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 12px;
                color: #38BDF8;
            }
        """)
        layout_ctrl.addWidget(self.lbl_info_params)

        # Linha 4: Botões Iniciar / Parar
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

        box_links = QHBoxLayout()
        self.lbl_last_link = QLabel("-")
        self.lbl_last_link.setStyleSheet("color: #EE4D2D; font-size: 12px; text-decoration: underline;")
        self.lbl_last_link.setCursor(Qt.PointingHandCursor)
        self.lbl_last_link.mousePressEvent = self._abrir_link_ultimo_pin
        box_links.addWidget(self.lbl_last_link)
        box_links.addStretch()
        box_last_info.addLayout(box_links)

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
        active_accs = self.am.get_active_accounts()
        if active_accs:
            total_max_daily = sum(acc.max_pins_per_day for acc in active_accs)
            acc_names = ", ".join(acc.name for acc in active_accs)
            acc_count = len(active_accs)
        else:
            total_max_daily = int(self.cfg.get("max_pins_per_day", 10))
            acc_names = "Nenhuma ativa (configure em 'Multi-Contas')"
            acc_count = 0

        pins_today = self.db.get_pins_posted_today_count()
        total_pins = self.db.get_total_pins_count()

        lbl_today = self.card_today.findChild(QLabel, "val_PINS HOJE")
        if lbl_today:
            lbl_today.setText(f"{pins_today} / {total_max_daily}")

        lbl_tot = self.card_total.findChild(QLabel, "val_TOTAL PUBLICADOS")
        if lbl_tot:
            lbl_tot.setText(str(total_pins))

        start_h = self.spin_start_hour.value()
        end_h = self.spin_end_hour.value()
        total_h = max(1, end_h - start_h)
        avg_m = (total_h * 60) // max(1, total_max_daily)
        per_acc_pause = avg_m * max(1, acc_count)

        self.lbl_info_params.setText(
            f"👥 <b>{acc_count} Conta(s) Ativa(s):</b> {acc_names} | "
            f"🎯 <b>Capacidade Somada:</b> {total_max_daily} pins/dia<br>"
            f"⏰ <b>Janela Ativa:</b> {start_h:02d}:00 às {end_h:02d}:00 ({total_h}h) • "
            f"⚡ <b>Ritmo:</b> 1 pin publicado a cada <b>~{avg_m} min</b> "
            f"(cada conta descansa <b>~{per_acc_pause} min</b> entre suas postagens)"
        )

    def _on_board_mode_changed(self, index: int):
        new_mode = self.combo_board_mode.itemData(index)
        self.cfg.set("board_mode", new_mode)
        self.cfg.save()
        self.atualizar_estatisticas()
        self.sig_log.emit(f"⚙️ Modo de distribuição de pastas: '{new_mode}'", "info")

    def _on_post_format_changed(self, index: int):
        new_fmt = self.combo_post_format.itemData(index)
        self.cfg.set("post_format", new_fmt)
        self.cfg.save()
        self.atualizar_estatisticas()
        self.sig_log.emit(f"⚙️ Formato de mídia atualizado: '{new_fmt}'", "info")

    def _on_hours_changed(self):
        start = self.spin_start_hour.value()
        end = self.spin_end_hour.value()
        if end <= start:
            self.spin_end_hour.setValue(min(24, start + 1))
            end = self.spin_end_hour.value()

        self.cfg.set("day_start_hour", start)
        self.cfg.set("day_end_hour", end)
        self.cfg.save()
        self.atualizar_estatisticas()

    def _iniciar_autopilot(self):
        active_accs = self.am.get_active_accounts()
        if not active_accs:
            QMessageBox.warning(
                self,
                "Nenhuma Conta Ativa",
                "Nenhuma conta do Pinterest está marcada como ativa no Piloto Automático.\n\n"
                "Acesse a aba '👥 Multi-Contas' no menu lateral e ative pelo menos uma conta."
            )
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
            if str(img_path).lower().endswith((".mp4", ".mov", ".m4v")):
                self.lbl_last_img.setText("🎬 Vídeo Animado\n(Publicado)")
                self.lbl_last_img.setStyleSheet("color: #10B981; font-weight: bold; font-size: 13px; text-align: center; border: 2px dashed #10B981; border-radius: 8px;")
            else:
                pix = QPixmap(img_path)
                if not pix.isNull():
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