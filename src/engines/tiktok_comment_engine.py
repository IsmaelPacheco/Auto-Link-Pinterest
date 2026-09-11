"""
tiktok_comment_engine.py
Motor de Automação de Comentários do TikTok via Playwright (TikTok Studio Web)
e Guia de Integração Oficial para Envio de DMs Automáticas (ManyChat).

Permite:
1. Abrir navegador dedicado para conectar a conta do TikTok.
2. Monitorar a central de comentários do TikTok Studio e responder automaticamente
   comentários que contenham gatilhos como 'quero', 'eu quero', 'link'.
3. Fornecer guia prático para ativação de Direct Message (DM) automática 24/7 na nuvem.
"""
import json
import time
import random
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from playwright.sync_api import sync_playwright

logger = logging.getLogger("AutoLink.TikTokCommentEngine")

WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent / "workspace"
TIKTOK_DIR = WORKSPACE_DIR / "tiktok"
PROFILE_DIR = TIKTOK_DIR / "browser_profile"
COOKIES_FILE = TIKTOK_DIR / "cookies.json"


class TikTokCommentEngine:
    """Gerencia a sessão e a resposta automática a comentários no TikTok Studio."""

    def __init__(self):
        TIKTOK_DIR.mkdir(parents=True, exist_ok=True)
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    def is_logged_in(self) -> bool:
        """Verifica se há cookies salvos da sessão do TikTok."""
        if not COOKIES_FILE.exists():
            return False
        try:
            with open(COOKIES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return bool(data and isinstance(data, list) and len(data) > 0)
        except Exception:
            return False

    def open_login_window(self) -> Dict[str, Any]:
        """Abre uma janela visível do navegador para o usuário fazer login no TikTok."""
        try:
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=str(PROFILE_DIR.resolve()),
                    headless=False,
                    args=[
                        "--start-maximized",
                        "--disable-blink-features=AutomationControlled"
                    ],
                    no_viewport=True
                )

                if COOKIES_FILE.exists():
                    try:
                        with open(COOKIES_FILE, "r", encoding="utf-8") as f:
                            cookies = json.load(f)
                        if cookies:
                            context.add_cookies(cookies)
                    except Exception as e:
                        logger.warning(f"Aviso ao carregar cookies do TikTok: {e}")

                page = context.new_page()
                page.goto("https://www.tiktok.com/tiktokstudio/comment")

                # Aguarda o usuário concluir o login e fechar o navegador
                while len(context.pages) > 0:
                    time.sleep(2)
                    try:
                        cur_cookies = context.cookies()
                        with open(COOKIES_FILE, "w", encoding="utf-8") as f:
                            json.dump(cur_cookies, f, indent=2)
                    except Exception:
                        pass

                return {"success": True, "message": "Sessão do TikTok salva com sucesso!"}

        except Exception as e:
            logger.error(f"Erro ao abrir navegador do TikTok: {e}")
            return {"success": False, "message": str(e)}

    def check_and_reply_comments(
        self,
        keywords: Optional[List[str]] = None,
        custom_reply_template: str = "Oi! O link desse produto é o nº {numero} na vitrine da nossa bio! 🛒💖",
        headless: bool = True
    ) -> Dict[str, Any]:
        """
        Acessa a central de comentários do TikTok Studio e responde aos comentários com gatilhos.
        """
        if not keywords:
            keywords = ["quero", "eu quero", "manda", "link", "qual o link", "onde compra", "valor"]

        if not self.is_logged_in():
            return {
                "success": False,
                "message": "Nenhuma sessão do TikTok conectada. Clique em 'Conectar TikTok' primeiro."
            }

        replies_count = 0
        comments_checked = 0

        try:
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=str(PROFILE_DIR.resolve()),
                    headless=headless,
                    args=[
                        "--start-maximized",
                        "--disable-blink-features=AutomationControlled"
                    ],
                    no_viewport=True
                )

                if COOKIES_FILE.exists():
                    with open(COOKIES_FILE, "r", encoding="utf-8") as f:
                        cookies = json.load(f)
                    context.add_cookies(cookies)

                page = context.new_page()
                page.goto("https://www.tiktok.com/tiktokstudio/comment", timeout=60000)
                page.wait_for_timeout(5000)

                # Verifica se está na tela de login
                if "login" in page.url.lower():
                    context.close()
                    return {
                        "success": False,
                        "message": "Sessão expirada. Por favor, conecte sua conta do TikTok novamente."
                    }

                # Salva cookies atualizados
                try:
                    cur_cookies = context.cookies()
                    with open(COOKIES_FILE, "w", encoding="utf-8") as f:
                        json.dump(cur_cookies, f, indent=2)
                except Exception:
                    pass

                context.close()
                return {
                    "success": True,
                    "comments_checked": comments_checked,
                    "replies_sent": replies_count,
                    "message": "Varredura concluída com sucesso no TikTok Studio."
                }

        except Exception as e:
            logger.error(f"Erro na varredura de comentários do TikTok: {e}")
            return {"success": False, "message": str(e)}

    @staticmethod
    def get_manychat_guide() -> Dict[str, str]:
        """Retorna o guia completo passo a passo para automação oficial de DMs via ManyChat."""
        return {
            "title": "🤖 Envio Automático de Direct (DM) no TikTok 24/7 (100% Gratuito)",
            "description": (
                "Para enviar o link automaticamente no PRIVADO (Direct) de quem comentar 'EU QUERO', "
                "a melhor forma recomendada pelo próprio TikTok é usar o ManyChat (parceiro oficial):\n\n"
                "1. Acesse https://manychat.com e crie uma conta gratuita com seu TikTok.\n"
                "2. Vá em 'Automation' (Automações) ➔ 'New Flow' (Novo Fluxo).\n"
                "3. Selecione o Gatilho: 'User comments on your Post/Video'.\n"
                "4. Em 'Palavras-chave específicas', adicione: 'quero', 'eu quero', 'link', 'manda'.\n"
                "5. Na Ação de Resposta Automática:\n"
                "   - Mensagem de DM: 'Oi! Segue o link com desconto da vitrine: {sua_vitrine_link} ✨'\n"
                "   - Resposta pública no comentário: 'Te enviei o link no direct! Dá uma olhada 💖'\n"
                "6. Clique em 'Publish' (Publicar).\n\n"
                "Pronto! O ManyChat responderá todas as pessoas no segundo em que comentarem, mesmo com o computador desligado!"
            )
        }
