"""
vitrine_engine.py
Motor de geração e sincronização da Vitrine Própria de Achadinhos (Web Mobile-First).
Compila os produtos aprovados do banco SQLite local em formato JSON e gera os arquivos
estáticos (HTML/CSS/JS) para hospedagem 100% gratuita no GitHub Pages ou Cloudflare Pages.
"""
import json
import logging
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from PIL import Image

from src.models.database import Database
from src.models.account_manager import AccountManager

logger = logging.getLogger("AutoLink.VitrineEngine")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VITRINE_DIR = PROJECT_ROOT / "vitrine"
DATA_DIR = VITRINE_DIR / "data"
VITRINE_IMAGES_DIR = VITRINE_DIR / "images"
DOCS_DIR = PROJECT_ROOT / "docs"  # Para deploy automático no GitHub Pages
DOCS_DATA_DIR = DOCS_DIR / "data"
DOCS_IMAGES_DIR = DOCS_DIR / "images"


class VitrineEngine:
    """Gerencia a compilação de dados e publicação da Vitrine Web de Achadinhos."""

    def __init__(self, database: Optional[Database] = None):
        self.db = database or Database()
        self.am = AccountManager()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        VITRINE_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        DOCS_DIR.mkdir(parents=True, exist_ok=True)
        DOCS_DATA_DIR.mkdir(parents=True, exist_ok=True)
        DOCS_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    def _infer_category(self, title: str, account_niche: str = "") -> str:
        """Categoriza o produto com base no nicho da conta e palavras do título."""
        t_low = title.lower()
        if any(w in t_low for w in ["panela", "cozinha", "processador", "triturador", "dispenser", "alho", "pote", "talher", "faca", "airfryer"]):
            return "Cozinha Prática"
        if any(w in t_low for w in ["organizador", "cabide", "gaveta", "armario", "geladeira", "prateleira", "sapateira"]):
            return "Casa & Organização"
        if any(w in t_low for w in ["fone", "bluetooth", "carregador", "led", "rgb", "mousepad", "magsafe", "suporte celular", "teclado", "usb", "smart"]):
            return "Gadgets & Setup"
        if any(w in t_low for w in ["luminaria", "quadro", "almofada", "decoracao", "vela", "espelho", "estilo"]):
            return "Decoração & Estilo"
        if any(w in t_low for w in ["maquiagem", "skincare", "pele", "escova", "cabelo", "secador", "esponja"]):
            return "Beleza & Cuidados"
        if any(w in t_low for w in ["mop", "vassoura", "esponja", "aspirador", "limpeza", "pano"]):
            return "Limpeza Inteligente"

        if account_niche:
            return account_niche.replace("🍳", "").replace("🏠", "").replace("✨", "").replace("💄", "").replace("🧹", "").strip()

        return "Achadinhos Gerais"

    def _extract_or_copy_thumbnail(self, image_path: str, item_num: int) -> str:
        """
        Gera thumbnail otimizado a partir de imagem local ou extrai frame de vídeo MP4.
        Retorna o caminho relativo 'images/thumb_{item_num}.jpg' ou vazio se falhar.
        """
        if not image_path:
            return ""

        img_p = Path(image_path)
        if not img_p.exists():
            return ""

        thumb_name = f"thumb_{item_num}.jpg"
        target_vitrine = VITRINE_IMAGES_DIR / thumb_name
        target_docs = DOCS_IMAGES_DIR / thumb_name

        # Se já existe em ambos os diretórios, reutiliza diretamente
        if target_vitrine.exists() and target_docs.exists():
            return f"images/{thumb_name}"

        try:
            im = None
            suffix = img_p.suffix.lower()

            if suffix == ".mp4":
                try:
                    import imageio.v3 as iio
                    frame = iio.imread(str(img_p), index=0)
                    im = Image.fromarray(frame)
                except Exception as ex_vid:
                    logger.warning(f"Erro ao extrair frame de vídeo {img_p}: {ex_vid}")
            else:
                try:
                    im = Image.open(str(img_p))
                except Exception as ex_img:
                    logger.warning(f"Erro ao abrir imagem {img_p}: {ex_img}")

            if im:
                im = im.convert("RGB")
                # Redimensiona mantendo proporção para no máximo 600x600 (alta nitidez e leve)
                im.thumbnail((600, 600), Image.Resampling.LANCZOS)
                
                im.save(target_vitrine, "JPEG", quality=82, optimize=True)
                im.save(target_docs, "JPEG", quality=82, optimize=True)
                return f"images/{thumb_name}"

        except Exception as e:
            logger.error(f"Falha ao gerar thumbnail para #{item_num} ({img_p}): {e}")

        return ""

    def compile_products(self) -> List[Dict[str, Any]]:
        """Lê os produtos do banco e compila a estrutura completa para a vitrine."""
        raw_products = self.db.get_all_vitrine_products()
        accounts_map = {acc.id: acc for acc in self.am.get_all_accounts()}

        compiled = []
        for p in raw_products:
            item_num = p.get("item_number") or p.get("id") or 1
            orig = float(p.get("original_price") or 0)
            disc = float(p.get("discount_price") or 0)

            discount_pct = 0
            if orig > 0 and disc > 0 and disc < orig:
                discount_pct = round(((orig - disc) / orig) * 100)

            acc_id = p.get("account_id") or "default"
            acc_obj = accounts_map.get(acc_id)
            acc_name = acc_obj.name if acc_obj else "Achadinhos Oficiais"
            acc_niche = acc_obj.niche if acc_obj else "Achadinhos"

            img_path = p.get("image_path") or ""

            # Prioridade da Imagem:
            # 1. URL pública direta (Shopee CDN)
            # 2. Thumbnail local gerado do arquivo de imagem ou vídeo MP4
            img_url = p.get("image_url") or ""
            if not img_url or not str(img_url).startswith("http"):
                thumb_rel = self._extract_or_copy_thumbnail(img_path, int(item_num))
                if thumb_rel:
                    img_url = thumb_rel

            category = self._infer_category(p.get("title", ""), acc_niche)

            compiled.append({
                "item_number": int(item_num),
                "title": p.get("title", "Produto Shopee"),
                "original_price": orig,
                "discount_price": disc,
                "discount_percent": discount_pct,
                "affiliate_link": p.get("affiliate_link", ""),
                "image_url": img_url,
                "image_path": img_path,
                "category": category,
                "account_id": acc_id,
                "account_name": acc_name,
                "created_at": p.get("created_at", "")
            })

        # Ordena sempre pelo número do achadinho decrescente (#42, #41...)
        compiled.sort(key=lambda x: x["item_number"], reverse=True)
        return compiled

    def sync_vitrine(self) -> Dict[str, Any]:
        """
        Sincroniza o banco de dados com os arquivos estáticos da Vitrine.
        Salva em `vitrine/data/products.json` e também copia para `docs/` (GitHub Pages).
        """
        try:
            products = self.compile_products()

            # 1. Salva em vitrine/data/products.json
            target_json = DATA_DIR / "products.json"
            with open(target_json, "w", encoding="utf-8") as f:
                json.dump(products, f, ensure_ascii=False, indent=2)

            # 2. Espelha para docs/ (GitHub Pages)
            with open(DOCS_DATA_DIR / "products.json", "w", encoding="utf-8") as f:
                json.dump(products, f, ensure_ascii=False, indent=2)

            # Copia index.html para docs/index.html se existir
            index_src = VITRINE_DIR / "index.html"
            if index_src.exists():
                with open(index_src, "r", encoding="utf-8") as f_in:
                    content = f_in.read()
                with open(DOCS_DIR / "index.html", "w", encoding="utf-8") as f_out:
                    f_out.write(content)

            # Garante sincronia dos thumbnails em docs/images
            if VITRINE_IMAGES_DIR.exists():
                for f in VITRINE_IMAGES_DIR.glob("*.jpg"):
                    doc_thumb = DOCS_IMAGES_DIR / f.name
                    if not doc_thumb.exists():
                        shutil.copy2(f, doc_thumb)

            logger.info(f"Vitrine sincronizada com sucesso! Total: {len(products)} achadinhos.")
            return {
                "success": True,
                "total_products": len(products),
                "json_path": str(target_json)
            }
        except Exception as e:
            logger.error(f"Erro ao sincronizar vitrine: {e}")
            return {"success": False, "error": str(e)}

    def get_public_url_instructions(self) -> Dict[str, str]:
        """Retorna as instruções e links para publicação 100% gratuita no GitHub Pages."""
        return {
            "github_pages_info": (
                "Sua vitrine já está configurada na pasta `/docs` do repositório!\n"
                "Para ativar seu link público gratuito na internet:\n"
                "1. Abra o repositório no GitHub: github.com/IsmaelPacheco/Auto-Link-Pinterest\n"
                "2. Vá em 'Settings' -> 'Pages'\n"
                "3. Em 'Branch', selecione 'main' (ou 'teste') e a pasta '/docs'\n"
                "4. Clique em 'Save'! Em 1 minuto seu link estará no ar: https://ismaelpacheco.github.io/Auto-Link-Pinterest/"
            ),
            "local_file": (VITRINE_DIR / "index.html").as_uri()
        }
