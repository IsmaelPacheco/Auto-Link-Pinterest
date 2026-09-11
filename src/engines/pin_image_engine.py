"""
pin_image_engine.py
Motor de composição visual 100% nativo com Pillow (PIL).
Gera artes verticais em alta definição (1000x1500 pixels - proporção 2:3)
com biblioteca de 7 paletas harmônicas, headlines variadas e múltiplos templates.
Garante diversidade visual total para evitar penalização de spam no algoritmo do Pinterest!
"""
import io
import logging
import random
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

logger = logging.getLogger("AutoLink.ImageEngine")

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "workspace" / "pins"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 🎨 7 Paletas Harmônicas de Alta Conversão no Pinterest
COLOR_PALETTES: Dict[str, Dict[str, Any]] = {
    "shopee_warm": {
        "name": "Shopee Warm (Laranja & Sunset)",
        "bg_top": (255, 248, 244),
        "bg_bottom": (255, 237, 230),
        "highlight": (238, 77, 45),     # Laranja Shopee
        "badge": (230, 0, 35),          # Vermelho
        "cta": (238, 77, 45),
        "text_main": (34, 34, 34),
        "text_muted": (120, 120, 120),
    },
    "clean_nordic": {
        "name": "Clean Nordic (Bege & Minimalista)",
        "bg_top": (250, 248, 245),
        "bg_bottom": (242, 238, 233),
        "highlight": (180, 83, 9),      # Âmbar sofisticado
        "badge": (220, 38, 38),         # Vermelho tomate
        "cta": (28, 25, 23),            # Preto sofisticado
        "text_main": (28, 25, 23),
        "text_muted": (115, 115, 115),
    },
    "rose_gold": {
        "name": "Rose Gold & Blush (Beleza / Decoração / Estilo)",
        "bg_top": (255, 241, 242),
        "bg_bottom": (254, 226, 226),
        "highlight": (225, 29, 72),     # Framboesa vibrante
        "badge": (225, 29, 72),
        "cta": (190, 18, 60),
        "text_main": (30, 27, 75),
        "text_muted": (140, 100, 110),
    },
    "fresh_mint": {
        "name": "Fresh Mint (Organização / Cozinha / Limpeza)",
        "bg_top": (240, 253, 244),
        "bg_bottom": (220, 252, 231),
        "highlight": (16, 185, 129),    # Verde Esmeralda
        "badge": (239, 68, 68),
        "cta": (5, 150, 105),
        "text_main": (6, 78, 59),
        "text_muted": (80, 120, 100),
    },
    "lavender_modern": {
        "name": "Lavender Dream (Gadgets & Achadinhos TikTok)",
        "bg_top": (245, 243, 255),
        "bg_bottom": (237, 233, 254),
        "highlight": (124, 58, 237),    # Púrpura Vibrante
        "badge": (236, 72, 153),
        "cta": (109, 40, 217),
        "text_main": (46, 16, 101),
        "text_muted": (120, 100, 140),
    },
    "royal_indigo": {
        "name": "Royal Indigo (Elegância & Tech)",
        "bg_top": (238, 242, 255),
        "bg_bottom": (224, 231, 255),
        "highlight": (79, 70, 229),     # Índigo Royal
        "badge": (225, 29, 72),
        "cta": (67, 56, 202),
        "text_main": (30, 27, 75),
        "text_muted": (100, 110, 135),
    },
    "golden_honey": {
        "name": "Golden Honey (Utilidades / Gourmet / Praticidade)",
        "bg_top": (254, 252, 232),
        "bg_bottom": (254, 243, 199),
        "highlight": (217, 119, 6),     # Dourado Âmbar
        "badge": (220, 38, 38),
        "cta": (180, 83, 9),
        "text_main": (69, 26, 3),
        "text_muted": (130, 100, 50),
    }
}

# 📢 Headlines Virais com Variação Semântica (anti-OCR spam)
VIRAL_HEADLINES: List[str] = [
    "ACHADINHOS DA SHOPEE",
    "DICA DE OURO DA SHOPEE",
    "OFERTA RELÂMPAGO",
    "TESTADO E APROVADO",
    "ACHADO VIRAL SHOPEE",
    "TENDÊNCIA DO MOMENTO",
    "VALE CADA CENTAVO",
    "SUPER RECOMENDADO",
    "UTILIDADE INDISPENSÁVEL"
]


class PinImageEngine:
    """Gera artes profissionais de 1000x1500 com variedade visual anti-spam."""

    WIDTH = 1000
    HEIGHT = 1500

    def __init__(self, output_dir: Path = OUTPUT_DIR):
        self.output_dir = output_dir

    def _get_font(self, font_name: str, size: int) -> ImageFont.FreeTypeFont:
        """Tenta carregar fontes nativas do Windows com fallback seguro."""
        candidatas = [
            f"C:/Windows/Fonts/{font_name}",
            f"C:/Windows/Fonts/segoeuib.ttf",
            f"C:/Windows/Fonts/segoeui.ttf",
            f"C:/Windows/Fonts/arialbd.ttf",
            f"C:/Windows/Fonts/arial.ttf",
            f"C:/Windows/Fonts/calibrib.ttf",
            f"C:/Windows/Fonts/calibri.ttf",
        ]
        for c in candidatas:
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                continue
        return ImageFont.load_default()

    def download_image(self, url: str) -> Optional[Image.Image]:
        """Baixa a imagem da Shopee e retorna um objeto PIL.Image RGB."""
        if not url:
            return None
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
                return img
        except Exception as e:
            logger.error(f"Erro ao baixar imagem {url}: {e}")
        return None

    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw) -> list:
        """Quebra o texto em linhas para caber dentro da largura máxima."""
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            test_line = " ".join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            line_width = bbox[2] - bbox[0]
            if line_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]

        if current_line:
            lines.append(" ".join(current_line))
        return lines

    def create_pin_image(
        self,
        product: Dict[str, Any],
        template: str = "classic_deal",
        palette_key: str = "auto",
        custom_headline: str = "auto",
        item_number: Optional[int] = None
    ) -> Image.Image:
        """
        Cria a montagem vertical 1000x1500 com paletas e elementos dinâmicos.
        - template: 'classic_deal', 'editorial_clean', 'viral_showcase' ou 'auto'
        - palette_key: chave em COLOR_PALETTES ou 'auto' (sorteia paleta diferente para cada pin)
        - custom_headline: texto superior ou 'auto' (sorteia frases virais para diversificar o OCR)
        - item_number: número do achadinho na vitrine (#42)
        """
        # 1. Seleciona Paleta de Cores
        if palette_key == "auto" or palette_key not in COLOR_PALETTES:
            chosen_palette = random.choice(list(COLOR_PALETTES.values()))
        else:
            chosen_palette = COLOR_PALETTES[palette_key]

        # 2. Seleciona Headline
        num = item_number or product.get("item_number")
        if num:
            headline_text = f"🔥 ACHADINHO #{num}"
        elif custom_headline == "auto" or not custom_headline:
            headline_text = random.choice(VIRAL_HEADLINES)
        else:
            headline_text = custom_headline.upper()

        # 3. Base Canvas 1000x1500
        canvas = Image.new("RGBA", (self.WIDTH, self.HEIGHT), (255, 255, 255, 255))
        draw = ImageDraw.Draw(canvas)

        cor_fundo_topo = chosen_palette["bg_top"]
        cor_fundo_baixo = chosen_palette["bg_bottom"]
        cor_destaque = chosen_palette["highlight"]
        cor_badge = chosen_palette["badge"]
        cor_cta = chosen_palette["cta"]
        cor_texto_escuro = chosen_palette["text_main"]
        cor_texto_cinza = chosen_palette["text_muted"]

        # Gradiente Suave de Fundo
        for y in range(self.HEIGHT):
            ratio = y / self.HEIGHT
            r = int(cor_fundo_topo[0] * (1 - ratio) + cor_fundo_baixo[0] * ratio)
            g = int(cor_fundo_topo[1] * (1 - ratio) + cor_fundo_baixo[1] * ratio)
            b = int(cor_fundo_topo[2] * (1 - ratio) + cor_fundo_baixo[2] * ratio)
            draw.line([(0, y), (self.WIDTH, y)], fill=(r, g, b, 255))

        # 4. Header / Badge Superior
        font_header = self._get_font("segoeuib.ttf", 30)
        h_bbox = draw.textbbox((0, 0), headline_text, font=font_header)
        h_w = h_bbox[2] - h_bbox[0]
        h_h = h_bbox[3] - h_bbox[1]

        pill_pad_x = 35
        pill_pad_y = 15
        pill_x1 = (self.WIDTH - h_w) // 2 - pill_pad_x
        pill_y1 = 60
        pill_x2 = pill_x1 + h_w + (pill_pad_x * 2)
        pill_y2 = pill_y1 + h_h + (pill_pad_y * 2)

        draw.rounded_rectangle(
            [pill_x1, pill_y1, pill_x2, pill_y2],
            radius=25,
            fill=cor_destaque
        )
        pill_cx = (pill_x1 + pill_x2) / 2
        pill_cy = (pill_y1 + pill_y2) / 2
        draw.text(
            (pill_cx, pill_cy),
            headline_text,
            font=font_header,
            fill=(255, 255, 255, 255),
            anchor="mm"
        )

        # 5. Card do Produto com Foto
        card_x1 = 70
        card_y1 = 160
        card_x2 = self.WIDTH - 70
        card_y2 = 1000
        card_w = card_x2 - card_x1
        card_h = card_y2 - card_y1

        # Sombra suave do card
        sombra = Image.new("RGBA", (self.WIDTH, self.HEIGHT), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(sombra)
        s_draw.rounded_rectangle(
            [card_x1 + 6, card_y1 + 10, card_x2 + 6, card_y2 + 10],
            radius=30,
            fill=(0, 0, 0, 45)
        )
        sombra = sombra.filter(ImageFilter.GaussianBlur(15))
        canvas = Image.alpha_composite(canvas, sombra)
        draw = ImageDraw.Draw(canvas)

        # Fundo do card
        draw.rounded_rectangle(
            [card_x1, card_y1, card_x2, card_y2],
            radius=30,
            fill=(255, 255, 255, 255)
        )

        # Baixar e Inserir a Foto do Produto
        img_url = product.get("image_url", "")
        raw_img = self.download_image(img_url)
        if raw_img:
            margem_interna = 24
            max_img_w = card_w - (margem_interna * 2)
            max_img_h = card_h - (margem_interna * 2)

            raw_img.thumbnail((max_img_w, max_img_h), Image.Resampling.LANCZOS)
            img_x = card_x1 + (card_w - raw_img.width) // 2
            img_y = card_y1 + (card_h - raw_img.height) // 2

            canvas.paste(raw_img, (img_x, img_y), raw_img if raw_img.mode == "RGBA" else None)

        # 6. Badge de Desconto Flutuante
        discount_pct = product.get("discount_pct", 0)
        if discount_pct and discount_pct > 0:
            badge_text = f"-{discount_pct}% OFF"
            font_badge = self._get_font("segoeuib.ttf", 34)
            b_bbox = draw.textbbox((0, 0), badge_text, font=font_badge)
            b_w = b_bbox[2] - b_bbox[0]
            b_h = b_bbox[3] - b_bbox[1]

            pad_x = 24
            pad_y = 16
            bx1 = card_x1 + 24
            by1 = card_y1 + 24
            bx2 = bx1 + b_w + (pad_x * 2)
            by2 = by1 + b_h + (pad_y * 2)

            draw.rounded_rectangle([bx1, by1, bx2, by2], radius=20, fill=cor_badge)
            badge_cx = (bx1 + bx2) / 2
            badge_cy = (by1 + by2) / 2
            draw.text((badge_cx, badge_cy), badge_text, font=font_badge, fill=(255, 255, 255, 255), anchor="mm")

        # 7. Título do Produto
        raw_title = product.get("title", "Produto Shopee")
        font_title = self._get_font("segoeuib.ttf", 38)
        title_lines = self._wrap_text(raw_title, font_title, self.WIDTH - 160, draw)
        title_lines = title_lines[:2]
        title_y = 1040
        for line in title_lines:
            t_bbox = draw.textbbox((0, 0), line, font=font_title)
            t_w = t_bbox[2] - t_bbox[0]
            draw.text(((self.WIDTH - t_w) // 2, title_y), line, font=font_title, fill=cor_texto_escuro)
            title_y += 50

        # 8. Preços (De / Por)
        orig_price = product.get("original_price", 0.0)
        disc_price = product.get("discount_price", 0.0)

        price_y = 1170
        if disc_price > 0:
            if orig_price > disc_price:
                font_orig = self._get_font("segoeui.ttf", 32)
                orig_text = f"De R$ {orig_price:.2f}".replace(".", ",")
                o_bbox = draw.textbbox((0, 0), orig_text, font=font_orig)
                o_w = o_bbox[2] - o_bbox[0]
                o_x = (self.WIDTH - o_w) // 2
                draw.text((o_x, price_y), orig_text, font=font_orig, fill=cor_texto_cinza)
                line_y = price_y + (o_bbox[3] - o_bbox[1]) // 2 + 3
                draw.line([(o_x - 4, line_y), (o_x + o_w + 4, line_y)], fill=cor_texto_cinza, width=3)
                price_y += 45

            font_price = self._get_font("segoeuib.ttf", 66)
            price_text = f"R$ {disc_price:.2f}".replace(".", ",")
            p_bbox = draw.textbbox((0, 0), price_text, font=font_price)
            p_w = p_bbox[2] - p_bbox[0]
            draw.text(((self.WIDTH - p_w) // 2, price_y), price_text, font=font_price, fill=cor_destaque)

        # 9. Call To Action (Botão no Rodapé com Cor Harmônica)
        cta_text = "CLIQUE NA IMAGEM PARA COMPRAR"
        font_cta = self._get_font("segoeuib.ttf", 34)
        c_bbox = draw.textbbox((0, 0), cta_text, font=font_cta)

        cta_x1 = 90
        cta_y1 = 1350
        cta_x2 = self.WIDTH - 90
        cta_y2 = 1430

        s_btn = Image.new("RGBA", (self.WIDTH, self.HEIGHT), (0, 0, 0, 0))
        sb_draw = ImageDraw.Draw(s_btn)
        sb_draw.rounded_rectangle([cta_x1, cta_y1 + 5, cta_x2, cta_y2 + 5], radius=40, fill=(0, 0, 0, 35))
        s_btn = s_btn.filter(ImageFilter.GaussianBlur(8))
        canvas = Image.alpha_composite(canvas, s_btn)
        draw = ImageDraw.Draw(canvas)

        draw.rounded_rectangle([cta_x1, cta_y1, cta_x2, cta_y2], radius=40, fill=cor_cta)
        cta_cx = (cta_x1 + cta_x2) / 2
        cta_cy = (cta_y1 + cta_y2) / 2
        draw.text(
            (cta_cx, cta_cy),
            cta_text,
            font=font_cta,
            fill=(255, 255, 255, 255),
            anchor="mm"
        )

        final_rgb = canvas.convert("RGB")
        return final_rgb

    def save_pin_image(self, image: Image.Image, filename: str) -> Path:
        """Salva a imagem em disco em formato JPEG otimizado."""
        file_path = self.output_dir / f"{filename}.jpg"
        image.save(file_path, "JPEG", quality=92, optimize=True)
        return file_path
