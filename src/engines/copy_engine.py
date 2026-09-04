"""
copy_engine.py
Gerador inteligente de títulos, descrições persuasivas e hashtags otimizadas
para SEO do Pinterest.
Possui dois modos:
1. Templates Dinâmicos de Alta Conversão (100% offline e gratuito).
2. Google Gemini API (IA generativa gratuita para reescrita estilo review,
   com consulta prévia dos modelos disponíveis e fallback automático).
"""
import logging
import random
import re
import warnings
from typing import Dict, Any, Tuple, List

# Suprime warnings internos de SDK (ex: Automatic Function Calling)
warnings.filterwarnings("ignore", category=UserWarning)

logger = logging.getLogger("AutoLink.CopyEngine")

HOOKS = [
    "Olha esse achadinho que encontrei na Shopee! 🔥",
    "Melhor compra do mês na Shopee, vale muito a pena! ✨",
    "Você não vai acreditar no preço desse produto na Shopee 😱",
    "Achadinho perfeito para facilitar a sua rotina! 🛒",
    "Se você gosta de praticidade e economia, precisa ver isso! 💡",
    "Um dos produtos mais bem avaliados da Shopee! ⭐",
    "Achadinho imperdível com super desconto hoje! 🏷️",
    "Dica de ouro da Shopee que você precisava conhecer! 🎯"
]

BENEFITS = [
    "Super prático, resistente e com acabamento de excelente qualidade.",
    "Perfeito para quem busca funcionalidade e organização no dia a dia.",
    "Excelente custo-benefício com milhares de avaliações 5 estrelas.",
    "Item indispensável que vai transformar a sua rotina para melhor.",
    "Design moderno e alta durabilidade que surpreende positivamente."
]

CTAS = [
    "Toque na imagem para conferir as avaliações e garantir o seu desconto!",
    "Clique no link do Pin para ver todos os detalhes na Shopee!",
    "Aproveite o cupom de desconto tocando diretamente na foto!",
    "Toque na foto para acessar a loja oficial e conferir mais fotos!"
]

HASHTAG_POOLS = [
    "#achadinhosshopee", "#shopeebrasil", "#achadinhos", "#comprinhas",
    "#promocao", "#ofertas", "#utilidades", "#dicas", "#comprasshopee",
    "#casaorganizada", "#decoracao", "#praticidade", "#achadosshopee"
]


class CopyEngine:
    """Gera títulos, descrições e hashtags para Pins no Pinterest."""

    def __init__(self, gemini_key: str = "", use_gemini: bool = True):
        self.gemini_key = gemini_key.strip()
        self.use_gemini = use_gemini
        self._gemini_client = None
        self._available_models_cache = None

        if self.gemini_key and self.use_gemini:
            self._init_gemini()

    def _init_gemini(self):
        try:
            from google import genai
            self._gemini_client = genai.Client(api_key=self.gemini_key)
        except Exception as e:
            logger.warning(f"Não foi possível inicializar o cliente Gemini: {e}")
            self._gemini_client = None

    def _get_available_models(self) -> List[str]:
        """Consulta a API do Google para descobrir os modelos disponíveis na conta."""
        if self._available_models_cache:
            return self._available_models_cache

        if not self._gemini_client:
            return ["gemini-2.5-flash", "gemini-1.5-flash"]

        try:
            models_list = list(self._gemini_client.models.list())
            supported_names = [
                m.name.replace("models/", "")
                for m in models_list
                if "generateContent" in (getattr(m, "supported_actions", []) or ["generateContent"])
            ]

            # Prioridade ordenada de modelos recomendados (leves, rápidos e com quota gratuita)
            prioridades = [
                "gemini-2.5-flash",
                "gemini-2.5-flash-lite",
                "gemini-2.0-flash",
                "gemini-1.5-flash",
                "gemini-flash-latest",
                "gemini-3.1-flash-lite",
                "gemini-1.5-pro"
            ]
            selecionados = [m for m in prioridades if m in supported_names]
            
            # Adiciona outros modelos flash que não estejam na lista prioritária
            for m in supported_names:
                if "flash" in m.lower() and m not in selecionados and "tts" not in m.lower():
                    selecionados.append(m)

            if selecionados:
                self._available_models_cache = selecionados
                return selecionados

        except Exception as e:
            logger.warning(f"Erro ao listar modelos disponíveis no Google: {e}")

        # Fallback padrão
        return ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]

    def clean_title(self, raw_title: str) -> str:
        """Limpa títulos da Shopee removendo excesso de palavras-chave spam."""
        cleaned = re.sub(r"\[.*?\]|\(.*?\)", "", raw_title)
        cleaned = re.sub(r"\s*\|\s*Shopee.*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if len(cleaned) > 75:
            parts = cleaned.split(" ")
            shortened = ""
            for p in parts:
                if len(shortened) + len(p) + 1 <= 75:
                    shortened += (" " if shortened else "") + p
                else:
                    break
            cleaned = shortened
        return cleaned or "Achadinho Shopee"

    def generate_copy(self, product: Dict[str, Any]) -> Tuple[str, str]:
        """
        Gera (title, description) otimizados para o Pinterest.
        Consulta o Gemini com fallback em cascata; se indisponível, usa Templates.
        """
        if self._gemini_client and self.use_gemini:
            try:
                return self._generate_with_gemini(product)
            except Exception as e:
                logger.warning(f"Erro geral ao gerar com Gemini: {e}. Usando templates dinâmicos.")

        return self._generate_with_templates(product)

    def _generate_with_templates(self, product: Dict[str, Any]) -> Tuple[str, str]:
        """Gera copy com templates de alta conversão sem custo de API."""
        raw_title = product.get("title", "Produto Shopee")
        clean_name = self.clean_title(raw_title)
        
        disc_price = product.get("discount_price", 0.0)
        orig_price = product.get("original_price", 0.0)
        discount_pct = product.get("discount_pct", 0)

        prefix = random.choice(["Achadinho:", "Olha isso:", "Shopee:", "Incrível:"])
        title = f"{prefix} {clean_name}"
        if discount_pct > 0 and len(title) <= 85:
            title += f" (-{discount_pct}%)"
        title = title[:100]

        hook = random.choice(HOOKS)
        benefit = random.choice(BENEFITS)
        cta = random.choice(CTAS)
        
        price_info = ""
        if disc_price > 0:
            if orig_price > disc_price:
                price_info = f"💰 De R$ {orig_price:.2f} por apenas R$ {disc_price:.2f}!".replace(".", ",")
            else:
                price_info = f"💰 Por apenas R$ {disc_price:.2f}!".replace(".", ",")

        selected_tags = random.sample(HASHTAG_POOLS, k=min(6, len(HASHTAG_POOLS)))
        tags_str = " ".join(selected_tags)

        desc_parts = [
            hook,
            f"\n{clean_name}",
            benefit,
            price_info,
            f"\n{cta}",
            f"\n{tags_str}"
        ]
        description = "\n".join([p for p in desc_parts if p.strip()])
        return title, description[:800]

    def _generate_with_gemini(self, product: Dict[str, Any]) -> Tuple[str, str]:
        """Gera copy consultando os modelos disponíveis no Google com fallback automático."""
        title_orig = product.get("title", "")
        disc_price = product.get("discount_price", 0.0)
        discount_pct = product.get("discount_pct", 0)

        prompt = f"""
        Você é um especialista em marketing de afiliados para o Pinterest Brasil e criador de conteúdo no nicho de 'Achadinhos da Shopee'.
        Crie um Título e uma Descrição altamente persuasivos para um Pin de produto da Shopee.
        
        Dados do Produto:
        - Nome original: {title_orig}
        - Preço promocional: R$ {disc_price:.2f}
        - Desconto: {discount_pct}% OFF

        Regras Específicas:
        1. O Título deve ter NO MÁXIMO 80 caracteres. Deve ser chamativo, direto e sem clickbait falso.
        2. A Descrição deve ter entre 150 e 400 caracteres, escrita em tom autêntico de recomendação pessoal/resenha.
        3. Inclua no final da descrição uma chamada para ação clara (ex: "Toque na imagem para ver o desconto na Shopee") e 5 a 6 hashtags relevantes em português.
        4. Responda ESTRITAMENTE no seguinte formato:
        TITULO: [texto do título aqui]
        DESCRICAO: [texto da descrição aqui]
        """

        models_to_try = self._get_available_models()
        last_error = None
        text = ""

        for model_name in models_to_try:
            try:
                logger.info(f"Gerando copy com Gemini (modelo: {model_name})...")
                response = self._gemini_client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                if response and response.text:
                    text = response.text
                    break
            except Exception as e:
                last_error = e
                logger.warning(f"Modelo {model_name} indisponível: {e}. Tentando próximo modelo disponível...")
                continue

        if not text:
            if last_error:
                logger.warning(f"Todos os modelos Gemini testados falharam ({last_error}). Usando templates dinâmicos.")
            return self._generate_with_templates(product)

        match_title = re.search(r"TITULO:\s*(.+)", text, re.IGNORECASE)
        match_desc = re.search(r"DESCRICAO:\s*(.+)", text, re.IGNORECASE | re.DOTALL)

        title = match_title.group(1).strip() if match_title else f"Achadinho: {self.clean_title(title_orig)}"
        desc = match_desc.group(1).strip() if match_desc else self._generate_with_templates(product)[1]

        return title[:100], desc[:800]
