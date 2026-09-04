"""
pinterest_engine.py
Cliente oficial da API v5 do Pinterest para autenticação,
listagem de boards (pastas) e publicação de Pins com link de afiliado e imagem em Base64.
"""
import base64
import logging
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from PIL import Image
import requests

logger = logging.getLogger("AutoLink.Pinterest")


class PinterestEngine:
    """Cliente para a API Oficial v5 do Pinterest."""

    BASE_URL = "https://api.pinterest.com/v5"

    def __init__(self, access_token: str = ""):
        self.access_token = str(access_token).strip()

    def is_configured(self) -> bool:
        """Verifica se o token de acesso do Pinterest está preenchido."""
        return bool(self.access_token)

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def test_connection(self) -> Dict[str, Any]:
        """Testa o Access Token consultando a conta do usuário (tentando Produção e Sandbox)."""
        if not self.is_configured():
            return {"success": False, "message": "Token de acesso do Pinterest não fornecido."}

        # 1. Tenta Produção
        url = f"{self.BASE_URL}/user_account"
        try:
            resp = requests.get(url, headers=self._get_headers(), timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                username = data.get("username", "Usuário Pinterest")
                return {
                    "success": True,
                    "message": f"Conectado com sucesso como: @{username}",
                    "user_data": data
                }
            
            # Se der erro de consumer type, tenta Sandbox
            sandbox_url = "https://api-sandbox.pinterest.com/v5/user_account"
            sb_resp = requests.get(sandbox_url, headers=self._get_headers(), timeout=15)
            if sb_resp.status_code == 200:
                self.BASE_URL = "https://api-sandbox.pinterest.com/v5"
                data = sb_resp.json()
                username = data.get("username", "Usuário Sandbox")
                return {
                    "success": True,
                    "message": f"Conectado via Sandbox como: @{username}",
                    "user_data": data
                }

            err = resp.json().get("message", resp.text)
            if "consumer type is not supported" in err.lower():
                return {
                    "success": False,
                    "message": (
                        "Status no Pinterest: 'Acesso Trial Pendente'.\n\n"
                        "O Pinterest está realizando a verificação inicial do seu aplicativo "
                        "(onde diz 'Chave secreta do aplicativo: Indisponível no status Acesso trial pendente').\n"
                        "Geralmente essa liberação automática leva de algumas horas até 1 dia útil. "
                        "Assim que o status mudar para 'Aprovado', seu token passará a funcionar imediatamente!"
                    )
                }
            return {"success": False, "message": f"Erro Pinterest ({resp.status_code}): {err}"}
        except Exception as e:
            return {"success": False, "message": f"Falha na conexão com Pinterest: {str(e)}"}

    def get_boards(self) -> List[Dict[str, str]]:
        """Busca todas as pastas (boards) disponíveis na conta do usuário."""
        if not self.is_configured():
            return []

        url = f"{self.BASE_URL}/boards?page_size=100"
        try:
            resp = requests.get(url, headers=self._get_headers(), timeout=15)
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                return [{"id": b["id"], "name": b["name"]} for b in items]
            else:
                logger.error(f"Erro ao listar boards: HTTP {resp.status_code} - {resp.text}")
                return []
        except Exception as e:
            logger.error(f"Exceção ao listar boards: {e}")
            return []

    def create_pin(
        self,
        board_id: str,
        title: str,
        description: str,
        link: str,
        image_input: Union[str, Path, bytes, Image.Image],
        alt_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Publica um Pin oficial no Pinterest.
        image_input pode ser caminho de arquivo, bytes ou objeto PIL.Image.
        """
        if not self.is_configured():
            raise ValueError("Pinterest Access Token não configurado.")
        if not board_id:
            raise ValueError("ID da pasta (board) do Pinterest é obrigatório.")

        # Converte a imagem para Base64 JPEG
        base64_data = self._image_to_base64(image_input)

        payload = {
            "board_id": str(board_id),
            "title": title[:100],  # Limite oficial do Pinterest: 100 caracteres
            "description": description[:800],  # Limite oficial: 800 caracteres
            "link": link,
            "media_source": {
                "source_type": "image_base64",
                "content_type": "image/jpeg",
                "data": base64_data
            }
        }
        if alt_text:
            payload["alt_text"] = alt_text[:500]

        url = f"{self.BASE_URL}/pins"
        resp = requests.post(url, json=payload, headers=self._get_headers(), timeout=30)

        if resp.status_code in (200, 201):
            pin_data = resp.json()
            pin_id = pin_data.get("id")
            # Constrói o link direto no Pinterest
            pin_url = f"https://www.pinterest.com/pin/{pin_id}/" if pin_id else ""
            return {
                "success": True,
                "pin_id": pin_id,
                "pin_url": pin_url,
                "raw_response": pin_data
            }
        else:
            err_msg = resp.text
            try:
                err_msg = resp.json().get("message", resp.text)
            except Exception:
                pass
            raise RuntimeError(f"Falha ao criar Pin (HTTP {resp.status_code}): {err_msg}")

    def _image_to_base64(self, image_input: Union[str, Path, bytes, Image.Image]) -> str:
        """Converte diferentes tipos de entrada de imagem para string Base64 JPEG."""
        if isinstance(image_input, (str, Path)):
            with open(image_input, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        
        elif isinstance(image_input, bytes):
            return base64.b64encode(image_input).decode("utf-8")
        
        elif isinstance(image_input, Image.Image):
            buffer = BytesIO()
            rgb_img = image_input.convert("RGB")
            rgb_img.save(buffer, format="JPEG", quality=92, optimize=True)
            return base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        else:
            raise ValueError(f"Tipo de imagem não suportado: {type(image_input)}")

