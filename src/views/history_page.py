"""
history_page.py
Tabela de histórico de publicações do AutoLink Pinterest:
Exibe todos os Pins criados, status, links de afiliados rastreados
e links diretos para visualização no Pinterest.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QLineEdit, QMessageBox
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices

from src.models.database import Database


class HistoryPage(QWidget):
    """Exibe o histórico de postagens no banco SQLite."""

    def __init__(self, database: Database, parent=None):
        super().__init__(parent)
        self.db = database
        self._montar()
        self.carregar_dados()

    def _montar(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # TOPO: CONTROLES DE FILTRO E ATUALIZAÇÃO
        top_card = QFrame()
        top_card.setObjectName("cardPanel")
        top_layout = QHBoxLayout(top_card)
        top_layout.setContentsMargins(15, 12, 15, 12)
        top_layout.setSpacing(15)

        lbl_hist = QLabel("📊 Histórico de Publicações")
        lbl_hist.setStyleSheet("font-size: 15px; font-weight: bold; color: #F3F4F6;")
        top_layout.addWidget(lbl_hist)

        self.input_filtro = QLineEdit()
        self.input_filtro.setPlaceholderText("Filtrar por nome do produto...")
        self.input_filtro.textChanged.connect(self._filtrar_tabela)
        top_layout.addWidget(self.input_filtro)

        self.btn_refresh = QPushButton("🔄 Atualizar")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.carregar_dados)
        top_layout.addWidget(self.btn_refresh)

        layout.addWidget(top_card)

        # TABELA DE PINS
        self.tabela = QTableWidget()
        self.tabela.setColumnCount(6)
        self.tabela.setHorizontalHeaderLabels([
            "Data / Hora", "Título do Produto", "Preço", "Link de Afiliado", "Ver no Pinterest", "Status"
        ])
        self.tabela.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tabela.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabela.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tabela.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tabela.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.tabela.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.tabela.setStyleSheet("""
            QTableWidget {
                background: #111827;
                border: 1px solid #1F2937;
                border-radius: 8px;
                gridline-color: #1F2937;
                color: #F3F4F6;
            }
            QHeaderView::section {
                background: #1F2937;
                color: #9CA3AF;
                padding: 8px;
                font-weight: bold;
                border: none;
            }
            QTableWidget::item {
                padding: 6px;
            }
        """)
        layout.addWidget(self.tabela)

    def carregar_dados(self):
        """Carrega os dados mais recentes do SQLite."""
        pins = self.db.get_all_pins(limit=200)
        self.tabela.setRowCount(len(pins))

        for row_idx, pin in enumerate(pins):
            # Data
            dt_item = QTableWidgetItem(str(pin.get("created_at", "")))
            dt_item.setTextAlignment(Qt.AlignCenter)
            self.tabela.setItem(row_idx, 0, dt_item)

            # Título
            title_item = QTableWidgetItem(str(pin.get("title", "")))
            self.tabela.setItem(row_idx, 1, title_item)

            # Preço
            price = pin.get("discount_price") or 0.0
            price_item = QTableWidgetItem(f"R$ {price:.2f}")
            price_item.setTextAlignment(Qt.AlignCenter)
            self.tabela.setItem(row_idx, 2, price_item)

            # Link Afiliado
            aff_link = pin.get("affiliate_link", "")
            btn_aff = QPushButton("🔗 Copiar Link")
            btn_aff.setCursor(Qt.PointingHandCursor)
            btn_aff.clicked.connect(lambda _, l=aff_link: self._copiar_link(l))
            self.tabela.setCellWidget(row_idx, 3, btn_aff)

            # Ver no Pinterest
            pin_url = pin.get("pinterest_url", "")
            if pin_url:
                btn_pin = QPushButton("📌 Abrir Pin")
                btn_pin.setStyleSheet("background-color: #E60023; color: white; border-radius: 4px; padding: 4px 8px;")
                btn_pin.setCursor(Qt.PointingHandCursor)
                btn_pin.clicked.connect(lambda _, u=pin_url: QDesktopServices.openUrl(QUrl(u)))
                self.tabela.setCellWidget(row_idx, 4, btn_pin)
            else:
                empty_item = QTableWidgetItem("-")
                empty_item.setTextAlignment(Qt.AlignCenter)
                self.tabela.setItem(row_idx, 4, empty_item)

            # Status
            status = pin.get("status", "SUCCESS")
            status_item = QTableWidgetItem(status)
            status_item.setTextAlignment(Qt.AlignCenter)
            if status == "SUCCESS":
                status_item.setForeground(Qt.green)
            else:
                status_item.setForeground(Qt.red)
            self.tabela.setItem(row_idx, 5, status_item)

    def _copiar_link(self, link: str):
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(link)
        QMessageBox.information(self, "Copiado", "Link de afiliado copiado para a área de transferência!")

    def _filtrar_tabela(self, texto: str):
        texto = texto.lower().strip()
        for row in range(self.tabela.rowCount()):
            item = self.tabela.item(row, 1)
            if item:
                visivel = texto in item.text().lower()
                self.tabela.setRowHidden(row, not visivel)