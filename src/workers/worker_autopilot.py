"""
worker_autopilot.py
Thread de automação contínua para o AutoLink Pinterest.
Executa buscas de produtos em promoção, filtra itens duplicados,
gera artes verticais, cria copys persuasivas e publica no Pinterest
distribuindo as postagens de forma inteligente ao longo do dia,
evitando postagens de madrugada e respeitando horários humanizados.
"""
import logging
import random
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from PySide6.QtCore import QThread, Signal

from src.models.config_manager import ConfigManager
from src.models.database import Database
from src.models.trending_catalog import TRENDING_NICHES, get_combined_viral_keywords
from src.engines.shopee_engine import ShopeeEngine
from src.engines.pinterest_engine import PinterestEngine
from src.engines.pinterest_browser_engine import PinterestBrowserEngine
from src.engines.pin_image_engine import PinImageEngine
from src.engines.pin_video_engine import PinVideoEngine
from src.engines.copy_engine import CopyEngine

logger = logging.getLogger("AutoLink.WorkerAutopilot")


class WorkerAutopilot(QThread):
    """Worker em segundo plano para o Piloto Automático."""

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

    def stop(self):
        """Para a execução do autopilot."""
        self._running = False

    def _sleep_with_check(self, seconds: int):
        """Aguarda um intervalo verificando periodicamente se o usuário mandou parar."""
        for s in range(seconds, 0, -1):
            if not self._running:
                break
            self.sig_countdown.emit(s)
            self.sig_status.emit(f"Próxima postagem em {s // 60:02d}:{s % 60:02d}")
            time.sleep(1)

    def _select_board(self, product: dict, all_boards: list, board_mode: str, rotation_index: int) -> tuple:
        """
        Retorna (board_id, board_name, motivo).
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

        idx = rotation_index % len(all_boards)
        selected = all_boards[idx]
        return selected["id"], selected["name"], f"Rotação ({idx + 1}/{len(all_boards)})"

    def _calculate_next_delay(self) -> int:
        """
        Calcula o tempo de espera (em segundos) até a próxima postagem,
        distribuindo perfeitamente as postagens ao longo do dia.
        """
        now = datetime.now()
        schedule_mode = self.cfg.get("schedule_mode", "distributed_day")

        # Modo alternativo simples por intervalo fixo
        if schedule_mode == "interval":
            base_minutes = int(self.cfg.get("auto_interval_minutes", 45))
            jitter_minutes = int(self.cfg.get("auto_jitter_minutes", 15))
            delay_minutes = max(10, base_minutes + random.randint(-jitter_minutes, jitter_minutes))
            return delay_minutes * 60

        # Modo padrão: Distribuição Inteligente ao Longo do Dia
        start_hour = int(self.cfg.get("day_start_hour", 8))
        end_hour = int(self.cfg.get("day_end_hour", 22))
        max_pins = int(self.cfg.get("max_pins_per_day", 10))
        today_count = self.db.get_pins_posted_today_count()

        # 1. Se já atingiu a meta do dia: aguarda até a manhã de amanhã
        if today_count >= max_pins:
            tomorrow = (now + timedelta(days=1)).replace(hour=start_hour, minute=0, second=0, microsecond=0)
            secs_until_tomorrow = int((tomorrow - now).total_seconds())
            self.sig_log.emit(
                f"🎉 Meta diária concluída ({today_count}/{max_pins} pins hoje)! "
                f"Repousando até amanhã às {start_hour:02d}:00.",
                "success"
            )
            return max(60, secs_until_tomorrow)

        # 2. Se a hora atual for antes do início das postagens do dia (ex: 05:00 da manhã)
        start_today = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        if now < start_today:
            secs_until_start = int((start_today - now).total_seconds())
            self.sig_log.emit(
                f"🌙 Fora do horário ativo matinal. As postagens do dia iniciarão às {start_hour:02d}:00.",
                "info"
            )
            return max(60, secs_until_start)

        # 3. Se a hora atual já passou do fim das postagens do dia (ex: 22:30 da noite)
        end_today = now.replace(hour=end_hour, minute=0, second=0, microsecond=0)
        if now >= end_today:
            tomorrow = (now + timedelta(days=1)).replace(hour=start_hour, minute=0, second=0, microsecond=0)
            secs_until_tomorrow = int((tomorrow - now).total_seconds())
            self.sig_log.emit(
                f"🌙 Horário noturno encerrado ({end_hour:02d}:00). Pausado para proteção da conta. "
                f"Retoma amanhã às {start_hour:02d}:00.",
                "info"
            )
            return max(60, secs_until_tomorrow)

        # 4. Estamos DENTRO da janela ativa do dia (entre start_hour e end_hour)
        remaining_pins = max_pins - today_count
        remaining_seconds = (end_today - now).total_seconds()

        # Divide os segundos restantes do dia pelas postagens restantes
        ideal_interval_secs = remaining_seconds / max(1, remaining_pins)

        # Adiciona variação randômica humanizada (+/- 15%)
        jitter_secs = int(ideal_interval_secs * 0.15)
        actual_delay_secs = int(ideal_interval_secs + random.randint(-jitter_secs, jitter_secs))

        # Garante no mínimo 10 minutos entre postagens
        actual_delay_secs = max(600, actual_delay_secs)

        delay_min = actual_delay_secs // 60
        next_time = now + timedelta(seconds=actual_delay_secs)

        self.sig_log.emit(
            f"📅 Distribuição ao Longo do Dia: {today_count}/{max_pins} pins postados hoje. "
            f"Próximo pin agendado para às {next_time.strftime('%H:%M')} (em ~{delay_min} min).",
            "info"
        )
        return actual_delay_secs

    def run(self):
        self.sig_status.emit("Piloto Automático Iniciado")
        self.sig_log.emit("🚀 Piloto Automático ativado com sucesso.", "info")

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

        all_boards = pinterest.get_boards()
        if not all_boards:
            default_id = self.cfg.get("pinterest_board_id", "")
            default_name = self.cfg.get("pinterest_board_name", "Pasta Padrão")
            if default_id or default_name:
                all_boards = [{"id": default_id, "name": default_name}]
            else:
                all_boards = [{"id": "", "name": "Pasta Padrão"}]

        rotation_index = 0

        while self._running:
            try:
                now = datetime.now()
                schedule_mode = self.cfg.get("schedule_mode", "distributed_day")
                start_hour = int(self.cfg.get("day_start_hour", 8))
                end_hour = int(self.cfg.get("day_end_hour", 22))
                max_pins = int(self.cfg.get("max_pins_per_day", 10))
                pins_today = self.db.get_pins_posted_today_count()

                # 1. Verifica limites e horários da janela diária
                if schedule_mode == "distributed_day":
                    start_today = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
                    end_today = now.replace(hour=end_hour, minute=0, second=0, microsecond=0)

                    # Se já atingiu a meta ou está de noite/madrugada, entra em modo repouso
                    if pins_today >= max_pins or now < start_today or now >= end_today:
                        wait_secs = self._calculate_next_delay()
                        self.sig_status.emit(f"Repouso ({pins_today}/{max_pins} pins hoje)")
                        self._sleep_with_check(wait_secs)
                        continue
                else:
                    if pins_today >= max_pins:
                        self.sig_log.emit(
                            f"🛡️ Limite diário anti-spam atingido ({pins_today}/{max_pins} pins hoje). Aguardando próximo ciclo.",
                            "warning"
                        )
                        self.sig_status.emit(f"Pausa: Limite diário atingido ({pins_today}/{max_pins})")
                        self._sleep_with_check(3600)
                        continue

                # 2. Seleciona keyword de busca (Combina palavras configuradas com termos virais)
                raw_keywords = self.cfg.get("search_keywords", "")
                user_keywords = [k.strip() for k in raw_keywords.split(",") if k.strip()]

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
                        min_sales=10      # Validação: histórico comprovado de compras
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
                self.sig_log.emit(f"🎯 Produto selecionado: {p_title[:50]}... (ID: {p_item_id})", "info")

                orig_link = selected_product.get("product_link") or selected_product.get("affiliate_link", "")
                affiliate_link = shopee.generate_affiliate_link(orig_link)
                selected_product["affiliate_link"] = affiliate_link

                # 6. Decide o Formato de Mídia (Vídeo Animado .mp4 ou Imagem Estática)
                post_format = self.cfg.get("post_format", "hybrid")
                if post_format == "hybrid":
                    # 50% chance de vídeo animado / 50% imagem estática (Equilíbrio de Ouro)
                    make_video = (random.random() < 0.5)
                elif post_format == "video":
                    make_video = True
                else:
                    make_video = False

                if make_video:
                    self.sig_status.emit("Renderizando vídeo animado (.mp4) com zoom e efeitos...")
                    video_engine = PinVideoEngine()
                    media_path = video_engine.create_pin_video(
                        selected_product,
                        palette_key="auto",
                        custom_headline="auto",
                        filename_prefix="auto_vid"
                    )
                    image_for_api = None
                    self.sig_log.emit(f"🎬 Vídeo animado (.mp4) gerado com sucesso: {media_path.name}", "info")
                else:
                    self.sig_status.emit("Renderizando imagem 1000x1500 com paleta dinâmica...")
                    image_for_api = img_engine.create_pin_image(
                        selected_product,
                        template=self.cfg.get("image_template", "classic_deal"),
                        palette_key="auto",
                        custom_headline="auto"
                    )
                    media_path = img_engine.save_pin_image(image_for_api, f"pin_{p_item_id}")
                    self.sig_log.emit(f"🎨 Arte vertical 1000x1500 com cores dinâmicas gerada: {media_path.name}", "info")

                # 7. Gera Título e Descrição Otimizados
                self.sig_status.emit("Elaborando título e descrição persuasiva...")
                pin_title, pin_desc = copy_engine.generate_copy(selected_product)

                # 8. Publica no Pinterest (Navegador Playwright ou API Oficial)
                post_method = self.cfg.get("post_method", "browser")
                self.sig_status.emit(f"Publicando em '{board_name}'...")

                if post_method == "browser":
                    tipo_desc = "Vídeo Animado (.mp4)" if make_video else "Imagem Vertical"
                    self.sig_log.emit(f"🌐 Publicando {tipo_desc} via Navegador na pasta '{board_name}'...", "info")
                    browser_engine = PinterestBrowserEngine()
                    headless = self.cfg.get("browser_headless", False)
                    res_pin = browser_engine.publish_pin(
                        image_path=str(media_path),
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
                    if not image_for_api:
                        image_for_api = img_engine.create_pin_image(selected_product, palette_key="auto", custom_headline="auto")
                    pin_result = pinterest.create_pin(
                        board_id=board_id,
                        title=pin_title,
                        description=pin_desc,
                        link=affiliate_link,
                        image_input=image_for_api,
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
                    image_path=str(media_path),
                    pinterest_pin_id=pin_id,
                    pinterest_board_id=board_id,
                    pinterest_url=pin_url,
                    status="SUCCESS"
                )

                self.sig_log.emit(f"✅ Pin publicado com sucesso! Link: {pin_url}", "success")
                self.sig_pin_published.emit({
                    "title": pin_title,
                    "url": pin_url,
                    "image_path": str(media_path),
                    "affiliate_link": affiliate_link
                })

                # 10. Calcula o próximo intervalo distribuído ao longo do dia
                next_wait_seconds = self._calculate_next_delay()
                self._sleep_with_check(next_wait_seconds)

            except Exception as e:
                logger.error(f"Erro no ciclo do autopilot: {e}", exc_info=True)
                self.sig_log.emit(f"❌ Erro no ciclo de automação: {e}", "error")
                self.sig_status.emit("Aguardando 2 min após erro...")
                self._sleep_with_check(120)

        self.sig_status.emit("Piloto Automático Parado")
        self.sig_log.emit("🛑 Piloto Automático finalizado.", "info")
        self.sig_finished.emit()
