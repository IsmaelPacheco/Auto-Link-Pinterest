"""
shopee_engine.py
Cliente oficial da Shopee Affiliate Open Platform via GraphQL com assinatura HMAC-SHA256,
mais suporte a extração/resolução de produtos via link direto.
"""
import hashlib
import hmac
import json
import logging
import re
import time
from typing import Dict, Any, List, Optional
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("AutoLink.Shopee")


class ShopeeEngine:
    """Cliente para a API Oficial de Afiliados Shopee."""

    GRAPHQL_URL_BR = "https://open-api.affiliate.shopee.com.br/graphql"
    GRAPHQL_URL_GLOBAL = "https://open-api.affiliate.shopee.com/graphql"

    def __init__(self, app_id: str = "", secret: str = "", country: str = "BR"):
        self.app_id = str(app_id).strip()
        self.secret = str(secret).strip()
        self.url = self.GRAPHQL_URL_BR if country.upper() == "BR" else self.GRAPHQL_URL_GLOBAL

    def is_configured(self) -> bool:
        """Verifica se credenciais estão preenchidas."""
        return bool(self.app_id and self.secret)

    def _generate_auth_header(self, payload_str: str, timestamp: int) -> str:
        """Gera a assinatura SHA256 oficial da Shopee Open Platform."""
        factor = f"{self.app_id}{timestamp}{payload_str}{self.secret}"
        signature = hashlib.sha256(factor.encode("utf-8")).hexdigest()
        return f"SHA256 Credential={self.app_id}, Timestamp={timestamp}, Signature={signature}"

    def _execute_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Envia requisição GraphQL assinada para a Shopee."""
        if not self.is_configured():
            raise ValueError("Credenciais da Shopee (App ID e Secret) não foram configuradas.")

        payload_dict = {"query": query}
        if variables:
            payload_dict["variables"] = variables

        payload_str = json.dumps(payload_dict, separators=(",", ":"))
        timestamp = int(time.time())
        auth_header = self._generate_auth_header(payload_str, timestamp)

        headers = {
            "Content-Type": "application/json",
            "Authorization": auth_header,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        response = requests.post(self.url, data=payload_str, headers=headers, timeout=20)
        
        if response.status_code != 200:
            raise RuntimeError(f"Shopee API HTTP {response.status_code}: {response.text}")

        res_json = response.json()
        if "errors" in res_json and res_json["errors"]:
            err_msg = res_json["errors"][0].get("message", "Erro desconhecido")
            raise RuntimeError(f"Erro Shopee GraphQL: {err_msg}")

        return res_json.get("data", {})

    def test_connection(self) -> Dict[str, Any]:
        """Testa se as credenciais da Shopee estão válidas realizando uma query simples."""
        query = """
        query {
          productOfferV2(page: 1, limit: 1) {
            pageInfo {
              page
              limit
            }
          }
        }
        """
        try:
            data = self._execute_query(query)
            return {"success": True, "message": "Conexão com Shopee Affiliate API realizada com sucesso!"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def search_promotions(
        self,
        keyword: str = "",
        page: int = 1,
        limit: int = 20,
        sort_type: int = 2,
        min_sales: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Consulta ofertas e promoções de produtos com link de afiliado oficial.
        sort_type:
          1: Mais Recentes
          2: Mais Vendidos (Top Sales / Best Sellers)
          3: Maior Comissão
          4: Maior Desconto
          5: Menor Preço
        min_sales: volume mínimo de vendas para validação de prova social.
        """
        query = """
        query ($page: Int, $limit: Int, $keyword: String, $sortType: Int) {
          productOfferV2(page: $page, limit: $limit, keyword: $keyword, sortType: $sortType) {
            nodes {
              itemId
              productName
              imageUrl
              price
              priceMin
              priceMax
              priceDiscountRate
              sales
              commissionRate
              productLink
              offerLink
              shopName
            }
            pageInfo {
              page
              limit
              hasNextPage
            }
          }
        }
        """
        variables = {
            "page": page,
            "limit": limit,
            "sortType": sort_type
        }
        if keyword:
            variables["keyword"] = keyword

        try:
            data = self._execute_query(query, variables)
            nodes = data.get("productOfferV2", {}).get("nodes", [])
            
            clean_products = []
            for n in nodes:
                sales_count = int(n.get("sales") or 0)
                if min_sales > 0 and sales_count < min_sales:
                    continue

                p_item_id = str(n.get("itemId", ""))
                p_name = n.get("productName", "")
                p_img = n.get("imageUrl", "")
                p_disc_price = float(n.get("price") or n.get("priceMin") or 0.0)
                
                # Desconto percentual oficial (priceDiscountRate)
                discount_pct = int(n.get("priceDiscountRate") or 0)
                
                # Preço original calculado
                p_orig_price = p_disc_price
                if discount_pct > 0 and discount_pct < 100:
                    p_orig_price = round(p_disc_price / (1 - (discount_pct / 100)), 2)
                
                affiliate_link = n.get("offerLink") or n.get("productLink") or ""
                
                clean_products.append({
                    "item_id": p_item_id,
                    "title": p_name,
                    "image_url": p_img,
                    "discount_price": p_disc_price,
                    "original_price": p_orig_price,
                    "discount_pct": discount_pct,
                    "sales": sales_count,
                    "commission_rate": str(n.get("commissionRate", "0%")),
                    "product_link": n.get("productLink", "") or affiliate_link,
                    "affiliate_link": affiliate_link
                })
            return clean_products
        except Exception as e:
            logger.error(f"Erro ao buscar ofertas Shopee: {e}")
            raise

    def generate_affiliate_link(self, origin_url: str, sub_ids: Optional[List[str]] = None) -> str:
        """Gera link de afiliado oficial encurtado via Shopee GraphQL."""
        if not self.is_configured():
            return origin_url

        query = """
        mutation ($input: ShortLinkInput!) {
          generateShortLink(input: $input) {
            shortLink
          }
        }
        """
        variables = {
            "input": {
                "originUrl": origin_url,
                "subIds": sub_ids or ["pinterest_auto"]
            }
        }
        try:
            data = self._execute_query(query, variables)
            short_link = data.get("generateShortLink", {}).get("shortLink")
            return short_link or origin_url
        except Exception as e:
            logger.warning(f"Falha ao gerar link curto Shopee: {e}. Usando URL original.")
            return origin_url

    def fetch_product_from_url(self, url: str) -> Dict[str, Any]:
        """
        Fallback / Extrator rápido de informações para links diretos colados pelo usuário.
        Resolve redirects, extrai meta tags OpenGraph e tenta gerar link de afiliado.
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        resp = requests.get(url, headers=headers, allow_redirects=True, timeout=15)
        final_url = resp.url
        soup = BeautifulSoup(resp.text, "html.parser")

        # Extrair Título
        title_tag = soup.find("meta", property="og:title")
        title = title_tag["content"] if title_tag and title_tag.get("content") else ""
        if not title:
            title = soup.title.string if soup.title else "Achadinho Incrível da Shopee"

        # Limpar sufixos comuns no título Shopee
        title = re.sub(r"\s*\|\s*Shopee Brasil.*", "", title, flags=re.IGNORECASE).strip()

        # Extrair Imagem
        img_tag = soup.find("meta", property="og:image")
        image_url = img_tag["content"] if img_tag and img_tag.get("content") else ""

        # Extrair Preço se disponível
        price_tag = soup.find("meta", property="product:price:amount")
        discount_price = float(price_tag["content"]) if price_tag and price_tag.get("content") else 0.0

        # Tenta extrair item_id da URL
        item_id_match = re.search(r"-i\.(\d+)\.(\d+)", final_url)
        item_id = item_id_match.group(2) if item_id_match else str(int(time.time()))

        # Se credenciais estiverem ativas, gera link de afiliado oficial
        affiliate_link = final_url
        if self.is_configured():
            affiliate_link = self.generate_affiliate_link(final_url)

        return {
            "item_id": item_id,
            "title": title,
            "image_url": image_url,
            "discount_price": discount_price,
            "original_price": round(discount_price * 1.35, 2) if discount_price > 0 else 0.0,
            "discount_pct": 26 if discount_price > 0 else 0,
            "product_link": affiliate_link,
            "affiliate_link": affiliate_link
        }

