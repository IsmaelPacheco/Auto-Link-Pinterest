"""
worker_manual.py
Workers assíncronos para a aba Manual / Dashboard:
- WorkerSearchProduct: Busca ofertas na Shopee ou extrai produto via link.
- WorkerPublishPin: Cria imagem, copy e publica o Pin no Pinterest.
"""
from typing import Dict, Any, Optional
from PySide6.QtCore import QThread, Signal
from PIL import Image

from src.models.config_manager import ConfigManager
from src.models.database import Database
from src.engines.shopee_engine import ShopeeEngine
from src.engines.pinterest_engine import PinterestEngine
from src.engines.pinterest_browser_engine import PinterestBrowserEngine
from src.engines.pin_image_engine import PinImageEngine
from src.engines.pin_video_engine import PinVideoEngine
from src.engines.copy_engine import CopyEngine


class WorkerSearchProduct(QThread):
    """Worker para buscar produtos ou carregar via link."""
    sig_success = Signal(list)
    sig_error = Signal(str)

    def __init__(self, query_or_url: str, config: ConfigManager, sort_type: int = 2, min_sales: int = 0):
        super().__init__()
        self.query_or_url = query_or_url.strip()
        self.cfg = config
        self.sort_type = sort_type
        self.min_sales = min_sales

    def run(self):
        try:
            shopee = ShopeeEngine(
                app_id=self.cfg.get("shopee_app_id", ""),
                secret=self.cfg.get("shopee_secret", ""),
                country=self.cfg.get("shopee_country", "BR")
            )

            # Se for uma URL (começa com http)
            if self.query_or_url.startswith("http://") or self.query_or_url.startswith("https://"):
                prod = shopee.fetch_product_from_url(self.query_or_url)
                self.sig_success.emit([prod])
            else:
                # Busca por keyword
                if not shopee.is_configured():
                    self.sig_error.emit("Configure seu App ID e Secret da Shopee nas Configurações para buscar por palavras-chave.")
                    return
                prods = shopee.search_promotions(
                    keyword=self.query_or_url,
                    limit=25,
                    sort_type=self.sort_type,
                    min_sales=self.min_sales
                )
                self.sig_success.emit(prods)
        except Exception as e:
            self.sig_error.emit(str(e))


class WorkerBrowserLogin(QThread):
    """Worker para abrir o navegador de login sem travar a interface gráfica."""
    sig_result = Signal(dict)

    def run(self):
        try:
            engine = PinterestBrowserEngine()
            res = engine.open_login_window()
            self.sig_result.emit(res)
        except Exception as e:
            self.sig_result.emit({"success": False, "message": str(e)})


class WorkerPublishPin(QThread):
    """Worker para montar a arte e publicar um Pin individual."""
    sig_log = Signal(str, str)
    sig_success = Signal(dict)
    sig_error = Signal(str)

    def __init__(
        self,
        product: Dict[str, Any],
        title: str,
        description: str,
        board_id: str,
        template: str,
        config: ConfigManager,
        database: Database,
        board_name: str = "",
        palette_key: str = "auto",
        post_format: str = "image"
    ):
        super().__init__()
        self.product = product
        self.title = title
        self.description = description
        self.board_id = board_id
        self.template = template
        self.cfg = config
        self.db = database
        self.board_name = board_name
        self.palette_key = palette_key
        self.post_format = post_format

    def run(self):
        try:
            self.sig_log.emit("Iniciando publicação do Pin...", "info")

            shopee = ShopeeEngine(
                app_id=self.cfg.get("shopee_app_id", ""),
                secret=self.cfg.get("shopee_secret", "")
            )
            img_engine = PinImageEngine()

            # 1. Gera link de afiliado oficial encurtado se ainda não tiver
            orig_link = self.product.get("product_link") or self.product.get("affiliate_link", "")
            affiliate_link = self.product.get("affiliate_link")
            if not affiliate_link or affiliate_link == orig_link:
                affiliate_link = shopee.generate_affiliate_link(orig_link)
                self.product["affiliate_link"] = affiliate_link

            # 2. Renderiza a mídia (Vídeo animado .mp4 ou Imagem 1000x1500)
            if self.post_format == "video":
                self.sig_log.emit("🎬 Renderizando vídeo animado (.mp4) com zoom e efeitos...", "info")
                video_engine = PinVideoEngine()
                media_path = video_engine.create_pin_video(
                    self.product,
                    palette_key=self.palette_key,
                    filename_prefix="manual"
                )
                image_for_api = None
            else:
                self.sig_log.emit("Renderizando montagem vertical 1000x1500...", "info")
                image_for_api = img_engine.create_pin_image(
                    self.product,
                    template=self.template,
                    palette_key=self.palette_key
                )
                media_path = img_engine.save_pin_image(image_for_api, f"manual_{self.product.get('item_id', 'pin')}")

            post_method = self.cfg.get("post_method", "browser")

            if post_method == "browser":
                # 3A. Publicação via Navegador Automatizado (Playwright)
                tipo_midia = "Vídeo Animado (.mp4)" if self.post_format == "video" else "Imagem Vertical"
                self.sig_log.emit(f"🌐 Publicando {tipo_midia} via Navegador Automatizado...", "info")
                browser_engine = PinterestBrowserEngine()
                headless = self.cfg.get("browser_headless", False)
                
                target_board = self.board_name or self.cfg.get("pinterest_board_name", "")
                result = browser_engine.publish_pin(
                    image_path=str(media_path),
                    title=self.title,
                    description=self.description,
                    link=affiliate_link,
                    board_name=target_board,
                    headless=headless
                )

                if not result.get("success"):
                    raise Exception(result.get("message", "Falha desconhecida no navegador."))

                pin_id = "browser_pin"
                pin_url = result.get("pin_url", "https://www.pinterest.com/")

            else:
                # 3B. Publicação via API Oficial v5
                self.sig_log.emit("Enviando Pin para o Pinterest via API Oficial...", "info")
                pinterest = PinterestEngine(
                    access_token=self.cfg.get("pinterest_access_token", "")
                )
                if not image_for_api:
                    image_for_api = img_engine.create_pin_image(self.product, template=self.template, palette_key=self.palette_key)
                result = pinterest.create_pin(
                    board_id=self.board_id,
                    title=self.title,
                    description=self.description,
                    link=affiliate_link,
                    image_input=image_for_api
                )

                pin_id = result.get("pin_id", "")
                pin_url = result.get("pin_url", "")

            # 4. Salva no banco SQLite local
            self.db.add_pin(
                shopee_item_id=str(self.product.get("item_id", "")),
                title=self.title,
                affiliate_link=affiliate_link,
                original_price=self.product.get("original_price"),
                discount_price=self.product.get("discount_price"),
                image_path=str(media_path),
                pinterest_pin_id=pin_id,
                pinterest_board_id=self.board_id,
                pinterest_url=pin_url,
                status="SUCCESS"
            )

            self.sig_log.emit(f"✅ Pin publicado com sucesso! {pin_url}", "success")
            self.sig_success.emit({
                "pin_id": pin_id,
                "pin_url": pin_url,
                "image_path": str(img_path)
            })

        except Exception as e:
            self.sig_log.emit(f"Erro ao publicar: {e}", "error")
            self.sig_error.emit(str(e))

