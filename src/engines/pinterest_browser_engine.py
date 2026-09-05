"""
pinterest_browser_engine.py
Motor de automação de publicação no Pinterest via navegador (Playwright).
Blindado com safe_click (force=True e JS evaluation) para eliminar timeouts de pointer events.
Suporta importação direta de cookies (Cookie-Editor) para não exigir 2FA nem login manual.
"""
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger("AutoLink.PinterestBrowser")

DEFAULT_PROFILE_DIR = Path("workspace") / "browser_profile"
DEFAULT_COOKIES_FILE = Path("workspace") / "cookies.json"


def clean_cookies_for_playwright(raw_cookies: list) -> List[Dict[str, Any]]:
    """Limpa e formata os cookies exportados de extensões (como Cookie-Editor) para o Playwright."""
    cleaned = []
    for c in raw_cookies:
        if not isinstance(c, dict):
            continue
        name = c.get("name")
        value = c.get("value")
        if not name or value is None:
            continue

        cookie_item: Dict[str, Any] = {
            "name": str(name),
            "value": str(value)
        }

        domain = c.get("domain", "")
        if domain:
            cookie_item["domain"] = domain

        path = c.get("path", "/")
        cookie_item["path"] = path

        if not domain and "url" not in c:
            cookie_item["url"] = "https://www.pinterest.com"

        if "httpOnly" in c:
            cookie_item["httpOnly"] = bool(c["httpOnly"])
        if "secure" in c:
            cookie_item["secure"] = bool(c["secure"])

        s_site = str(c.get("sameSite", "")).lower()
        if s_site in ("strict", "lax"):
            cookie_item["sameSite"] = s_site.capitalize()
        elif s_site in ("none", "no_restriction"):
            cookie_item["sameSite"] = "None"
            cookie_item["secure"] = True

        exp = c.get("expires") or c.get("expirationDate")
        if exp and isinstance(exp, (int, float)) and exp > 0:
            cookie_item["expires"] = float(exp)

        cleaned.append(cookie_item)
    return cleaned


def safe_click(page, elem, timeout: int = 3000):
    """Clica no elemento ignorando interceptações de ponteiro usando force=True ou JS dispatch."""
    try:
        elem.click(timeout=timeout, force=True)
    except Exception:
        try:
            page.evaluate("(el) => el.click()", elem)
        except Exception as e:
            logger.debug(f"Falha em safe_click: {e}")


def safe_fill(page, elem, text: str):
    """Preenche o elemento de forma segura contra interceptações de DOM."""
    try:
        elem.click(timeout=2000, force=True)
        elem.fill(text, timeout=3000)
    except Exception:
        try:
            page.evaluate("""(el, val) => {
                el.focus();
                if ('value' in el) {
                    el.value = val;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                } else {
                    el.innerText = val;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                }
            }""", elem, text)
        except Exception as e:
            logger.debug(f"Falha em safe_fill: {e}")


class PinterestBrowserEngine:
    """Gerencia a sessão e publicação de Pins via navegador automatizado."""

    def __init__(self, profile_dir: Optional[Path] = None, cookies_file: Optional[Path] = None):
        self.profile_dir = profile_dir or DEFAULT_PROFILE_DIR
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.cookies_file = cookies_file or DEFAULT_COOKIES_FILE

    def import_cookies(self, raw_json_text: str) -> Dict[str, Any]:
        """
        Recebe o texto JSON copiado do Cookie-Editor, valida, salva e testa a sessão.
        """
        try:
            parsed = json.loads(raw_json_text)
            if isinstance(parsed, dict):
                parsed = [parsed]
            if not isinstance(parsed, list):
                return {"success": False, "message": "O conteúdo não é uma lista de cookies válida."}

            cleaned = clean_cookies_for_playwright(parsed)
            if not cleaned:
                return {"success": False, "message": "Nenhum cookie válido encontrado no JSON colado."}

            self.cookies_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cookies_file, "w", encoding="utf-8") as f:
                json.dump(cleaned, f, indent=2)

            logger.info(f"{len(cleaned)} cookies salvos com sucesso em {self.cookies_file}")

            logged = self.is_logged_in()
            if logged:
                return {
                    "success": True,
                    "message": f"🎉 Sucesso! {len(cleaned)} cookies importados e sessão do Pinterest confirmada como ATIVA!"
                }
            else:
                return {
                    "success": True,
                    "message": f"{len(cleaned)} cookies salvos com sucesso! Eles serão aplicados nas postagens."
                }

        except json.JSONDecodeError as e:
            return {"success": False, "message": f"Erro de formatação JSON: {e}"}
        except Exception as e:
            return {"success": False, "message": f"Falha ao importar cookies: {e}"}

    def _inject_saved_cookies(self, context) -> bool:
        """Injeta os cookies salvos no contexto do navegador."""
        if self.cookies_file.exists():
            try:
                with open(self.cookies_file, "r", encoding="utf-8") as f:
                    cookies = json.load(f)
                if cookies and isinstance(cookies, list):
                    context.add_cookies(cookies)
                    logger.info(f"{len(cookies)} cookies injetados no navegador com sucesso.")
                    return True
            except Exception as e:
                logger.warning(f"Erro ao injetar cookies salvos: {e}")
        return False

    def open_login_window(self) -> Dict[str, Any]:
        """Abre o navegador visível para o usuário fazer login no Pinterest."""
        from playwright.sync_api import sync_playwright

        logger.info("Abrindo navegador para login no Pinterest...")
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir.resolve()),
                headless=False,
                args=["--start-maximized", "--disable-blink-features=AutomationControlled"],
                no_viewport=True
            )
            self._inject_saved_cookies(context)
            page = context.new_page()
            page.goto("https://www.pinterest.com/")

            logger.info("Aguardando o usuário concluir o login...")
            max_wait = 180
            start_time = time.time()
            logged = False

            while time.time() - start_time < max_wait:
                time.sleep(2)
                cur_url = page.url.lower()
                if "login" not in cur_url and "signup" not in cur_url and "pinterest.com" in cur_url:
                    if page.query_selector('[data-test-id="header-profile"]') or page.query_selector('a[href*="/"] img'):
                        logged = True
                        break

            try:
                current_cookies = context.cookies()
                with open(self.cookies_file, "w", encoding="utf-8") as f:
                    json.dump(current_cookies, f, indent=2)
            except Exception:
                pass

            context.close()

            if logged:
                return {"success": True, "message": "Login no Pinterest realizado com sucesso! Sessão salva."}
            else:
                return {"success": False, "message": "Tempo limite para login esgotado."}

    def is_logged_in(self) -> bool:
        """Verifica se há uma sessão ativa válida."""
        from playwright.sync_api import sync_playwright

        try:
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=str(self.profile_dir.resolve()),
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled"]
                )
                self._inject_saved_cookies(context)
                page = context.new_page()
                page.goto("https://www.pinterest.com/", timeout=15000)
                time.sleep(3)
                cur_url = page.url.lower()
                is_logged = "login" not in cur_url and "signup" not in cur_url
                context.close()
                return is_logged
        except Exception as e:
            logger.warning(f"Erro ao verificar sessão do Pinterest: {e}")
            return False

    def publish_pin(
        self,
        image_path: str,
        title: str,
        description: str,
        link: str,
        board_name: str = "",
        headless: bool = False
    ) -> Dict[str, Any]:
        """
        Publica um Pin completo usando o Criador Oficial de Pins do Pinterest no navegador.
        """
        from playwright.sync_api import sync_playwright

        img_file = Path(image_path)
        if not img_file.exists():
            return {"success": False, "message": f"Arquivo de imagem não encontrado: {image_path}"}

        logger.info(f"Iniciando publicação via navegador: '{title}'")

        try:
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=str(self.profile_dir.resolve()),
                    headless=headless,
                    args=[
                        "--start-maximized",
                        "--disable-blink-features=AutomationControlled"
                    ],
                    no_viewport=True if not headless else False
                )
                self._inject_saved_cookies(context)
                page = context.new_page()

                # Acessa o Criador de Pins oficial
                page.goto("https://www.pinterest.com/pin-creation-tool/", timeout=45000)
                time.sleep(4)

                # Fecha eventuais modais introdutórios do Pinterest
                intro_selectors = [
                    'button[aria-label="Fechar"]',
                    'button[aria-label="Close"]',
                    'button:has-text("Entendi")',
                    'button:has-text("Got it")',
                    'button:has-text("Aceitar todos")',
                    'button:has-text("Accept all")'
                ]
                for intro in intro_selectors:
                    try:
                        modal_btn = page.query_selector(intro)
                        if modal_btn:
                            safe_click(page, modal_btn, timeout=1000)
                            time.sleep(1)
                    except Exception:
                        pass

                # Verifica se caiu na tela de login
                if "login" in page.url.lower() or "signup" in page.url.lower():
                    context.close()
                    return {
                        "success": False,
                        "message": "Sessão expirada ou não conectada. Use o botão ' Conectar Sessão' nas Configurações para colar seus cookies."
                    }

                # 1. UPLOAD DA IMAGEM
                logger.info("Enviando imagem 1000x1500...")
                file_input = page.wait_for_selector('input[type="file"]', timeout=20000)
                if file_input:
                    file_input.set_input_files(str(img_file.resolve()))
                    time.sleep(3)
                else:
                    context.close()
                    return {"success": False, "message": "Campo de upload de imagem não encontrado na página."}

                # 2. PREENCHIMENTO DO TÍTULO
                logger.info("Preenchendo título do Pin...")
                title_selectors = [
                    'input[placeholder*="título" i]',
                    'textarea[placeholder*="título" i]',
                    'input[placeholder*="title" i]',
                    'textarea[placeholder*="title" i]',
                    '[data-test-id="pin-draft-title"] input',
                    '[data-test-id="pin-draft-title"] textarea',
                    '#storyboard-selector-title'
                ]
                title_elem = None
                for sel in title_selectors:
                    elem = page.query_selector(sel)
                    if elem:
                        title_elem = elem
                        safe_fill(page, elem, title)
                        break

                # 3. PREENCHIMENTO DA DESCRIÇÃO (REACT / DRAFT.JS RICH TEXT)
                logger.info("Preenchendo descrição e hashtags...")
                desc_selectors = [
                    '[data-test-id="editor-description"] div[contenteditable="true"]',
                    '[data-test-id="pin-draft-description"] div[contenteditable="true"]',
                    '[data-test-id="pin-draft-description"] textarea',
                    '[data-test-id="pin-draft-description"] [role="textbox"]',
                    'div[contenteditable="true"][aria-label*="descri" i]',
                    'div[contenteditable="true"][placeholder*="descri" i]',
                    'div[contenteditable="true"][data-placeholder*="descri" i]',
                    'div[role="textbox"][aria-label*="descri" i]',
                    'textarea[placeholder*="descri" i]',
                    'textarea[placeholder*="description" i]',
                    'textarea[placeholder*="conte" i]',
                    'textarea[placeholder*="tell" i]',
                    '[data-test-id="editor-description"]',
                    '[data-test-id="pin-draft-description"]'
                ]
                desc_filled = False
                for sel in desc_selectors:
                    elem = page.query_selector(sel)
                    if elem:
                        try:
                            safe_click(page, elem)
                            time.sleep(0.3)
                            elem.focus()
                            time.sleep(0.3)
                            page.keyboard.press("Control+A")
                            page.keyboard.press("Backspace")
                            time.sleep(0.2)
                            page.keyboard.insert_text(description)
                            time.sleep(0.5)
                            desc_filled = True
                            logger.info(f"Descrição preenchida com sucesso via seletor: {sel}")
                            break
                        except Exception as e:
                            logger.debug(f"Falha ao preencher descrição com {sel}: {e}")

                # Fallback: se os seletores não acharam o elemento, navega pelo Tab a partir do título
                if not desc_filled and title_elem:
                    logger.info("Navegando para campo de descrição via tecla Tab...")
                    try:
                        title_elem.focus()
                        page.keyboard.press("Tab")
                        time.sleep(0.5)
                        page.keyboard.insert_text(description)
                        time.sleep(0.5)
                        logger.info("Descrição inserida via Tab com sucesso!")
                    except Exception as e:
                        logger.warning(f"Falha no fallback Tab da descrição: {e}")

                # 4. PREENCHIMENTO DO LINK DE AFILIADO
                logger.info(f"Preenchendo link de afiliado: {link}")
                link_selectors = [
                    'input[placeholder*="link" i]',
                    'input[placeholder*="destino" i]',
                    'input[placeholder*="destination" i]',
                    '[data-test-id="pin-draft-link"] input',
                    '#storyboard-selector-link'
                ]
                for sel in link_selectors:
                    elem = page.query_selector(sel)
                    if elem:
                        safe_fill(page, elem, link)
                        break

                time.sleep(2)

                # 5. SELEÇÃO DA PASTA (BOARD)
                if board_name:
                    logger.info(f"Selecionando pasta: {board_name}")
                    board_btn_selectors = [
                        '[data-test-id="board-dropdown-select-button"]',
                        'button[aria-label*="pasta" i]',
                        'button[aria-label*="board" i]',
                        'div[data-test-id="board-dropdown"] button'
                    ]
                    for sel in board_btn_selectors:
                        btn = page.query_selector(sel)
                        if btn:
                            safe_click(page, btn)
                            time.sleep(2)
                            search_board_input = page.query_selector('input[placeholder*="Pesquisar" i], input[placeholder*="Search" i]')
                            if search_board_input:
                                safe_fill(page, search_board_input, board_name)
                                time.sleep(1)
                            board_item = page.query_selector(f'text="{board_name}"') or page.query_selector(f'[title*="{board_name}" i]')
                            if board_item:
                                safe_click(page, board_item)
                                time.sleep(1)
                            break

                # 6. CLIQUE NO BOTÃO PUBLICAR
                logger.info("Clicando no botão Publicar...")
                publish_btn_selectors = [
                    '[data-test-id="board-dropdown-save-button"]',
                    'button:has-text("Publicar")',
                    'button:has-text("Salvar")',
                    'button:has-text("Publish")',
                    'button:has-text("Save")'
                ]
                published = False
                for sel in publish_btn_selectors:
                    btn = page.query_selector(sel)
                    if btn and btn.is_enabled():
                        safe_click(page, btn)
                        published = True
                        time.sleep(6)
                        break

                # Salva cookies atualizados para manter a sessão sempre viva
                try:
                    current_cookies = context.cookies()
                    with open(self.cookies_file, "w", encoding="utf-8") as f:
                        json.dump(current_cookies, f, indent=2)
                except Exception:
                    pass

                context.close()

                if published:
                    logger.info("Pin publicado com sucesso via navegador!")
                    return {
                        "success": True,
                        "message": "Pin publicado com sucesso via navegador!",
                        "pin_url": "https://www.pinterest.com/"
                    }
                else:
                    return {
                        "success": False,
                        "message": "Não foi possível localizar o botão de publicar ativo na página."
                    }

        except Exception as e:
            logger.error(f"Erro ao publicar Pin via navegador: {e}")
            return {"success": False, "message": f"Erro no navegador Playwright: {str(e)}"}
