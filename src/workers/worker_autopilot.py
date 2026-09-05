"""
worker_autopilot.py
Thread de automação contínua para o AutoLink Pinterest.
Executa buscas de produtos em promoção, filtra itens duplicados,
gera artes verticais, cria copys persuasivas e publica no Pinterest
respeitando rigorosamente limites de postagem diária e intervalos humanizados.
"""
import logging
import random
import re
import time
from pathlib import Path
from PySide6.QtCore import QThread, Signal

from src.models.config_manager import ConfigManager
from src.models.database import Database
from src.models.trending_catalog import TRENDING_NICHES, get_combined_viral_keywords
from src.engines.shopee_engine import ShopeeEngine
from src.engines.pinterest_engine import PinterestEngine
from src.engines.pinterest_browser_engine import PinterestBrowserEngine
from src.engines.pin_image_engine import PinImageEngine
from src.engines.copy_engine import CopyEngine

logger = logging.getLogger("AutoLink.WorkerAutopilot")


class WorkerAutopilot(QThread):
    """Worker em segundo plano para o Piloto Automático."""

    # Sinais para atualizar a interface
    sig_log = Signal(str, str)             # (mensagem, nivel: 'info', 'success', 'warning', 'error')
    sig_status = Signal(str)               # Texto de status atual
    sig_pin_published = Signal(dict)       # Dados do pin recém-publicado
    sig_countdown = Signal(int)            # Segundos restantes até a próxima postagem
    sig_finished = Signal()

    def __init__(self, config_manager: ConfigManager, database: Database):
        super().__init__()
        self.cfg = config_manager
        self.db = database
        self._running = True
        self._paused = False

    def stop(self):
        """Para a execução do autopilot."""
        self._running = False

    def _select_board(self, product: dict, all_boards: list, board_mode: str, rotation_index: int) -> tuple:
        """
        Retorna (board_id, board_name, motivo).
        - "single": usa a pasta padrão configurada.
        - "smart": tenta combinar termos do produto com nomes das pastas; se não der match, rotaciona.
        - "rotate": rotaciona sequencialmente entre as pastas disponíveis.
        """
        if not all_boards:
            default_id = self.cfg.get("pinterest_board_id", "")
            default_name = self.cfg.get("pinterest_board_name", "Pasta Padrão")
            return default_id, default_name, "Padrão"

        if board_mode == "single":
            default_id = self.cfg.get("pinterest_board_id", "")
            for b in all_boards:
                if b["id"] == default_id:
                    return b["id"], b["name"], "Pasta Fixa"
            return all_boards[0]["id"], all_boards[0]["name"], "Pasta Fixa"

        if board_mode == "smart":
            p_title = product.get("title", "").lower()
            for b in all_boards:
                b_name_lower = b["name"].lower()
                palavras = [w for w in re.findall(r"\w+", b_name_lower) if len(w) > 3 and w not in ("para", "com", "como", "mais")]
                for kw in palavras:
                    if kw in p_title:
                        return b["id"], b["name"], f"Nicho compatível ('{kw}')"

        # Modo "rotate" (ou fallback do smart)
        idx = rotation_index % len(all_boards)
        selected = all_boards[idx]
        return selected["id"], selected["name"], f"Rotação ({idx + 1}/{len(all_boards)})"

    def run(self):
        self.sig_status.emit("Piloto Automático Iniciado")
        self.sig_log.emit("🚀 Piloto Automático ativado com sucesso.", "info")

        # Instancia os motores com as credenciais atuais
        shopee = ShopeeEngine(
            app_id=self.cfg.get("shopee_app_id", ""),
            secret=self.cfg.get("shopee_secret", ""),
            country=self.cfg.get("shopee_country", "BR")
        )
        pinterest = PinterestEngine(
            access_token=self.cfg.get("pinterest_access_token", "")
        )
        img_engine = PinImageEngine()
        copy_engine = CopyEngine(
            gemini_key=self.cfg.get("gemini_key", "") or self.cfg.get("gemini_api_key", ""),
            use_gemini=self.cfg.get("use_gemini", True)
        )

        # Carrega lista de pastas da conta
        all_boards = pinterest.get_boards()
        if not all_boards:
            # Fallback para a pasta padrão configurada
            default_id = self.cfg.get("pinterest_board_id", "")
            default_name = self.cfg.get("pinterest_board_name", "Pasta Padrão")
            if default_id:
                all_boards = [{"id": default_id, "name": default_name}]
            else:
                self.sig_log.emit("❌ Erro: Nenhuma pasta/board do Pinterest encontrada nas Configurações!", "error")
                self.sig_status.emit("Erro: Selecione uma Pasta nas Configurações")
                self.sig_finished.emit()
                return

        rotation_index = 0
        board_mode = self.cfg.get("board_mode", "rotate")

        while self._running:
            try:
                # 1. Checa limite de segurança diário anti-spam
                max_pins = int(self.cfg.get("max_pins_per_day", 12))
                pins_today = self.db.get_pins_posted_today_count()
                if pins_today >= max_pins:
                    self.sig_log.emit(
                        f"🛡️ Limite diário anti-spam atingido ({pins_today}/{max_pins} pins hoje). Aguardando próximo ciclo.",
                        "warning"
                    )
                    self.sig_status.emit(f"Pausa: Limite diário atingido ({pins_today}/{max_pins})")
                    self._sleep_with_check(3600)  # Aguarda 1 hora antes de checar novamente
                    continue

                # 2. Seleciona keyword de busca (Combina palavras configuradas com termos virais)
                raw_keywords = self.cfg.get("search_keywords", "")
                user_keywords = [k.strip() for k in raw_keywords.split(",") if k.strip()]
                
                # Se o usuário configurou termos, usa 70% das vezes; 30% sorteia termos virais comprovados
                viral_list = [kw for n in TRENDING_NICHES.values() for kw in n["keywords"]]
                if user_keywords and random.random() < 0.7:
                    keyword = random.choice(user_keywords)
                else:
                    keyword = random.choice(viral_list) if viral_list else "achadinhos"

                self.sig_status.emit(f"Buscando ofertas para: '{keyword}'...")
                self.sig_log.emit(f"🔍 Varrendo ofertas mais vendidas na Shopee: '{keyword}'...", "info")

                products = []
                try:
                    products = shopee.search_promotions(
                        keyword=keyword,
                        page=random.randint(1, 3),
                        limit=20,
                        sort_type=2,      # 2 = Mais Vendidos (Top Sales)
                        min_sales=10      # Validação: só produtos com histórico de vendas
                    )
                except Exception as e:
                    self.sig_log.emit(f"⚠️ Erro ao consultar Shopee API: {e}", "warning")

                # 3. Encontra um produto que ainda não foi postado
                selected_product = None
                for p in products:
                    item_id = p.get("item_id")
                    if not self.db.is_already_posted(item_id):
                        selected_product = p
                        break

                if not selected_product:
                    self.sig_log.emit("⚠️ Nenhum produto inédito encontrado nesta página. Tentando novamente em breve...", "warning")
                    self._sleep_with_check(180)
                    continue

                # 4. Seleciona a pasta de destino (Gerenciamento Automático)
                current_mode = self.cfg.get("board_mode", "rotate")
                board_id, board_name, motivo = self._select_board(
                    selected_product, all_boards, current_mode, rotation_index
                )
                rotation_index += 1
                self.sig_log.emit(f"📁 Pasta de destino: '{board_name}' ({motivo})", "info")

                # 5. Processa o produto escolhido
                p_title = selected_product.get("title", "Produto Shopee")
                p_item_id = selected_product.get("item_id", "")
                self.sig_log.emit(f"📦 Produto selecionado: {p_title[:50]}...", "info")
                self.sig_status.emit("Gerando link de afiliado oficial...")

                # Gera link de afiliado oficial encurtado
                orig_link = selected_product.get("product_link", "")
                affiliate_link = shopee.generate_affiliate_link(orig_link)
                selected_product["affiliate_link"] = affiliate_link

                # 6. Monta a imagem vertical 1000x1500 com Pillow
                self.sig_status.emit("Renderizando imagem 1000x1500 (Pillow)...")
                image = img_engine.create_pin_image(
                    selected_product,
                    template=self.cfg.get("image_template", "classic_deal")
                )
                img_path = img_engine.save_pin_image(image, f"pin_{p_item_id}")
                self.sig_log.emit(f"🎨 Arte vertical 1000x1500 gerada com sucesso: {img_path.name}", "info")

                # 7. Gera Título e Descrição Otimizados
                self.sig_status.emit("Elaborando título e descrição persuasiva...")
                pin_title, pin_desc = copy_engine.generate_copy(selected_product)

                # 8. Publica no Pinterest (Navegador Playwright ou API Oficial)
                post_method = self.cfg.get("post_method", "browser")
                self.sig_status.emit(f"Publicando em '{board_name}'...")

                if post_method == "browser":
                    self.sig_log.emit(f"🌐 Publicando via Navegador na pasta '{board_name}'...", "info")
                    browser_engine = PinterestBrowserEngine()
                    headless = self.cfg.get("browser_headless", False)
                    res_pin = browser_engine.publish_pin(
                        image_path=str(img_path),
                        title=pin_title,
                        description=pin_desc,
                        link=affiliate_link,
                        board_name=board_name,
                        headless=headless
                    )
                    if not res_pin.get("success"):
                        raise Exception(res_pin.get("message", "Falha na publicação via navegador."))
                    pin_id = "browser_pin"
                    pin_url = res_pin.get("pin_url", "https://www.pinterest.com/")
                else:
                    self.sig_log.emit(f"📤 Enviando Pin para a API oficial na pasta '{board_name}'...", "info")
                    pin_result = pinterest.create_pin(
                        board_id=board_id,
                        title=pin_title,
                        description=pin_desc,
                        link=affiliate_link,
                        image_input=image,
                        alt_text=pin_title
                    )
                    pin_id = pin_result.get("pin_id", "")
                    pin_url = pin_result.get("pin_url", "")

                # 9. Registra no banco SQLite local
                self.db.add_pin(
                    shopee_item_id=p_item_id,
                    title=pin_title,
                    affiliate_link=affiliate_link,
                    original_price=selected_product.get("original_price"),
                    discount_price=selected_product.get("discount_price"),
                    image_path=str(img_path),
                    pinterest_pin_id=pin_id,
                    pinterest_board_id=board_id,
                    pinterest_url=pin_url,
                    status="SUCCESS"
                )

                self.sig_log.emit(f"✅ Pin publicado com sucesso! Link: {pin_url}", "success")
                self.sig_pin_published.emit({
                    "title": pin_title,
                    "url": pin_url,
                    "image_path": str(img_path),
                    "affiliate_link": affiliate_link
                })

                # 9. Calcula intervalo humanizado com variação anti-spam
                base_minutes = int(self.cfg.get("auto_interval_minutes", 45))
                jitter_minutes = int(self.cfg.get("auto_jitter_minutes", 15))
                # Variação randômica (+/- jitter)
                delay_minutes = max(10, base_minutes + random.randint(-jitter_minutes, jitter_minutes))
                total_seconds = delay_minutes * 60

                self.sig_log.emit(
                    f"⏳ Próxima postagem agendada em {delay_minutes} minutos (comportamento humanizado).",
                    "info"
                )

                # Contagem regressiva respeitando interrupção do usuário
                for s in range(total_seconds, 0, -1):
                    if not self._running:
                        break
                    self.sig_countdown.emit(s)
                    self.sig_status.emit(f"Próxima postagem em {s // 60:02d}:{s % 60:02d}")
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Erro no ciclo do autopilot: {e}", exc_info=True)
                self.sig_log.emit(f"❌ Erro no ciclo de automação: {e}", "error")
                self.sig_status.emit("Aguardando 2 min após erro...")
                self._sleep_with_check(120)

        self.sig_status.emit("Piloto Automático Parado")
        self.sig_log.emit("🛑 Piloto Automático finalizado.", "info")
        self.sig_finished.emit()

    def _sleep_with_check(self, seconds: int):
        """Dorme em intervalos curtos permitindo parar a thread instantaneamente."""
        for _ in range(seconds):
            if not self._running:
                break
            time.sleep(1)
