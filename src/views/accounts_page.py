"""
accounts_page.py
Página de Gerenciamento de Múltiplas Contas do Pinterest (Multi-Account).
Permite cadastrar novas contas nichadas, importar cookies independentes,
testar sessões e gerenciar o rodízio do Piloto Automático.
"""
from typing import Optional
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QDialog, QLineEdit, QSpinBox,
    QComboBox, QCheckBox, QMessageBox, QGridLayout
)
from PySide6.QtCore import Qt, Signal, QThread

from src.models.account_manager import AccountManager, PinterestAccount
from src.models.database import Database
from src.views.cookie_dialog import CookieImportDialog


class WorkerAccountBrowserLogin(QThread):
    """Abre o navegador isolado para login de uma conta específica."""
    sig_result = Signal(dict)

    def __init__(self, browser_engine):
        super().__init__()
        self.engine = browser_engine

    def run(self):
        try:
            res = self.engine.open_login_window()
            self.sig_result.emit(res)
        except Exception as e:
            self.sig_result.emit({"success": False, "message": str(e)})


class AccountEditDialog(QDialog):
    """Diálogo para criar ou editar uma conta do Pinterest."""

    def __init__(self, parent=None, account: Optional[PinterestAccount] = None):
        super().__init__(parent)
        self.account = account
        is_edit = account is not None
        self.setWindowTitle("✏️ Editar Conta" if is_edit else "➕ Nova Conta do Pinterest")
        self.setMinimumWidth(500)
        self.setStyleSheet("""
            QDialog {
                background-color: #111827;
                color: #F9FAFB;
            }
            QLabel {
                font-size: 12px;
                color: #D1D5DB;
                font-weight: bold;
            }
            QLineEdit, QSpinBox, QComboBox {
                background-color: #1F2937;
                color: white;
                border: 1px solid #374151;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        lbl_title = QLabel("Configurações da Conta Nichada")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #EE4D2D;")
        layout.addWidget(lbl_title)

        # Nome
        layout.addWidget(QLabel("Nome de Identificação da Conta:"))
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("Ex: Conta 2 - Decoração & Estilo")
        if account:
            self.input_name.setText(account.name)
        layout.addWidget(self.input_name)

        # Nicho
        layout.addWidget(QLabel("Nicho Principal:"))
        self.combo_niche = QComboBox()
        nichos = [
            "🍳 Cozinha Prática",
            "🏠 Casa & Organização",
            "✨ Decoração & Estilo",
            "💄 Beleza & Cuidados",
            "🧹 Limpeza Inteligente",
            "🏊 Jardim & Varanda",
            "🔥 Achadinhos Gerais Shopee"
        ]
        self.combo_niche.addItems(nichos)
        if account:
            idx = self.combo_niche.findText(account.niche, Qt.MatchContains)
            if idx >= 0:
                self.combo_niche.setCurrentIndex(idx)
            else:
                self.combo_niche.addItem(account.niche)
                self.combo_niche.setCurrentIndex(self.combo_niche.count() - 1)
        layout.addWidget(self.combo_niche)

        # Pasta Padrão
        layout.addWidget(QLabel("Nome da Pasta no Pinterest (Board):"))
        self.input_board = QLineEdit()
        self.input_board.setPlaceholderText("Ex: Achadinhos de Cozinha (deixe vazio para usar a principal)")
        if account:
            self.input_board.setText(account.board_name)
        layout.addWidget(self.input_board)

        # Palavras-chave
        layout.addWidget(QLabel("Palavras-chave de Busca na Shopee (separadas por vírgula):"))
        self.input_keywords = QLineEdit()
        self.input_keywords.setPlaceholderText("Ex: panela antiaderente, organizador, mixer, potes")
        if account:
            self.input_keywords.setText(account.search_keywords)
        layout.addWidget(self.input_keywords)

        # Meta Diária
        box_meta = QHBoxLayout()
        box_meta.addWidget(QLabel("Meta Diária de Pins:"))
        self.spin_meta = QSpinBox()
        self.spin_meta.setRange(1, 50)
        self.spin_meta.setValue(account.max_pins_per_day if account else 15)
        self.spin_meta.setSuffix(" pins/dia")
        box_meta.addWidget(self.spin_meta)
        box_meta.addStretch()
        layout.addLayout(box_meta)

        # Checkbox Ativa
        self.check_active = QCheckBox("Habilitar esta conta no rodízio do Piloto Automático")
        self.check_active.setChecked(account.is_active if account else True)
        self.check_active.setStyleSheet("color: #10B981; font-weight: bold; font-size: 12px;")
        layout.addWidget(self.check_active)

        # Botões
        layout.addSpacing(10)
        box_btns = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setStyleSheet("background: #374151; color: white; padding: 10px 18px; border-radius: 6px;")
        self.btn_cancel.clicked.connect(self.reject)
        box_btns.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("💾 Salvar Conta")
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setStyleSheet("background: #10B981; color: white; font-weight: bold; padding: 10px 22px; border-radius: 6px;")
        self.btn_save.clicked.connect(self._validar_e_salvar)
        box_btns.addWidget(self.btn_save)

        layout.addLayout(box_btns)

    def _validar_e_salvar(self):
        nome = self.input_name.text().strip()
        if not nome:
            QMessageBox.warning(self, "Atenção", "Informe um nome para a conta.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "name": self.input_name.text().strip(),
            "niche": self.combo_niche.currentText(),
            "board_name": self.input_board.text().strip(),
            "search_keywords": self.input_keywords.text().strip(),
            "max_pins_per_day": self.spin_meta.value(),
            "is_active": self.check_active.isChecked()
        }


class AccountsPage(QWidget):
    """Página visual de gerenciamento de múltiplas contas."""
    sig_log = Signal(str, str)
    sig_accounts_changed = Signal()

    def __init__(self, account_manager: AccountManager, database: Database, parent=None):
        super().__init__(parent)
        self.am = account_manager
        self.db = database
        self._montar_ui()

    def _montar_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # BARRA DE TÍTULO E AÇÃO
        box_top = QHBoxLayout()
        box_title = QVBoxLayout()
        lbl_title = QLabel("👥 Gerenciador Multi-Contas do Pinterest")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #F9FAFB;")
        lbl_sub = QLabel("Escale suas vendas dividindo o volume em contas nichadas com sessões 100% isoladas.")
        lbl_sub.setStyleSheet("font-size: 13px; color: #9CA3AF;")
        box_title.addWidget(lbl_title)
        box_title.addWidget(lbl_sub)
        box_top.addLayout(box_title)
        box_top.addStretch()

        self.btn_add_account = QPushButton("➕ Nova Conta do Pinterest")
        self.btn_add_account.setCursor(Qt.PointingHandCursor)
        self.btn_add_account.setStyleSheet("""
            QPushButton {
                background-color: #EE4D2D;
                color: white;
                font-weight: bold;
                font-size: 13px;
                padding: 10px 20px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #D73211;
            }
        """)
        self.btn_add_account.clicked.connect(self._adicionar_conta)
        box_top.addWidget(self.btn_add_account)
        layout.addLayout(box_top)

        # CARDS DE MÉTRICAS RÁPIDAS
        self.box_kpis = QHBoxLayout()
        self.box_kpis.setSpacing(14)
        layout.addLayout(self.box_kpis)

        # ÁREA DE ROLAGEM COM A LISTA DE CONTAS
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        self.container_cards = QWidget()
        self.layout_cards = QVBoxLayout(self.container_cards)
        self.layout_cards.setContentsMargins(0, 8, 0, 8)
        self.layout_cards.setSpacing(14)

        scroll.setWidget(self.container_cards)
        layout.addWidget(scroll, 1)

        self.carregar_contas()

    def carregar_contas(self):
        """Recarrega a lista de contas na tela."""
        # Limpa widgets anteriores
        while self.layout_cards.count():
            item = self.layout_cards.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        while self.box_kpis.count():
            item = self.box_kpis.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        accounts = self.am.get_all_accounts()
        counts_today = self.db.get_pins_count_per_account_today()
        total_pins_today = sum(counts_today.values())
        total_meta = sum(acc.max_pins_per_day for acc in accounts if acc.is_active)
        active_count = len([acc for acc in accounts if acc.is_active])

        # Renderiza KPIs
        self.box_kpis.addWidget(self._criar_kpi("Contas Cadastradas", str(len(accounts)), "👥", "#3B82F6"))
        self.box_kpis.addWidget(self._criar_kpi("Contas Ativas no Rodízio", str(active_count), "⚡", "#10B981"))
        self.box_kpis.addWidget(self._criar_kpi("Capacidade Combinada", f"{total_meta} pins/dia", "🎯", "#8B5CF6"))
        self.box_kpis.addWidget(self._criar_kpi("Postados Hoje (Total)", f"{total_pins_today} pins", "🚀", "#F59E0B"))

        # Renderiza Card para cada conta
        for acc in accounts:
            card = self._criar_card_conta(acc, counts_today.get(acc.id, 0))
            self.layout_cards.addWidget(card)

        self.layout_cards.addStretch()

    def _criar_kpi(self, titulo: str, valor: str, icone: str, cor: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #1F2937;
                border-left: 4px solid {cor};
                border-radius: 8px;
                padding: 12px 16px;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setSpacing(4)
        lbl_t = QLabel(f"{icone} {titulo}")
        lbl_t.setStyleSheet("color: #9CA3AF; font-size: 11px; font-weight: bold;")
        lbl_v = QLabel(valor)
        lbl_v.setStyleSheet("color: #F9FAFB; font-size: 18px; font-weight: bold;")
        lay.addWidget(lbl_t)
        lay.addWidget(lbl_v)
        return card

    def _criar_card_conta(self, acc: PinterestAccount, pins_hoje: int) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame#cardConta {
                background-color: #1A2234;
                border: 1px solid #2D3748;
                border-radius: 10px;
                padding: 16px;
            }
            QFrame#cardConta:hover {
                border: 1px solid #4B5563;
            }
        """)
        card.setObjectName("cardConta")

        main_lay = QVBoxLayout(card)
        main_lay.setSpacing(12)

        # Linha Superior (Nome, Nicho e Status)
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        lbl_nome = QLabel(acc.name)
        lbl_nome.setStyleSheet("font-size: 15px; font-weight: bold; color: #F3F4F6;")
        top_row.addWidget(lbl_nome)

        lbl_niche = QLabel(f" {acc.niche} ")
        lbl_niche.setStyleSheet("background: #374151; color: #93C5FD; font-size: 11px; font-weight: bold; border-radius: 4px; padding: 3px 8px;")
        top_row.addWidget(lbl_niche)

        top_row.addStretch()

        has_session = acc.has_cookies()
        status_text = "🟢 Sessão Conectada" if has_session else "🔴 Não Conectada"
        status_color = "#10B981" if has_session else "#EF4444"
        lbl_status = QLabel(status_text)
        lbl_status.setStyleSheet(f"color: {status_color}; font-weight: bold; font-size: 12px;")
        top_row.addWidget(lbl_status)

        main_lay.addLayout(top_row)

        # Detalhes (Pasta, Palavras-chave e Progresso)
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(6)

        pasta = acc.board_name or "(Pasta Padrão)"
        grid.addWidget(QLabel("📂 Pasta do Pinterest:"), 0, 0)
        lbl_pasta = QLabel(pasta)
        lbl_pasta.setStyleSheet("color: #D1D5DB; font-weight: bold;")
        grid.addWidget(lbl_pasta, 0, 1)

        grid.addWidget(QLabel("🎯 Palavras-chave:"), 1, 0)
        lbl_kw = QLabel(acc.search_keywords[:60] + ("..." if len(acc.search_keywords) > 60 else ""))
        lbl_kw.setStyleSheet("color: #9CA3AF; font-size: 11px;")
        grid.addWidget(lbl_kw, 1, 1)

        grid.addWidget(QLabel("📊 Desempenho Hoje:"), 2, 0)
        lbl_prog = QLabel(f"{pins_hoje} / {acc.max_pins_per_day} pins postados")
        pct = min(100, int((pins_hoje / max(1, acc.max_pins_per_day)) * 100))
        lbl_prog.setStyleSheet(f"color: {'#10B981' if pct >= 100 else '#F59E0B'}; font-weight: bold;")
        grid.addWidget(lbl_prog, 2, 1)

        main_lay.addLayout(grid)

        # Rodapé de Ações
        bot_row = QHBoxLayout()
        bot_row.setSpacing(8)

        check_ativo = QCheckBox("Ativa no Piloto Automático")
        check_ativo.setChecked(acc.is_active)
        check_ativo.setStyleSheet("color: #E5E7EB; font-size: 12px;")
        check_ativo.toggled.connect(lambda checked, aid=acc.id: self._toggle_ativo(aid, checked))
        bot_row.addWidget(check_ativo)

        bot_row.addStretch()

        # Botão Conectar Cookies
        btn_cookies = QPushButton("🔑 Conectar Cookies")
        btn_cookies.setCursor(Qt.PointingHandCursor)
        btn_cookies.setStyleSheet("background: #3B82F6; color: white; padding: 6px 12px; border-radius: 4px; font-size: 11px; font-weight: bold;")
        btn_cookies.clicked.connect(lambda _, a=acc: self._importar_cookies_conta(a))
        bot_row.addWidget(btn_cookies)

        # Botão Abrir Navegador
        btn_browser = QPushButton("🌐 Abrir Navegador")
        btn_browser.setCursor(Qt.PointingHandCursor)
        btn_browser.setStyleSheet("background: #374151; color: white; padding: 6px 12px; border-radius: 4px; font-size: 11px;")
        btn_browser.clicked.connect(lambda _, a=acc: self._abrir_login_navegador(a))
        bot_row.addWidget(btn_browser)

        # Botão Testar Sessão
        btn_test = QPushButton("⚡ Testar")
        btn_test.setCursor(Qt.PointingHandCursor)
        btn_test.setStyleSheet("background: #065F46; color: #6EE7B7; padding: 6px 12px; border-radius: 4px; font-size: 11px; font-weight: bold;")
        btn_test.clicked.connect(lambda _, a=acc: self._testar_sessao(a))
        bot_row.addWidget(btn_test)

        # Botão Editar
        btn_edit = QPushButton("✏️ Editar")
        btn_edit.setCursor(Qt.PointingHandCursor)
        btn_edit.setStyleSheet("background: #374151; color: #D1D5DB; padding: 6px 10px; border-radius: 4px; font-size: 11px;")
        btn_edit.clicked.connect(lambda _, a=acc: self._editar_conta(a))
        bot_row.addWidget(btn_edit)

        # Botão Excluir (Não permite excluir a default se for a única)
        if acc.id != "default" or len(self.am.get_all_accounts()) > 1:
            btn_del = QPushButton("🗑️")
            btn_del.setToolTip("Excluir esta conta")
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.setStyleSheet("background: #7F1D1D; color: white; padding: 6px 8px; border-radius: 4px; font-size: 11px;")
            btn_del.clicked.connect(lambda _, aid=acc.id, name=acc.name: self._excluir_conta(aid, name))
            bot_row.addWidget(btn_del)

        main_lay.addLayout(bot_row)
        return card

    def _adicionar_conta(self):
        dlg = AccountEditDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            new_acc = self.am.add_account(
                name=data["name"],
                niche=data["niche"],
                board_name=data["board_name"],
                search_keywords=data["search_keywords"],
                max_pins_per_day=data["max_pins_per_day"],
                is_active=data["is_active"]
            )
            self.sig_log.emit(f"Conta '{new_acc.name}' cadastrada com sucesso no Multi-Contas!", "success")
            self.carregar_contas()
            self.sig_accounts_changed.emit()

    def _editar_conta(self, acc: PinterestAccount):
        dlg = AccountEditDialog(self, account=acc)
        if dlg.exec():
            data = dlg.get_data()
            self.am.update_account(acc.id, **data)
            self.sig_log.emit(f"Conta '{acc.name}' atualizada com sucesso.", "info")
            self.carregar_contas()
            self.sig_accounts_changed.emit()

    def _toggle_ativo(self, account_id: str, is_active: bool):
        self.am.update_account(account_id, is_active=is_active)
        status = "ativada" if is_active else "pausada"
        self.sig_log.emit(f"Conta '{account_id}' {status} no rodízio do autopilot.", "info")
        self.carregar_contas()
        self.sig_accounts_changed.emit()

    def _excluir_conta(self, account_id: str, name: str):
        reply = QMessageBox.question(
            self,
            "Confirmar Exclusão",
            f"Deseja realmente remover a conta '{name}' do Multi-Contas?\n"
            "Seus cookies e dados associados serão removidos.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.am.delete_account(account_id)
            self.sig_log.emit(f"Conta '{name}' removida com sucesso.", "warning")
            self.carregar_contas()
            self.sig_accounts_changed.emit()

    def _importar_cookies_conta(self, acc: PinterestAccount):
        engine = self.am.get_browser_engine_for_account(acc.id)
        dlg = CookieImportDialog(self, browser_engine=engine)
        if dlg.exec():
            self.sig_log.emit(f"Cookies salvos com sucesso para a conta '{acc.name}'!", "success")
            self.carregar_contas()

    def _abrir_login_navegador(self, acc: PinterestAccount):
        self.sig_log.emit(f"Abrindo janela do Chromium isolada para a conta '{acc.name}'...", "info")
        engine = self.am.get_browser_engine_for_account(acc.id)
        self._login_worker = WorkerAccountBrowserLogin(engine)
        self._login_worker.sig_result.connect(lambda res, name=acc.name: self._on_login_finished(name, res))
        self._login_worker.start()

    def _on_login_finished(self, name: str, res: dict):
        if res.get("success"):
            QMessageBox.information(self, "Login Concluído", f"Sessão da conta '{name}' conectada com sucesso!")
            self.sig_log.emit(f"Sessão salva com sucesso para a conta '{name}'!", "success")
        else:
            QMessageBox.warning(self, "Aviso", res.get("message", "Login não concluído."))
        self.carregar_contas()

    def _testar_sessao(self, acc: PinterestAccount):
        if not acc.has_cookies():
            QMessageBox.warning(self, "Atenção", f"A conta '{acc.name}' ainda não possui cookies importados.")
            return
        engine = self.am.get_browser_engine_for_account(acc.id)
        self.sig_log.emit(f"Verificando sessão da conta '{acc.name}'...", "info")
        is_ok = engine.is_logged_in()
        if is_ok:
            QMessageBox.information(self, "Sessão Ativa", f"✅ A conta '{acc.name}' está com a sessão ativa e conectada!")
            self.sig_log.emit(f"Conta '{acc.name}': Sessão válida e pronta para postar.", "success")
        else:
            QMessageBox.warning(self, "Sessão Expirada", f"⚠️ A sessão da conta '{acc.name}' expirou ou não está logada.\nImporte novos cookies.")
            self.sig_log.emit(f"Conta '{acc.name}': Sessão desconectada.", "warning")
        self.carregar_contas()
