"""
dashboard_page.py
Tela principal do AutoLink Pinterest:
Busca de produtos da Shopee, extração via URL, preview visual ao vivo do Pin (1000x1500),
edição de Título/Descrição/Hashtags e disparo imediato para o Pinterest.
"""
import random
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTextEdit, QComboBox, QFrame, QScrollArea, QSplitter, QMessageBox,
    QProgressBar, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QImage
from PIL import Image

from src.models.config_manager import ConfigManager
from src.models.database import Database
from src.models.trending_catalog import TRENDING_NICHES, SORT_OPTIONS
from src.engines.pin_image_engine import PinImageEngine
from src.engines.copy_engine import CopyEngine
from src.engines.pinterest_engine import PinterestEngine
from src.workers.worker_manual import WorkerSearchProduct, WorkerPublishPin


class DashboardPage(QWidget):
    """Página de criação rápida e teste de Pins."""

    sig_log = Signal(str, str)

    def __init__(self, config_manager: ConfigManager, database: Database, parent=None):
        super().__init__(parent)
        self.cfg = config_manager
        self.db = database
        self.img_engine = PinImageEngine()
        self.copy_engine = CopyEngine(
            gemini_key=self.cfg.get("gemini_key", "") or self.cfg.get("gemini_api_key", ""),
            use_gemini=self.cfg.get("use_gemini", True)
        )

        self.current_product = None
        self.current_pil_image = None
        self._worker_search = None
        self._worker_publish = None

        self._montar()

    def _montar(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 1. PAINEL DE INTELIGÊNCIA DE BUSCA E TENDÊNCIAS
        bar_card = QFrame()
        bar_card.setObjectName("cardPanel")
        bar_layout = QVBoxLayout(bar_card)
        bar_layout.setContentsMargins(15, 14, 15, 14)
        bar_layout.setSpacing(10)

        # Linha 1: Filtros de Inteligência de Mercado
        row_filters = QHBoxLayout()
        row_filters.setSpacing(10)

        # Seletor de Nicho Viral
        lbl_nicho = QLabel("🎯 Nicho Viral:")
        lbl_nicho.setStyleSheet("font-size: 12px; font-weight: bold; color: #9CA3AF;")
        row_filters.addWidget(lbl_nicho)

        self.combo_nicho = QComboBox()
        self.combo_nicho.addItem("✨ Escolha um Nicho / Sugestão Viral...", "")
        for n_key, n_info in TRENDING_NICHES.items():
            self.combo_nicho.addItem(n_info["nome"], n_key)
        self.combo_nicho.setStyleSheet("""
            QComboBox {
                background: #1F2937; color: #F9FAFB; border: 1px solid #374151;
                border-radius: 6px; padding: 5px 10px; font-size: 12px; min-width: 200px;
            }
        """)
        self.combo_nicho.currentIndexChanged.connect(self._on_nicho_selected)
        row_filters.addWidget(self.combo_nicho)

        # Seletor de Ordenação
        lbl_sort = QLabel("📊 Ordenar por:")
        lbl_sort.setStyleSheet("font-size: 12px; font-weight: bold; color: #9CA3AF;")
        row_filters.addWidget(lbl_sort)

        self.combo_sort = QComboBox()
        for opt in SORT_OPTIONS:
            self.combo_sort.addItem(opt["label"], opt["value"])
        self.combo_sort.setStyleSheet("""
            QComboBox {
                background: #1F2937; color: #F9FAFB; border: 1px solid #374151;
                border-radius: 6px; padding: 5px 10px; font-size: 12px;
            }
        """)
        row_filters.addWidget(self.combo_sort)

        # Filtro de Mínimo de Vendas
        lbl_sales = QLabel("🔥 Mínimo Vendas:")
        lbl_sales.setStyleSheet("font-size: 12px; font-weight: bold; color: #9CA3AF;")
        row_filters.addWidget(lbl_sales)

        self.combo_min_sales = QComboBox()
        self.combo_min_sales.addItem("Qualquer volume", 0)
        self.combo_min_sales.addItem("50+ vendas", 50)
        self.combo_min_sales.addItem("100+ vendas", 100)
        self.combo_min_sales.addItem("500+ vendas", 500)
        self.combo_min_sales.addItem("1.000+ vendas", 1000)
        self.combo_min_sales.setStyleSheet("""
            QComboBox {
                background: #1F2937; color: #F9FAFB; border: 1px solid #374151;
                border-radius: 6px; padding: 5px 10px; font-size: 12px;
            }
        """)
        row_filters.addWidget(self.combo_min_sales)
        row_filters.addStretch()
        bar_layout.addLayout(row_filters)

        # Linha 2: Campo de busca manual + Botão
        row_search = QHBoxLayout()
        row_search.setSpacing(10)

        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("Cole o link de um produto Shopee OU digite um termo (ex: organizador de maquiagem, luminaria)...")
        self.input_search.returnPressed.connect(self._iniciar_busca)
        row_search.addWidget(self.input_search)

        self.btn_search = QPushButton("🔍 Buscar Ofertas na Shopee")
        self.btn_search.setCursor(Qt.PointingHandCursor)
        self.btn_search.setStyleSheet("background-color: #EE4D2D; color: white; font-weight: bold; padding: 9px 20px; border-radius: 6px;")
        self.btn_search.clicked.connect(self._iniciar_busca)
        row_search.addWidget(self.btn_search)
        bar_layout.addLayout(row_search)

        main_layout.addWidget(bar_card)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # 2. SPLITTER PRINCIPAL (LISTA À ESQUERDA, PREVIEW & CONTROLES À DIREITA)
        splitter = QSplitter(Qt.Horizontal)

        # PAINEL ESQUERDO: LISTA DE PRODUTOS
        panel_left = QFrame()
        panel_left.setObjectName("cardPanel")
        layout_left = QVBoxLayout(panel_left)
        layout_left.setContentsMargins(15, 15, 15, 15)

        lbl_prods = QLabel("📦 Ofertas Encontradas (Clique para carregar no Pin):")
        lbl_prods.setStyleSheet("font-weight: bold; color: #E5E7EB;")
        layout_left.addWidget(lbl_prods)

        self.list_products = QListWidget()
        self.list_products.setStyleSheet("""
            QListWidget {
                background: #111827;
                border: 1px solid #1F2937;
                border-radius: 8px;
                color: #F3F4F6;
                padding: 5px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #1F2937;
                border-radius: 6px;
            }
            QListWidget::item:hover {
                background: #1F2937;
            }
            QListWidget::item:selected {
                background: #EE4D2D;
                color: white;
            }
        """)
        self.list_products.itemClicked.connect(self._on_product_selected)
        layout_left.addWidget(self.list_products)
        splitter.addWidget(panel_left)

        # PAINEL DIREITO: PREVIEW VISUAL DO PIN & METADADOS
        panel_right = QFrame()
        panel_right.setObjectName("cardPanel")
        layout_right = QHBoxLayout(panel_right)
        layout_right.setContentsMargins(15, 15, 15, 15)
        layout_right.setSpacing(20)

        # PREVIEW DA IMAGEM 1000x1500 (Proporção 2:3 em escala)
        box_preview = QVBoxLayout()
        box_preview.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        lbl_preview_title = QLabel("👁️ Pré-visualização do Pin (2:3)")
        lbl_preview_title.setStyleSheet("font-weight: bold; color: #9CA3AF; font-size: 11px;")
        box_preview.addWidget(lbl_preview_title)

        self.lbl_image_preview = QLabel()
        self.lbl_image_preview.setFixedSize(260, 390)  # Proporção 2:3
        self.lbl_image_preview.setStyleSheet("""
            QLabel {
                background: #0B0F19;
                border: 2px dashed #374151;
                border-radius: 12px;
                color: #6B7280;
            }
        """)
        self.lbl_image_preview.setAlignment(Qt.AlignCenter)
        self.lbl_image_preview.setText("Nenhum produto\nselecionado")
        box_preview.addWidget(self.lbl_image_preview)

        # Seletor de Paleta de Cores
        box_palette = QHBoxLayout()
        box_palette.setSpacing(6)
        lbl_pal = QLabel("🎨 Paleta:")
        lbl_pal.setStyleSheet("color: #9CA3AF; font-size: 11px; font-weight: bold;")
        box_palette.addWidget(lbl_pal)

        self.combo_palette = QComboBox()
        self.combo_palette.addItem("🎲 Aleatório (Rotativo)", "auto")
        self.combo_palette.addItem("🔥 Shopee Warm", "shopee_warm")
        self.combo_palette.addItem("✨ Clean Nordic", "clean_nordic")
        self.combo_palette.addItem("💄 Rose Gold", "rose_gold")
        self.combo_palette.addItem("🌿 Fresh Mint", "fresh_mint")
        self.combo_palette.addItem("💜 Lavender Dream", "lavender_modern")
        self.combo_palette.addItem("💎 Royal Indigo", "royal_indigo")
        self.combo_palette.addItem("🍯 Golden Honey", "golden_honey")
        self.combo_palette.setStyleSheet("background: #1F2937; color: white; border-radius: 4px; padding: 4px; font-size: 11px;")
        self.combo_palette.currentIndexChanged.connect(self._on_palette_changed)
        box_palette.addWidget(self.combo_palette)
        box_preview.addLayout(box_palette)

        self.btn_new_art = QPushButton("🎲 Nova Variação Visual")
        self.btn_new_art.setCursor(Qt.PointingHandCursor)
        self.btn_new_art.setStyleSheet("background-color: #374151; color: #E5E7EB; padding: 6px; border-radius: 6px; font-size: 11px;")
        self.btn_new_art.clicked.connect(self._regenerar_variacao_arte)
        box_preview.addWidget(self.btn_new_art)

        layout_right.addLayout(box_preview)

        # FORMULÁRIO DE PUBLICAÇÃO
        scroll_form = QScrollArea()
        scroll_form.setWidgetResizable(True)
        scroll_form.setFrameShape(QFrame.NoFrame)

        container_form = QWidget()
        layout_form = QVBoxLayout(container_form)
        layout_form.setSpacing(12)

        # Seletor de Formato de Mídia
        box_format = QHBoxLayout()
        box_format.setSpacing(8)
        lbl_fmt = QLabel("🎬 Formato do Pin:")
        lbl_fmt.setStyleSheet("font-weight: bold; color: #E5E7EB; font-size: 12px;")
        box_format.addWidget(lbl_fmt)

        self.combo_format = QComboBox()
        self.combo_format.addItem("📌 Imagem Estática (1000x1500)", "image")
        self.combo_format.addItem("🎬 Vídeo Animado (.MP4 com Zoom & Pulso)", "video")
        self.combo_format.setStyleSheet("background: #1F2937; color: white; border-radius: 4px; padding: 6px; font-size: 12px;")
        box_format.addWidget(self.combo_format)
        layout_form.addLayout(box_format)

        layout_form.addWidget(QLabel("📌 Título do Pin (Pinterest):"))
        self.input_pin_title = QLineEdit()
        self.input_pin_title.setPlaceholderText("Título chamativo...")
        layout_form.addWidget(self.input_pin_title)

        layout_form.addWidget(QLabel("📝 Descrição e SEO (com hashtags):"))
        self.input_pin_desc = QTextEdit()
        self.input_pin_desc.setMinimumHeight(120)
        self.input_pin_desc.setPlaceholderText("Descrição autêntica com ganchos e hashtags...")
        layout_form.addWidget(self.input_pin_desc)

        layout_form.addWidget(QLabel("🔗 Link de Afiliado Oficial:"))
        self.input_pin_link = QLineEdit()
        self.input_pin_link.setPlaceholderText("https://s.shopee.com.br/...")
        layout_form.addWidget(self.input_pin_link)

        layout_form.addWidget(QLabel("📂 Pasta do Pinterest (Board):"))
        self.combo_boards = QComboBox()
        layout_form.addWidget(self.combo_boards)

        self.btn_publish_now = QPushButton("🚀 Publicar Agora no Pinterest")
        self.btn_publish_now.setCursor(Qt.PointingHandCursor)
        self.btn_publish_now.setStyleSheet("""
            QPushButton {
                background-color: #E60023;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 12px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #C0001D;
            }
        """)
        self.btn_publish_now.clicked.connect(self._publicar_pin_agora)
        layout_form.addWidget(self.btn_publish_now)

        scroll_form.setWidget(container_form)
        layout_right.addWidget(scroll_form, 1)

        splitter.addWidget(panel_right)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)

        main_layout.addWidget(splitter, 1)

        self._atualizar_boards()

    def _atualizar_boards(self):
        """Carrega os boards das configurações."""
        self.combo_boards.clear()
        saved_id = self.cfg.get("pinterest_board_id", "")
        saved_name = self.cfg.get("pinterest_board_name", "Pasta Padrão")
        if saved_id:
            self.combo_boards.addItem(saved_name, saved_id)

    def _on_nicho_selected(self, index: int):
        niche_key = self.combo_nicho.itemData(index)
        if not niche_key:
            return
        niche_info = TRENDING_NICHES.get(niche_key)
        if niche_info and niche_info.get("keywords"):
            # Escolhe um termo viral do nicho
            chosen_term = random.choice(niche_info["keywords"])
            self.input_search.setText(chosen_term)
            self._iniciar_busca()

    def _iniciar_busca(self):
        query = self.input_search.text().strip()
        if not query:
            QMessageBox.warning(self, "Atenção", "Digite um termo ou escolha um nicho viral da Shopee.")
            return

        self.progress_bar.setVisible(True)
        self.btn_search.setEnabled(False)
        self.list_products.clear()
        
        sort_val = self.combo_sort.currentData() or 2
        min_sales_val = self.combo_min_sales.currentData() or 0

        self.sig_log.emit(f"Consultando ofertas para: '{query}' (Ordenação: {self.combo_sort.currentText()} | Mín. vendas: {min_sales_val})...", "info")

        self._worker_search = WorkerSearchProduct(
            query_or_url=query,
            config=self.cfg,
            sort_type=sort_val,
            min_sales=min_sales_val
        )
        self._worker_search.sig_success.connect(self._on_search_success)
        self._worker_search.sig_error.connect(self._on_search_error)
        self._worker_search.start()

    def _on_search_success(self, products):
        self.progress_bar.setVisible(False)
        self.btn_search.setEnabled(True)

        if not products:
            self.sig_log.emit("Nenhuma oferta encontrada com os filtros atuais.", "warning")
            QMessageBox.information(self, "Resultado", "Nenhum produto encontrado. Tente reduzir o filtro de 'Mínimo Vendas' ou buscar outro termo.")
            return

        self.sig_log.emit(f"{len(products)} produto(s) encontrado(s).", "info")
        for p in products:
            title = p.get("title", "Produto")
            price = p.get("discount_price", 0.0)
            disc = p.get("discount_pct", 0)
            sales = p.get("sales", 0)
            comm = p.get("commission_rate", "")
            
            sales_badge = f"🔥 {sales:,} vendidos" if sales > 0 else "Novo"
            comm_badge = f" • 🪙 Comissao {comm}" if comm and comm != "0%" else ""
            
            text = f"{title[:55]}...\n💰 R$ {price:.2f} ({disc}% OFF)  •  {sales_badge}{comm_badge}".replace(",", ".")
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, p)
            self.list_products.addItem(item)

        # Seleciona o primeiro automaticamente
        if self.list_products.count() > 0:
            self.list_products.setCurrentRow(0)
            self._on_product_selected(self.list_products.item(0))

    def _on_search_error(self, err_msg):
        self.progress_bar.setVisible(False)
        self.btn_search.setEnabled(True)
        self.sig_log.emit(f"Erro na busca: {err_msg}", "error")
        QMessageBox.critical(self, "Erro", f"Não foi possível buscar produtos:\n{err_msg}")

    def _on_product_selected(self, item: QListWidgetItem):
        product = item.data(Qt.UserRole)
        if not product:
            return
        self.current_product = product

        # 1. Gera Copy
        title, desc = self.copy_engine.generate_copy(product)
        self.input_pin_title.setText(title)
        self.input_pin_desc.setText(desc)
        self.input_pin_link.setText(product.get("affiliate_link") or product.get("product_link", ""))

        # 2. Gera Imagem 1000x1500
        self._renderizar_preview_imagem()

    def _on_palette_changed(self, index: int):
        if self.current_product:
            self._renderizar_preview_imagem()

    def _regenerar_variacao_arte(self):
        if self.current_product:
            self.sig_log.emit("🎨 Gerando nova variação de cores e layout...", "info")
            self._renderizar_preview_imagem()

    def _renderizar_preview_imagem(self):
        if not self.current_product:
            return
        try:
            palette_key = self.combo_palette.currentData() or "auto"
            self.sig_log.emit(f"Gerando preview da montagem 1000x1500 (Paleta: {palette_key})...", "info")
            pil_img = self.img_engine.create_pin_image(
                self.current_product,
                palette_key=palette_key,
                custom_headline="auto"
            )
            self.current_pil_image = pil_img

            # Converte PIL para QPixmap escalonado
            qimg = self._pil_to_qimage(pil_img)
            pixmap = QPixmap.fromImage(qimg)
            self.lbl_image_preview.setPixmap(pixmap.scaled(
                self.lbl_image_preview.width(),
                self.lbl_image_preview.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            ))
        except Exception as e:
            self.sig_log.emit(f"Erro ao renderizar imagem do Pin: {e}", "warning")

    def _pil_to_qimage(self, pil_image: Image.Image) -> QImage:
        """Converte PIL Image RGB para QImage."""
        rgb_image = pil_image.convert("RGB")
        data = rgb_image.tobytes("raw", "RGB")
        return QImage(data, rgb_image.width, rgb_image.height, rgb_image.width * 3, QImage.Format_RGB888)

    def _publicar_pin_agora(self):
        if not self.current_product or not self.current_pil_image:
            QMessageBox.warning(self, "Atenção", "Selecione um produto e gere a imagem antes de publicar.")
            return

        board_id = self.combo_boards.currentData() or self.cfg.get("pinterest_board_id", "")
        board_name = self.combo_boards.currentText() or self.cfg.get("pinterest_board_name", "")
        post_method = self.cfg.get("post_method", "browser")
        palette_key = self.combo_palette.currentData() or "auto"
        post_format = self.combo_format.currentData() or "image"

        if post_method == "api" and not board_id:
            QMessageBox.warning(self, "Atenção", "Selecione uma pasta do Pinterest nas Configurações.")
            return

        title = self.input_pin_title.text().strip()
        desc = self.input_pin_desc.toPlainText().strip()
        link = self.input_pin_link.text().strip()
        self.current_product["affiliate_link"] = link

        self.btn_publish_now.setEnabled(False)
        self.btn_publish_now.setText("Publicando no Pinterest...")
        self.progress_bar.setVisible(True)

        self._worker_publish = WorkerPublishPin(
            product=self.current_product,
            title=title,
            description=desc,
            board_id=board_id,
            template="classic_deal",
            config=self.cfg,
            database=self.db,
            board_name=board_name,
            palette_key=palette_key,
            post_format=post_format
        )
        self._worker_publish.sig_log.connect(self.sig_log.emit)
        self._worker_publish.sig_success.connect(self._on_publish_success)
        self._worker_publish.sig_error.connect(self._on_publish_error)
        self._worker_publish.start()

    def _on_publish_success(self, res):
        self.btn_publish_now.setEnabled(True)
        self.btn_publish_now.setText("🚀 Publicar Agora no Pinterest")
        self.progress_bar.setVisible(False)
        url = res.get("pin_url", "")
        QMessageBox.information(self, "Sucesso", f"Pin publicado com sucesso no Pinterest!\n\nLink:\n{url}")

    def _on_publish_error(self, err):
        self.btn_publish_now.setEnabled(True)
        self.btn_publish_now.setText("🚀 Publicar Agora no Pinterest")
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Erro ao Publicar", f"Falha na publicação do Pin:\n{err}")
