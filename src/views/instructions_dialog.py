"""
instructions_dialog.py
Modal de instruções e checklist interativo para configuração do AutoLink Pinterest:
- Credenciais da Shopee Open Platform (Afiliados)
- Credenciais da Pinterest Developer API v5
- Boas práticas para evitar punição de spam no Pinterest
"""
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QPushButton, QScrollArea, QWidget, QFrame, QProgressBar
)
from PySide6.QtCore import Qt

from src.models.config_manager import ConfigManager


class InstructionsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📖 Guia de Configuração e Boas Práticas - AutoLink Pinterest")
        self.setMinimumSize(780, 580)
        self.cfg = ConfigManager()
        self.progress = self.cfg.get("tutorial_progress", {})

        self.checkboxes = []
        self._setup_ui()
        self._update_progress()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Cabeçalho
        header_layout = QVBoxLayout()
        title = QLabel("🚀 Guia Passo a Passo: AutoLink Pinterest")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #EE4D2D;")
        
        self.lbl_progress = QLabel("Progresso do Setup: 0%")
        self.lbl_progress.setStyleSheet("font-size: 13px; color: #9CA3AF;")
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: none; border-radius: 4px; background-color: #374151; }
            QProgressBar::chunk { background-color: #10B981; border-radius: 4px; }
        """)

        header_layout.addWidget(title)
        header_layout.addWidget(self.lbl_progress)
        header_layout.addWidget(self.progress_bar)
        main_layout.addLayout(header_layout)

        # Área de Rolagem com os Passos
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #1F2937; border-radius: 8px; background: #0B0F19; }")
        
        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setSpacing(16)

        # ETAPA 1: SHOPEE AFFILIATE OPEN API
        self._add_step(
            "step_shopee",
            "1. Credenciais Oficiais da Shopee (Open Platform)",
            "Acesse o portal oficial <b>affiliate.shopee.com.br</b> (ou Shopee Open Platform) e solicite sua chave de API.<br>"
            "Você receberá um <b>App ID</b> e um <b>Secret</b>.<br>"
            "Insira ambos na aba <i>Configurações</i> do programa e teste a conexão.",
            "Já configurei meu App ID e Secret da Shopee"
        )

        # ETAPA 2: PINTEREST DEVELOPER API V5
        self._add_step(
            "step_pinterest",
            "2. Aplicativo no Pinterest Developers",
            "Acesse <b>developers.pinterest.com</b> com a sua conta do Pinterest.<br>"
            "Crie um aplicativo gratuito para obter o seu <b>Access Token</b> com permissão de criação de Pins (<code>pins:write</code>, <code>boards:read</code>).<br>"
            "Cole o token nas <i>Configurações</i> e clique em <i>Atualizar Pastas</i> para selecionar onde os Pins serão salvos.",
            "Já gerei meu Access Token e selecionei a Pasta do Pinterest"
        )

        # ETAPA 3: COPYWRITING & INTELIGÊNCIA ARTIFICIAL
        self._add_step(
            "step_copy",
            "3. Copywriting e SEO (Opcional - Google Gemini)",
            "O programa já vem de fábrica com <b>Templates Dinâmicos de Alta Conversão</b> que não custam nada e funcionam 100% offline.<br>"
            "Se você quiser copys reescritas com IA, pegue uma chave gratuita no <b>Google AI Studio</b> (airstudio.google.com) e ative a opção nas Configurações.",
            "Entendi como funciona a geração de textos e títulos"
        )

        # ETAPA 4: POLÍTICA ANTI-SPAM
        self._add_step(
            "step_antispam",
            "4. Regras de Ouro Anti-Spam do Pinterest",
            "O Pinterest prioriza contas com postagens consistentes e visual de alta qualidade.<br>"
            "• Mantenha o robô configurado entre <b>5 a 15 pins por dia</b>.<br>"
            "• Deixe o intervalo entre <b>30 a 60 minutos</b> para manter o ritmo humanizado.<br>"
            "• O sistema possui deduplicação automática no banco SQLite para nunca postar o mesmo item duas vezes.",
            "Estou ciente das boas práticas para proteger minha conta do Pinterest"
        )

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        # Botão Fechar
        btn_close = QPushButton("Entendido, Fechar")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet("background-color: #10B981; color: white; font-weight: bold; padding: 10px 20px; border-radius: 6px;")
        btn_close.clicked.connect(self.accept)
        main_layout.addWidget(btn_close, alignment=Qt.AlignRight)

    def _add_step(self, step_id: str, title: str, desc: str, check_label: str):
        card = QFrame()
        card.setStyleSheet("background-color: #111827; border: 1px solid #1F2937; border-radius: 8px; padding: 12px;")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(8)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #F3F4F6;")
        card_layout.addWidget(lbl_title)

        lbl_desc = QLabel(desc)
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("font-size: 12px; color: #9CA3AF; line-height: 1.4;")
        card_layout.addWidget(lbl_desc)

        cb = QCheckBox(check_label)
        cb.setCursor(Qt.PointingHandCursor)
        cb.setStyleSheet("color: #E5E7EB; font-weight: 500;")
        cb.setChecked(self.progress.get(step_id, False))
        cb.stateChanged.connect(lambda state, sid=step_id: self._on_check_changed(sid, state))
        card_layout.addWidget(cb)

        self.checkboxes.append(cb)
        self.content_layout.addWidget(card)

    def _on_check_changed(self, step_id: str, state: int):
        self.progress[step_id] = (state == Qt.Checked.value)
        self.cfg.set("tutorial_progress", self.progress)
        self.cfg.save()
        self._update_progress()

    def _update_progress(self):
        total = len(self.checkboxes)
        if total == 0:
            return
        checked = sum(1 for cb in self.checkboxes if cb.isChecked())
        pct = int((checked / total) * 100)
        self.lbl_progress.setText(f"Progresso do Setup: {pct}%")
        self.progress_bar.setValue(pct)
