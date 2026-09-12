"""
vitrine_page.py
Página de Gerenciamento da Vitrine Web de Achadinhos e Automação de Comentários do TikTok.
Permite sincronizar o catálogo online, abrir a vitrine no navegador, copiar o link da bio
e gerenciar o bot de respostas para quem comentar 'EU QUERO' no TikTok.
"""
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QMessageBox, QDialog, QTextEdit, QGridLayout
)
from PySide6.QtCore import Qt, Signal, QThread, QUrl
from PySide6.QtGui import QDesktopServices

from src.models.database import Database
from src.engines.vitrine_engine import VitrineEngine
from src.engines.tiktok_comment_engine import TikTokCommentEngine


class WorkerTikTokLogin(QThread):
    """Executa o login do TikTok no navegador dedicado."""
    sig_result = Signal(dict)

    def run(self):
        engine = TikTokCommentEngine()
        res = engine.open_login_window()
        self.sig_result.emit(res)


class VitrinePage(QWidget):
    """Página de controle da Vitrine de Achadinhos e TikTok."""

    sig_log = Signal(str, str)

    def __init__(self, database: Database, parent=None):
        super().__init__(parent)
        self.db = database
        self.ve = VitrineEngine(self.db)
        self.tiktok_engine = TikTokCommentEngine()
        self._worker_login = None

        self._montar()
        self.atualizar_status()

    def _montar(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(18)

        # 1. CARDS DE MÉTRICAS / TOPO
        box_metrics = QHBoxLayout()
        box_metrics.setSpacing(15)

        self.card_total_vitrine = self._criar_metric_card("ACHADINHOS NA VITRINE", "0 itens", "#EE4D2D")
        self.card_status_sync = self._criar_metric_card("STATUS DA VITRINE", "SINCRONIZADA", "#10B981")
        self.card_status_tiktok = self._criar_metric_card("CONEXÃO TIKTOK", "VERIFICANDO", "#3B82F6")

        box_metrics.addWidget(self.card_total_vitrine)
        box_metrics.addWidget(self.card_status_sync)
        box_metrics.addWidget(self.card_status_tiktok)
        layout.addLayout(box_metrics)

        # 2. CARD: VITRINE PRÓPRIA DE ACHADINHOS (MOBILE-FIRST)
        card_vitrine = self._criar_card("🛍️ Sua Vitrine Web de Achadinhos (100% Gratuita)")
        layout_vitrine = QVBoxLayout()
        layout_vitrine.setSpacing(14)

        lbl_desc = QLabel(
            "A sua vitrine é uma página web mobile-first onde seus seguidores encontram o link exato de cada "
            "achadinho digitando apenas o número do vídeo (ex: <b>#42</b>). O robô atualiza automaticamente a cada postagem!"
        )
        lbl_desc.setStyleSheet("color: #D1D5DB; font-size: 13px; line-height: 1.4;")
        lbl_desc.setWordWrap(True)
        layout_vitrine.addWidget(lbl_desc)

        # Links e Ações
        box_actions = QHBoxLayout()
        box_actions.setSpacing(12)

        btn_abrir_local = QPushButton("🌐 Abrir Vitrine no Navegador")
        btn_abrir_local.setCursor(Qt.PointingHandCursor)
        btn_abrir_local.setStyleSheet("""
            QPushButton {
                background-color: #EE4D2D;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 8px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #D03B1C;
            }
        """)
        btn_abrir_local.clicked.connect(self._abrir_vitrine_navegador)
        box_actions.addWidget(btn_abrir_local)

        btn_sync = QPushButton("🔄 Sincronizar Vitrine Agora")
        btn_sync.setCursor(Qt.PointingHandCursor)
        btn_sync.setStyleSheet("background-color: #1F2937; color: #F3F4F6; font-weight: bold; padding: 10px 18px; border-radius: 8px;")
        btn_sync.clicked.connect(self._sincronizar_vitrine)
        box_actions.addWidget(btn_sync)

        btn_copiar_link = QPushButton("📋 Copiar Link para a Bio (GitHub Pages)")
        btn_copiar_link.setCursor(Qt.PointingHandCursor)
        btn_copiar_link.setStyleSheet("background-color: #10B981; color: white; font-weight: bold; padding: 10px 18px; border-radius: 8px;")
        btn_copiar_link.clicked.connect(self._copiar_link_bio)
        box_actions.addWidget(btn_copiar_link)
        box_actions.addStretch()

        layout_vitrine.addLayout(box_actions)

        # Caixa explicativa de ativação gratuita no GitHub Pages
        box_pages_guide = QFrame()
        box_pages_guide.setStyleSheet("background: #0F172A; border: 1px solid #1E293B; border-radius: 8px; padding: 12px;")
        layout_pg = QVBoxLayout(box_pages_guide)
        layout_pg.setSpacing(6)

        lbl_pg_title = QLabel("🚀 Como colocar seu link oficial no ar de graça (GitHub Pages):")
        lbl_pg_title.setStyleSheet("color: #38BDF8; font-weight: bold; font-size: 12px;")
        layout_pg.addWidget(lbl_pg_title)

        lbl_pg_steps = QLabel(
            "1. Os arquivos da vitrine já são salvos automaticamente na pasta <b>/docs</b> do projeto.<br>"
            "2. Acesse seu repositório no GitHub: <b>github.com/IsmaelPacheco/Auto-Link-Pinterest</b> ➔ Vá em <b>Settings</b> ➔ <b>Pages</b>.<br>"
            "3. Em <i>'Branch'</i>, escolha <b>main</b> e a pasta <b>/docs</b> e clique em <b>Save</b>.<br>"
            "4. Pronto! Seu link público fica ativo no formato: <b style='color: #10B981;'>https://ismaelpacheco.github.io/Auto-Link-Pinterest/</b>"
        )
        lbl_pg_steps.setStyleSheet("color: #94A3B8; font-size: 11px; line-height: 1.5;")
        layout_pg.addWidget(lbl_pg_steps)
        layout_vitrine.addWidget(box_pages_guide)

        card_vitrine.layout().addLayout(layout_vitrine)
        layout.addWidget(card_vitrine)

        # 3. CARD: AUTOMAÇÃO DE COMENTÁRIOS NO TIKTOK ("EU QUERO")
        card_tiktok = self._criar_card("💬 Automação de Comentários no TikTok ('EU QUERO')")
        layout_tiktok = QVBoxLayout()
        layout_tiktok.setSpacing(14)

        lbl_tt_desc = QLabel(
            "Quando você posta um vídeo no TikTok com a chamada <i>'Comente QUERO que te envio o link'</i>, "
            "o algoritmo impulsiona o vídeo para a For You. Aqui você pode gerenciar a resposta automática:"
        )
        lbl_tt_desc.setStyleSheet("color: #D1D5DB; font-size: 13px;")
        lbl_tt_desc.setWordWrap(True)
        layout_tiktok.addWidget(lbl_tt_desc)

        box_tt_actions = QHBoxLayout()
        box_tt_actions.setSpacing(12)

        self.btn_login_tiktok = QPushButton("🌐 Conectar / Fazer Login no TikTok")
        self.btn_login_tiktok.setCursor(Qt.PointingHandCursor)
        self.btn_login_tiktok.setStyleSheet("background-color: #000000; color: white; border: 1px solid #374151; font-weight: bold; padding: 10px 18px; border-radius: 8px;")
        self.btn_login_tiktok.clicked.connect(self._conectar_tiktok)
        box_tt_actions.addWidget(self.btn_login_tiktok)

        self.btn_reply_comments = QPushButton("⚡ Responder Comentários Pendentes")
        self.btn_reply_comments.setCursor(Qt.PointingHandCursor)
        self.btn_reply_comments.setStyleSheet("background-color: #3B82F6; color: white; font-weight: bold; padding: 10px 18px; border-radius: 8px;")
        self.btn_reply_comments.clicked.connect(self._responder_comentarios)
        box_tt_actions.addWidget(self.btn_reply_comments)

        btn_manychat = QPushButton("🤖 Guia de DMs Automáticas 24/7 (ManyChat Oficial)")
        btn_manychat.setCursor(Qt.PointingHandCursor)
        btn_manychat.setStyleSheet("background-color: #8B5CF6; color: white; font-weight: bold; padding: 10px 18px; border-radius: 8px;")
        btn_manychat.clicked.connect(self._abrir_guia_manychat)
        box_tt_actions.addWidget(btn_manychat)
        box_tt_actions.addStretch()

        layout_tiktok.addLayout(box_tt_actions)
        card_tiktok.layout().addLayout(layout_tiktok)
        layout.addWidget(card_tiktok)

        layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _criar_card(self, titulo: str) -> QFrame:
        card = QFrame()
        card.setObjectName("cardPanel")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(12)

        lbl = QLabel(titulo)
        lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #F3F4F6;")
        card_layout.addWidget(lbl)
        return card

    def _criar_metric_card(self, titulo: str, valor: str, cor: str) -> QFrame:
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
        lbl_v.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {cor};")
        clayout.addWidget(lbl_v)
        return card

    def atualizar_status(self):
        products = self.ve.compile_products()
        count = len(products)
        lbl_tot = self.card_total_vitrine.findChild(QLabel, "val_ACHADINHOS NA VITRINE")
        if lbl_tot:
            lbl_tot.setText(f"{count} produtos")

        is_tt = self.tiktok_engine.is_logged_in()
        lbl_tt = self.card_status_tiktok.findChild(QLabel, "val_CONEXÃO TIKTOK")
        if lbl_tt:
            if is_tt:
                lbl_tt.setText("CONECTADO 🟢")
                lbl_tt.setStyleSheet("font-size: 18px; font-weight: bold; color: #10B981;")
            else:
                lbl_tt.setText("DESCONECTADO 🔴")
                lbl_tt.setStyleSheet("font-size: 18px; font-weight: bold; color: #EF4444;")

    def _abrir_vitrine_navegador(self):
        html_path = Path(__file__).resolve().parent.parent.parent / "vitrine" / "index.html"
        if html_path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(html_path.resolve())))
            self.sig_log.emit("Vitrine aberta no seu navegador!", "success")
        else:
            QMessageBox.warning(self, "Aviso", "Arquivo index.html da vitrine não encontrado.")

    def _sincronizar_vitrine(self):
        res = self.ve.sync_vitrine()
        if res.get("success"):
            self.atualizar_status()
            self.sig_log.emit(f"Vitrine sincronizada com {res.get('total_products')} achadinhos!", "success")
            QMessageBox.information(
                self,
                "Vitrine Sincronizada",
                f"Vitrine sincronizada com sucesso!\n\n"
                f"Total de achadinhos cadastrados: {res.get('total_products')}\n"
                f"Arquivos atualizados em /vitrine e /docs (GitHub Pages)."
            )
        else:
            self.sig_log.emit(f"Erro ao sincronizar vitrine: {res.get('error')}", "error")
            QMessageBox.critical(self, "Erro", f"Falha ao sincronizar: {res.get('error')}")

    def _copiar_link_bio(self):
        from PySide6.QtGui import QGuiApplication
        link = "https://ismaelpacheco.github.io/Auto-Link-Pinterest/"
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(link)
        self.sig_log.emit(f"Link da vitrine copiado para a área de transferência: {link}", "success")
        QMessageBox.information(
            self,
            "Link Copiado!",
            f"O link da sua vitrine foi copiado com sucesso:\n\n{link}\n\n"
            f"Cole este link na Bio do seu perfil do TikTok e Pinterest!"
        )

    def _conectar_tiktok(self):
        self.btn_login_tiktok.setEnabled(False)
        self.btn_login_tiktok.setText("Aguardando login no TikTok...")
        self.sig_log.emit("Abrindo janela dedicada para login no TikTok Studio...", "info")

        self._worker_login = WorkerTikTokLogin()
        self._worker_login.sig_result.connect(self._on_tiktok_login_finished)
        self._worker_login.start()

    def _on_tiktok_login_finished(self, res: dict):
        self.btn_login_tiktok.setEnabled(True)
        self.btn_login_tiktok.setText("🌐 Conectar / Fazer Login no TikTok")
        self.atualizar_status()
        if res.get("success"):
            QMessageBox.information(self, "TikTok Conectado", res.get("message"))
            self.sig_log.emit("Sessão do TikTok salva com sucesso!", "success")
        else:
            QMessageBox.warning(self, "Aviso", res.get("message", "Login não concluído."))
            self.sig_log.emit(f"Aviso no login do TikTok: {res.get('message')}", "warning")

    def _responder_comentarios(self):
        if not self.tiktok_engine.is_logged_in():
            QMessageBox.warning(self, "Atenção", "Conecte sua conta do TikTok antes de iniciar o robô de comentários.")
            return

        self.sig_log.emit("Iniciando varredura de comentários no TikTok Studio...", "info")
        res = self.tiktok_engine.check_and_reply_comments(headless=False)
        if res.get("success"):
            self.sig_log.emit(res.get("message", "Varredura concluída."), "success")
            QMessageBox.information(self, "Varredura de Comentários", res.get("message"))
        else:
            self.sig_log.emit(f"Aviso: {res.get('message')}", "warning")
            QMessageBox.warning(self, "Aviso", res.get("message"))

    def _abrir_guia_manychat(self):
        guide = self.tiktok_engine.get_manychat_guide()
        dlg = QDialog(self)
        dlg.setWindowTitle("🤖 Automação de Directs (DMs) 24/7 no TikTok")
        dlg.setMinimumSize(560, 440)
        dlg.setStyleSheet("background-color: #111827; color: #F9FAFB;")

        d_layout = QVBoxLayout(dlg)
        d_layout.setContentsMargins(20, 20, 20, 20)
        d_layout.setSpacing(12)

        lbl_t = QLabel(guide["title"])
        lbl_t.setStyleSheet("font-size: 15px; font-weight: bold; color: #8B5CF6;")
        d_layout.addWidget(lbl_t)

        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setStyleSheet("background: #1F2937; color: #E5E7EB; border: 1px solid #374151; border-radius: 8px; font-size: 12px; padding: 10px;")
        txt.setPlainText(guide["description"])
        d_layout.addWidget(txt)

        btn_ok = QPushButton("Fechar")
        btn_ok.setStyleSheet("background-color: #8B5CF6; color: white; font-weight: bold; padding: 8px 16px; border-radius: 6px;")
        btn_ok.clicked.connect(dlg.accept)
        d_layout.addWidget(btn_ok, alignment=Qt.AlignRight)

        dlg.exec()

