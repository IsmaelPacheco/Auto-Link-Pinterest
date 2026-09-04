"""
trending_catalog.py
Catálogo de inteligência de tendências e palavras-chave virais
otimizadas para alta conversão no Pinterest e vendas na Shopee.
"""
from typing import Dict, List, Any

TRENDING_NICHES: Dict[str, Dict[str, Any]] = {
    "casa_organizacao": {
        "nome": "🏠 Casa & Organização",
        "keywords": [
            "organizador acrilico", "organizador maquiagem giratorio",
            "porta tempero giratorio", "caixa organizadora transparente",
            "sapateira vertical", "cabide magico multiuso",
            "prateleira adesiva banheiro", "dispenser detergente esponja",
            "organizador geladeira", "gaveta organizadora"
        ]
    },
    "cozinha_pratica": {
        "nome": "🍳 Cozinha Prática",
        "keywords": [
            "mini processador manual", "triturador alho eletrico",
            "selador de embalagens termico", "escorredor de louca retratil",
            "forma silicone airfryer", "dispenser azeite spray",
            "cortador legumes multifuncional", "pote hermetico vidro",
            "espatula silicone resistente"
        ]
    },
    "decoracao_estilo": {
        "nome": "✨ Decoração & Estilo",
        "keywords": [
            "luminaria led sensor movimento", "fita led rgb quarto",
            "espelho com led toque", "difusor aromaterapia ultrassonico",
            "porta retrato vintage", "quadro decorativo minimalista",
            "luminaria projetor galaxia astronauta", "vaso ceramica moderno"
        ]
    },
    "beleza_cuidados": {
        "nome": "💄 Beleza & Skincare",
        "keywords": [
            "escova secadora modeladora", "rolete pedra jade facial",
            "curvex termico eletrico", "kit pinceis maquiagem profissional",
            "massageador facial antirrugas", "esponja polvo limpeza facial",
            "organizador pincel maquiagem"
        ]
    },
    "utilidades_limpeza": {
        "nome": "🧹 Limpeza Inteligente",
        "keywords": [
            "mop giratorio lava seca", "escova limpeza eletrica giratoria",
            "aspirador portatil carro sem fio", "limpa vidros magnetico duplo",
            "esponja magica tira manchas", "escova de vaso sanitário silicone",
            "rodo magico retratil"
        ]
    },
    "jardim_piscina": {
        "nome": "🏊 Jardim & Piscina",
        "keywords": [
            "lona impermeavel reforçada", "kit limpeza piscina aspirador",
            "mangueira magica retratil expansivel", "cloro pastilha flutuador",
            "luminaria solar jardim led", "peneira piscina cabo telescopico"
        ]
    },
    "virais_tiktok": {
        "nome": "🔥 Achadinhos Virais Shopee",
        "keywords": [
            "achadinhos shopee", "produtos virais shopee",
            "utilidades domesticas criativas", "gadgets inteligentes casa",
            "produtos inovadores dia a dia", "itens que facilitam a vida"
        ]
    }
}

SORT_OPTIONS = [
    {"label": "🏆 Mais Vendidos (Top Sales)", "value": 2},
    {"label": "🏷️ Maior Desconto (% OFF)", "value": 4},
    {"label": "💰 Maior Comissão", "value": 3},
    {"label": "✨ Mais Recentes", "value": 1},
]

def get_all_niches() -> Dict[str, Dict[str, Any]]:
    return TRENDING_NICHES

def get_keywords_for_niche(niche_key: str) -> List[str]:
    niche = TRENDING_NICHES.get(niche_key)
    return niche["keywords"] if niche else []

def get_combined_viral_keywords() -> str:
    """Retorna uma lista combinada das melhores palavras-chave para o autopilot."""
    combined = []
    for niche in TRENDING_NICHES.values():
        combined.extend(niche["keywords"][:3])
    return ", ".join(combined[:20])

