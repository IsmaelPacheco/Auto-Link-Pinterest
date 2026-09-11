"""
vitrine_engine.py
Motor de geração e sincronização da Vitrine Própria de Achadinhos (Web Mobile-First).
Compila os produtos aprovados do banco SQLite local em formato JSON e gera os arquivos
estáticos (HTML/CSS/JS) para hospedagem 100% gratuita no GitHub Pages ou Cloudflare Pages.
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.models.database import Database
from src.models.account_manager import AccountManager

logger = logging.getLogger("AutoLink.VitrineEngine")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VITRINE_DIR = PROJECT_ROOT / "vitrine"
DATA_DIR = VITRINE_DIR / "data"
DOCS_DIR = PROJECT_ROOT / "docs"  # Para deploy automático no GitHub Pages


class VitrineEngine:
    """Gerencia a compilação de dados e publicação da Vitrine Web de Achadinhos."""

    def __init__(self, database: Optional[Database] = None):
        self.db = database or Database()
        self.am = AccountManager()
        DATA_DIR.mkdir(parents=True, exist_ok=True)

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
            # Se for caminho local no Windows, pega apenas o nome do arquivo para web ou mantém
            img_rel = ""
            if img_path:
                img_p = Path(img_path)
                if img_p.exists():
                    img_rel = f"../{img_p.as_posix()}" if not img_p.is_absolute() else img_p.name

            category = self._infer_category(p.get("title", ""), acc_niche)

            compiled.append({
                "item_number": int(item_num),
                "title": p.get("title", "Produto Shopee"),
                "original_price": orig,
                "discount_price": disc,
                "discount_percent": discount_pct,
                "affiliate_link": p.get("affiliate_link", ""),
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

            # 2. Se a pasta docs/ existir ou para deploy no GitHub Pages, espelha
            DOCS_DIR.mkdir(parents=True, exist_ok=True)
            docs_data = DOCS_DIR / "data"
            docs_data.mkdir(parents=True, exist_ok=True)

            with open(docs_data / "products.json", "w", encoding="utf-8") as f:
                json.dump(products, f, ensure_ascii=False, indent=2)

            # Copia index.html para docs/index.html se existir
            index_src = VITRINE_DIR / "index.html"
            if index_src.exists():
                with open(index_src, "r", encoding="utf-8") as f_in:
                    content = f_in.read()
                with open(DOCS_DIR / "index.html", "w", encoding="utf-8") as f_out:
                    f_out.write(content)

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
