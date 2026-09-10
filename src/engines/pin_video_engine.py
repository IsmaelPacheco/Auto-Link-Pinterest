"""
pin_video_engine.py
Motor de composição de vídeos curtos (.mp4) 100% nativo e local.
Gera animações verticais (1000x1500 px - 2:3 ou 9:16) de 5 a 6 segundos
com efeito Ken Burns (zoom suave), badge pulsante e botão com brilho.
Produz Pins de Vídeo de altíssimo alcance e engajamento no Pinterest!
"""
import io
import math
import logging
import random
from pathlib import Path
from typing import Dict, Any, Optional, List
import numpy as np
import imageio
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from src.engines.pin_image_engine import COLOR_PALETTES, VIRAL_HEADLINES, PinImageEngine

logger = logging.getLogger("AutoLink.VideoEngine")

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "workspace" / "pins"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class PinVideoEngine:
    """Renderiza vídeos animados de 5 a 6 segundos para o Pinterest."""

    WIDTH = 1000
    HEIGHT = 1500
    FPS = 24
    DURATION_SECONDS = 5  # 5 segundos = 120 frames

    def __init__(self, output_dir: Path = OUTPUT_DIR):
        self.output_dir = output_dir
        self.img_engine = PinImageEngine(output_dir)

    def _get_font(self, font_name: str, size: int) -> ImageFont.FreeTypeFont:
        return self.img_engine._get_font(font_name, size)

    def create_pin_video(
        self,
        product: Dict[str, Any],
        palette_key: str = "auto",
        custom_headline: str = "auto",
        filename_prefix: str = "pin"
    ) -> Path:
        """
        Cria um vídeo vertical 1000x1500 em formato .mp4 com animações suaves em loop.
        """
        item_id = str(product.get("item_id", "prod"))
        output_file = self.output_dir / f"{filename_prefix}_{item_id}.mp4"

        # 1. Seleciona Paleta e Headline
        if palette_key == "auto" or palette_key not in COLOR_PALETTES:
            chosen_palette = random.choice(list(COLOR_PALETTES.values()))
        else:
            chosen_palette = COLOR_PALETTES[palette_key]

        if custom_headline == "auto" or not custom_headline:
            headline_text = random.choice(VIRAL_HEADLINES)
        else:
            headline_text = custom_headline.upper()

        cor_fundo_topo = chosen_palette["bg_top"]
        cor_fundo_baixo = chosen_palette["bg_bottom"]
        cor_destaque = chosen_palette["highlight"]
        cor_badge = chosen_palette["badge"]
        cor_cta = chosen_palette["cta"]
        cor_texto_escuro = chosen_palette["text_main"]
        cor_texto_cinza = chosen_palette["text_muted"]

        # 2. Baixa a foto do produto
        img_url = product.get("image_url", "")
        raw_prod_img = self.img_engine.download_image(img_url)

        # 3. Pré-renderiza a base estática (Fundo + Card + Textos + Preços)
        base_canvas = Image.new("RGBA", (self.WIDTH, self.HEIGHT), (255, 255, 255, 255))
        base_draw = ImageDraw.Draw(base_canvas)

        # Gradiente de fundo
        for y in range(self.HEIGHT):
            ratio = y / self.HEIGHT
            r = int(cor_fundo_topo[0] * (1 - ratio) + cor_fundo_baixo[0] * ratio)
            g = int(cor_fundo_topo[1] * (1 - ratio) + cor_fundo_baixo[1] * ratio)
            b = int(cor_fundo_topo[2] * (1 - ratio) + cor_fundo_baixo[2] * ratio)
            base_draw.line([(0, y), (self.WIDTH, y)], fill=(r, g, b, 255))

        # Headline do topo (Pílula)
        font_header = self._get_font("segoeuib.ttf", 30)
        h_bbox = base_draw.textbbox((0, 0), headline_text, font=font_header)
        h_w = h_bbox[2] - h_bbox[0]
        h_h = h_bbox[3] - h_bbox[1]
        pill_pad_x = 35
        pill_pad_y = 15
        pill_x1 = (self.WIDTH - h_w) // 2 - pill_pad_x
        pill_y1 = 60
        pill_x2 = pill_x1 + h_w + (pill_pad_x * 2)
        pill_y2 = pill_y1 + h_h + (pill_pad_y * 2)

        base_draw.rounded_rectangle([pill_x1, pill_y1, pill_x2, pill_y2], radius=25, fill=cor_destaque)
        base_draw.text(((pill_x1 + pill_x2) / 2, (pill_y1 + pill_y2) / 2), headline_text, font=font_header, fill=(255, 255, 255, 255), anchor="mm")

        # Card do Produto
        card_x1 = 70
        card_y1 = 160
        card_x2 = self.WIDTH - 70
        card_y2 = 1000
        card_w = card_x2 - card_x1
        card_h = card_y2 - card_y1

        sombra = Image.new("RGBA", (self.WIDTH, self.HEIGHT), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(sombra)
        s_draw.rounded_rectangle([card_x1 + 6, card_y1 + 10, card_x2 + 6, card_y2 + 10], radius=30, fill=(0, 0, 0, 45))
        sombra = sombra.filter(ImageFilter.GaussianBlur(15))
        base_canvas = Image.alpha_composite(base_canvas, sombra)
        base_draw = ImageDraw.Draw(base_canvas)

        base_draw.rounded_rectangle([card_x1, card_y1, card_x2, card_y2], radius=30, fill=(255, 255, 255, 255))

        # Título do Produto
        raw_title = product.get("title", "Produto Shopee")
        font_title = self._get_font("segoeuib.ttf", 38)
        title_lines = self.img_engine._wrap_text(raw_title, font_title, self.WIDTH - 160, base_draw)[:2]
        title_y = 1040
        for line in title_lines:
            t_bbox = base_draw.textbbox((0, 0), line, font=font_title)
            t_w = t_bbox[2] - t_bbox[0]
            base_draw.text(((self.WIDTH - t_w) // 2, title_y), line, font=font_title, fill=cor_texto_escuro)
            title_y += 50

        # Preços (De / Por)
        orig_price = product.get("original_price", 0.0)
        disc_price = product.get("discount_price", 0.0)
        price_y = 1170
        if disc_price > 0:
            if orig_price > disc_price:
                font_orig = self._get_font("segoeui.ttf", 32)
                orig_text = f"De R$ {orig_price:.2f}".replace(".", ",")
                o_bbox = base_draw.textbbox((0, 0), orig_text, font=font_orig)
                o_w = o_bbox[2] - o_bbox[0]
                o_x = (self.WIDTH - o_w) // 2
                base_draw.text((o_x, price_y), orig_text, font=font_orig, fill=cor_texto_cinza)
                line_y = price_y + (o_bbox[3] - o_bbox[1]) // 2 + 3
                base_draw.line([(o_x - 4, line_y), (o_x + o_w + 4, line_y)], fill=cor_texto_cinza, width=3)
                price_y += 45

            font_price = self._get_font("segoeuib.ttf", 66)
            price_text = f"R$ {disc_price:.2f}".replace(".", ",")
            p_bbox = base_draw.textbbox((0, 0), price_text, font=font_price)
            p_w = p_bbox[2] - p_bbox[0]
            base_draw.text(((self.WIDTH - p_w) // 2, price_y), price_text, font=font_price, fill=cor_destaque)

        # Botão CTA
        cta_text = "CLIQUE NA IMAGEM PARA COMPRAR"
        font_cta = self._get_font("segoeuib.ttf", 34)
        cta_x1, cta_y1 = 90, 1350
        cta_x2, cta_y2 = self.WIDTH - 90, 1430

        s_btn = Image.new("RGBA", (self.WIDTH, self.HEIGHT), (0, 0, 0, 0))
        sb_draw = ImageDraw.Draw(s_btn)
        sb_draw.rounded_rectangle([cta_x1, cta_y1 + 5, cta_x2, cta_y2 + 5], radius=40, fill=(0, 0, 0, 35))
        s_btn = s_btn.filter(ImageFilter.GaussianBlur(8))
        base_canvas = Image.alpha_composite(base_canvas, s_btn)
        base_draw = ImageDraw.Draw(base_canvas)

        base_draw.rounded_rectangle([cta_x1, cta_y1, cta_x2, cta_y2], radius=40, fill=cor_cta)
        base_draw.text(((cta_x1 + cta_x2) / 2, (cta_y1 + cta_y2) / 2), cta_text, font=font_cta, fill=(255, 255, 255, 255), anchor="mm")

        # 4. Configura animação dos quadros
        total_frames = self.FPS * self.DURATION_SECONDS
        discount_pct = product.get("discount_pct", 0)

        # Prepara a imagem do produto base redimensionada
        base_img_w = card_w - 48
        base_img_h = card_h - 48
        scaled_prod_img = None
        if raw_prod_img:
            scaled_prod_img = raw_prod_img.copy()
            scaled_prod_img.thumbnail((base_img_w, base_img_h), Image.Resampling.LANCZOS)

        logger.info(f"Renderizando {total_frames} frames de vídeo animado para {output_file.name}...")

        # Escreve os frames diretamente no arquivo MP4
        writer = imageio.get_writer(
            str(output_file.resolve()),
            fps=self.FPS,
            codec="libx264",
            quality=8,
            pixelformat="yuv420p",
            macro_block_size=None
        )

        try:
            for frame_idx in range(total_frames):
                # Cria cópia do canvas base estático
                frame_canvas = base_canvas.copy()

                # A. Efeito Ken Burns (Zoom suave e contínuo de 1.00x para 1.07x)
                if scaled_prod_img:
                    progress = frame_idx / total_frames
                    zoom_factor = 1.00 + (0.07 * math.sin(progress * math.pi))  # Sobe suavemente e volta
                    cur_w = int(scaled_prod_img.width * zoom_factor)
                    cur_h = int(scaled_prod_img.height * zoom_factor)
                    zoomed_img = scaled_prod_img.resize((cur_w, cur_h), Image.Resampling.BILINEAR)

                    # Centraliza no card
                    img_x = card_x1 + (card_w - cur_w) // 2
                    img_y = card_y1 + (card_h - cur_h) // 2

                    # Corta se exceder o limite do card
                    frame_canvas.paste(zoomed_img, (img_x, img_y), zoomed_img if zoomed_img.mode == "RGBA" else None)

                # B. Badge de Desconto Pulsante
                if discount_pct and discount_pct > 0:
                    badge_draw = ImageDraw.Draw(frame_canvas)
                    badge_text = f"-{discount_pct}% OFF"
                    # Pulsação suave (frequência de ~1.5 segundos)
                    pulse = 1.0 + (0.06 * math.sin(frame_idx * (2 * math.pi / (self.FPS * 1.5))))
                    badge_font_size = int(34 * pulse)
                    font_badge_p = self._get_font("segoeuib.ttf", badge_font_size)

                    b_bbox = badge_draw.textbbox((0, 0), badge_text, font=font_badge_p)
                    bw = b_bbox[2] - b_bbox[0]
                    bh = b_bbox[3] - b_bbox[1]

                    bx1 = card_x1 + 24
                    by1 = card_y1 + 24
                    bx2 = bx1 + bw + int(48 * pulse)
                    by2 = by1 + bh + int(32 * pulse)

                    badge_draw.rounded_rectangle([bx1, by1, bx2, by2], radius=int(20 * pulse), fill=cor_badge)
                    badge_draw.text(((bx1 + bx2) / 2, (by1 + by2) / 2), badge_text, font=font_badge_p, fill=(255, 255, 255, 255), anchor="mm")

                # C. Efeito de Brilho Dinâmico (Shimmer) no Botão CTA
                # A cada 2.5 segundos, uma barra suave de luz passa pelo botão
                cycle_frame = frame_idx % int(self.FPS * 2.5)
                if cycle_frame < int(self.FPS * 0.8):  # Duração da passagem: 0.8s
                    shine_progress = cycle_frame / (self.FPS * 0.8)
                    shine_x = int(cta_x1 + shine_progress * (cta_x2 - cta_x1))
                    shine_layer = Image.new("RGBA", (self.WIDTH, self.HEIGHT), (0, 0, 0, 0))
                    sh_draw = ImageDraw.Draw(shine_layer)
                    sh_draw.rounded_rectangle(
                        [max(cta_x1, shine_x - 30), cta_y1, min(cta_x2, shine_x + 30), cta_y2],
                        radius=20,
                        fill=(255, 255, 255, 75)
                    )
                    frame_canvas = Image.alpha_composite(frame_canvas, shine_layer)

                # Converte para RGB e alimenta o escritor de vídeo
                frame_rgb = frame_canvas.convert("RGB")
                frame_array = np.array(frame_rgb)
                writer.append_data(frame_array)

        finally:
            writer.close()

        logger.info(f"Vídeo animado gerado com sucesso: {output_file.name} ({output_file.stat().st_size // 1024} KB)")
        return output_file
