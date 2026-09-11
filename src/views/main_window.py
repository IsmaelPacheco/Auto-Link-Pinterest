"""
main_window.py
Janela principal do AutoLink Pinterest:
Conecta a barra lateral, cabeçalho, páginas (Dashboard, Autopilot, Histórico, Configurações)
e o gerenciamento de temas e logs centralizados.
"""
import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
    QSystemTrayIcon, QMenu, QApplication
)
from PySide6.QtGui import QAction, QIcon, QCloseEvent
from PySide6.QtCore import Qt

from src.models.config_manager import ConfigManager
from src.models.database import Database
from src.models.account_manager import AccountManager
from .theme import ThemeManager
from .sidebar import Sidebar
from .header import Header
from .dashboard_page import DashboardPage
from .autopilot_page import AutopilotPage
from .accounts_page import AccountsPage
from .history_page import HistoryPage
from .settings_page import SettingsPage
from .instructions_dialog import InstructionsDialog

TITULOS_PAGINA = [
    ("🛍️ Criador Rápido", "Busque ofertas na Shopee, pré-visualize o Pin e publique imediatamente"),
    ("⚡ Piloto Automático", "Esteira contínua com agendamento humanizado e proteção anti-spam"),
    ("👥 Multi-Contas", "Gerencie múltiplas contas nichadas do Pinterest com perfis e cookies isolados"),
    ("📊 Histórico de Pins", "Rastreie todos os pins publicados com métricas e links diretos"),
    ("⚙️ Configurações & APIs", "Gerencie suas chaves da Shopee Open Platform, Pinterest API e preferências")
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cfg = ConfigManager()
        self.db = Database()
        self.am = AccountManager()
        self.tema = ThemeManager()
        self.is_dark_mode = self.cfg.get("dark_mode", True)

        self.setWindowTitle("AutoLink Pinterest • Automação Oficial Shopee")
        self.resize(1280, 820)
        self.setMinimumSize(1000, 650)

        # Widget Central
        widget_central = QWidget()
        self.setCentralWidget(widget_central)
        layout_mestre = QHBoxLayout(widget_central)
        layout_mestre.setContentsMargins(0, 0, 0, 0)
        layout_mestre.setSpacing(0)

        # Barra Lateral
        self.sidebar = Sidebar()
        self.sidebar.navegar.connect(self._mudar_pagina)
        layout_mestre.addWidget(self.sidebar)

        # Área Direita de Conteúdo
        area_direita = QWidget()
        layout_direita = QVBoxLayout(area_direita)
        layout_direita.setContentsMargins(30, 24, 30, 24)
        layout_direita.setSpacing(18)
        layout_mestre.addWidget(area_direita, 1)

        # Cabeçalho
        self.header = Header()
        self.header.alternar_tema.connect(self._alternar_tema)
        self.header.abrir_instrucoes.connect(self._abrir_instrucoes)
        layout_direita.addWidget(self.header)

        # Pilha de Páginas
        self.stacked_widget = QStackedWidget()
        layout_direita.addWidget(self.stacked_widget)

        # Instanciar Páginas
        self.pagina_dashboard = DashboardPage(self.cfg, self.db)
        self.pagina_autopilot = AutopilotPage(self.cfg, self.db)
        self.pagina_accounts = AccountsPage(self.am, self.db)
        self.pagina_historico = HistoryPage(self.db)
        self.pagina_settings = SettingsPage(self.cfg)

        # Conectar Logs de todas as páginas ao terminal da Sidebar
        self.pagina_dashboard.sig_log.connect(self.sidebar.append_log)
        self.pagina_autopilot.sig_log.connect(self.sidebar.append_log)
        self.pagina_accounts.sig_log.connect(self.sidebar.append_log)
        self.pagina_settings.sig_log.connect(self.sidebar.append_log)

        # Atualização em tempo real de contas no Dashboard e Piloto Automático
        self.pagina_accounts.sig_accounts_changed.connect(self.pagina_dashboard._atualizar_contas_combo)
        self.pagina_accounts.sig_accounts_changed.connect(self.pagina_autopilot.atualizar_estatisticas)

        # Adicionar à pilha
        self.stacked_widget.addWidget(self.pagina_dashboard)  # 0
        self.stacked_widget.addWidget(self.pagina_autopilot)  # 1
        self.stacked_widget.addWidget(self.pagina_accounts)   # 2
        self.stacked_widget.addWidget(self.pagina_historico)  # 3
        self.stacked_widget.addWidget(self.pagina_settings)   # 4

        self._mudar_pagina(0)
        self._aplicar_tema()

        # Configuração da Bandeja do Sistema (System Tray)
        self.pode_fechar = False
        self._configurar_system_tray()

        # Log inicial no terminal
        self.sidebar.append_log("AutoLink Pinterest iniciado com sucesso.", "success")
        if not self.cfg.get("shopee_app_id"):
            self.sidebar.append_log("Dica: Adicione suas credenciais na aba Configurações.", "warning")

    def _configurar_system_tray(self):
        caminho_icone = Path(__file__).resolve().parent.parent.parent / "assets" / "icon.png"
        if not caminho_icone.exists():
            caminho_icone = Path(__file__).resolve().parent.parent.parent / "assets" / "icon.ico"

        self.tray_icon = QSystemTrayIcon(self)
        if caminho_icone.exists():
            self.tray_icon.setIcon(QIcon(str(caminho_icone)))

        self.tray_icon.setToolTip("AutoLink Pinterest • Shopee Automator")

        menu = QMenu()
        acao_abrir = QAction("🛍️ Abrir Janela", self)
        acao_abrir.triggered.connect(self._restaurar_janela)
        menu.addAction(acao_abrir)

        menu.addSeparator()

        acao_sair = QAction("❌ Encerrar Aplicativo", self)
        acao_sair.triggered.connect(self._sair_aplicacao)
        menu.addAction(acao_sair)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self._restaurar_janela()

    def _restaurar_janela(self):
        self.showNormal()
        self.activateWindow()

    def _sair_aplicacao(self):
        self.pode_fechar = True
        if hasattr(self.pagina_autopilot, "_worker") and self.pagina_autopilot._worker:
            self.pagina_autopilot._worker.stop()
        self.close()
        QApplication.quit()

    def closeEvent(self, event: QCloseEvent):
        if not self.pode_fechar:
            event.ignore()
            self.hide()
            if self.tray_icon.isVisible():
                self.tray_icon.showMessage(
                    "AutoLink Pinterest",
                    "O aplicativo continua rodando em segundo plano na bandeja do sistema.",
                    QSystemTrayIcon.Information,
                    2000
                )
        else:
            event.accept()

    def _mudar_pagina(self, index: int):
        self.stacked_widget.setCurrentIndex(index)
        if 0 <= index < len(TITULOS_PAGINA):
            titulo, subtitulo = TITULOS_PAGINA[index]
            self.header.definir_titulos(titulo, subtitulo)
        
        # Atualizações ao trocar de página
        if index == 1:
            self.pagina_autopilot.atualizar_estatisticas()
        elif index == 2:
            self.pagina_historico.carregar_dados()
        elif index == 0:
            self.pagina_dashboard._atualizar_boards()

    def _aplicar_tema(self):
        self.tema.aplicar(self, self.is_dark_mode)
        self.header.definir_texto_tema(self.tema.texto_botao_tema(self.is_dark_mode))

    def _alternar_tema(self):
        self.is_dark_mode = not self.is_dark_mode
        self.cfg.set("dark_mode", self.is_dark_mode)
        self.cfg.save()
        self._aplicar_tema()

    def _abrir_instrucoes(self):
        dlg = InstructionsDialog(self)
        dlg.exec()