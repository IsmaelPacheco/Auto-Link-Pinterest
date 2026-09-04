"""
pin_image_engine.py
Motor de composição visual 100% nativo com Pillow (PIL).
Gera artes verticais em alta definição (1000x1500 pixels - proporção 2:3)
otimizadas para máxima taxa de cliques (CTR) no Pinterest.
"""
import io
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

logger = logging.getLogger("AutoLink.ImageEngine")

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "workspace" / "pins"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class PinImageEngine:
    """Gera artes profissionais de 1000x1500 para o Pinterest."""

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
        custom_headline: str = "ACHADINHOS DA SHOPEE"
    ) -> Image.Image:
        """
        Cria a montagem vertical 1000x1500 para o Pinterest.
        """
        # 1. Base Canvas 1000x1500
        canvas = Image.new("RGBA", (self.WIDTH, self.HEIGHT), (255, 255, 255, 255))
        draw = ImageDraw.Draw(canvas)

        # Paleta de Cores (Estilo Shopee / Pinterest)
        cor_fundo_topo = (255, 248, 244)
        cor_fundo_baixo = (255, 237, 230)
        cor_destaque = (238, 77, 45)      # Laranja Shopee
        cor_vermelho = (230, 0, 35)       # Vermelho Pinterest
        cor_texto_escuro = (34, 34, 34)
        cor_texto_cinza = (120, 120, 120)
        cor_cta = (238, 77, 45)

        # Gradiente de Fundo
        for y in range(self.HEIGHT):
            ratio = y / self.HEIGHT
            r = int(cor_fundo_topo[0] * (1 - ratio) + cor_fundo_baixo[0] * ratio)
            g = int(cor_fundo_topo[1] * (1 - ratio) + cor_fundo_baixo[1] * ratio)
            b = int(cor_fundo_topo[2] * (1 - ratio) + cor_fundo_baixo[2] * ratio)
            draw.line([(0, y), (self.WIDTH, y)], fill=(r, g, b, 255))

        # 2. Header / Badge Superior
        font_header = self._get_font("segoeuib.ttf", 30)
        header_text = custom_headline.upper()
        h_bbox = draw.textbbox((0, 0), header_text, font=font_header)
        h_w = h_bbox[2] - h_bbox[0]
        h_h = h_bbox[3] - h_bbox[1]

        # Pílula do cabeçalho
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
        # Centralização exata com anchor="mm"
        pill_cx = (pill_x1 + pill_x2) / 2
        pill_cy = (pill_y1 + pill_y2) / 2
        draw.text(
            (pill_cx, pill_cy),
            header_text,
            font=font_header,
            fill=(255, 255, 255, 255),
            anchor="mm"
        )

        # 3. Card do Produto com Foto
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
            # Redimensiona preservando proporção dentro do card
            margem_interna = 24
            max_img_w = card_w - (margem_interna * 2)
            max_img_h = card_h - (margem_interna * 2)

            raw_img.thumbnail((max_img_w, max_img_h), Image.Resampling.LANCZOS)
            
            # Centraliza a imagem no card
            img_x = card_x1 + (card_w - raw_img.width) // 2
            img_y = card_y1 + (card_h - raw_img.height) // 2

            # Mascara com cantos arredondados se a imagem preencher quase tudo
            canvas.paste(raw_img, (img_x, img_y), raw_img if raw_img.mode == "RGBA" else None)

        # 4. Badge de Desconto Flutuante (se houver desconto)
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

            draw.rounded_rectangle([bx1, by1, bx2, by2], radius=20, fill=cor_vermelho)
            badge_cx = (bx1 + bx2) / 2
            badge_cy = (by1 + by2) / 2
            draw.text((badge_cx, badge_cy), badge_text, font=font_badge, fill=(255, 255, 255, 255), anchor="mm")

        # 5. Título do Produto
        raw_title = product.get("title", "Produto Shopee")
        font_title = self._get_font("segoeuib.ttf", 38)
        title_lines = self._wrap_text(raw_title, font_title, self.WIDTH - 160, draw)
        
        # Limita a 2 linhas para ficar visualmente perfeito
        title_lines = title_lines[:2]
        title_y = 1040
        for line in title_lines:
            t_bbox = draw.textbbox((0, 0), line, font=font_title)
            t_w = t_bbox[2] - t_bbox[0]
            draw.text(((self.WIDTH - t_w) // 2, title_y), line, font=font_title, fill=cor_texto_escuro)
            title_y += 50

        # 6. Preços (De / Por)
        orig_price = product.get("original_price", 0.0)
        disc_price = product.get("discount_price", 0.0)

        price_y = 1170
        if disc_price > 0:
            # Se tem preço anterior, desenha com risco tachado
            if orig_price > disc_price:
                font_orig = self._get_font("segoeui.ttf", 32)
                orig_text = f"De R$ {orig_price:.2f}".replace(".", ",")
                o_bbox = draw.textbbox((0, 0), orig_text, font=font_orig)
                o_w = o_bbox[2] - o_bbox[0]
                o_x = (self.WIDTH - o_w) // 2
                draw.text((o_x, price_y), orig_text, font=font_orig, fill=cor_texto_cinza)
                # Linha tachada
                line_y = price_y + (o_bbox[3] - o_bbox[1]) // 2 + 3
                draw.line([(o_x - 4, line_y), (o_x + o_w + 4, line_y)], fill=cor_texto_cinza, width=3)
                price_y += 45

            # Preço Promocional em Destaque Gigante
            font_price = self._get_font("segoeuib.ttf", 66)
            price_text = f"R$ {disc_price:.2f}".replace(".", ",")
            p_bbox = draw.textbbox((0, 0), price_text, font=font_price)
            p_w = p_bbox[2] - p_bbox[0]
            draw.text(((self.WIDTH - p_w) // 2, price_y), price_text, font=font_price, fill=cor_destaque)

        # 7. Call To Action (Botão no Rodapé)
        cta_text = "CLIQUE NA IMAGEM PARA COMPRAR"
        font_cta = self._get_font("segoeuib.ttf", 34)
        c_bbox = draw.textbbox((0, 0), cta_text, font=font_cta)
        c_w = c_bbox[2] - c_bbox[0]
        c_h = c_bbox[3] - c_bbox[1]

        cta_x1 = 90
        cta_y1 = 1350
        cta_x2 = self.WIDTH - 90
        cta_y2 = 1430

        # Sombra suave do botão CTA
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

