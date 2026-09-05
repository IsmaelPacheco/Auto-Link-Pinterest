"""
pinterest_browser_engine.py
Motor de automação de publicação no Pinterest via navegador (Playwright).
Permite publicar Pins com foto 1000x1500, título, descrição persuasiva,
link de afiliado da Shopee e seleção de pasta de forma autônoma,
sem depender de aprovação da API do Pinterest!
"""
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("AutoLink.PinterestBrowser")

DEFAULT_PROFILE_DIR = Path("workspace") / "browser_profile"


class PinterestBrowserEngine:
    """Gerencia a sessão e publicação de Pins via navegador automatizado."""

    def __init__(self, profile_dir: Optional[Path] = None):
        self.profile_dir = profile_dir or DEFAULT_PROFILE_DIR
        self.profile_dir.mkdir(parents=True, exist_ok=True)

    def open_login_window(self) -> Dict[str, Any]:
        """
        Abre o navegador visível para o usuário fazer login no Pinterest.
        A sessão fica salva permanentemente no diretório de perfil.
        """
        from playwright.sync_api import sync_playwright

        logger.info("Abrindo navegador para login no Pinterest...")
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir.resolve()),
                headless=False,
                args=["--start-maximized", "--disable-blink-features=AutomationControlled"],
                no_viewport=True
            )
            page = context.new_page()
            page.goto("https://www.pinterest.com/login/")

            logger.info("Aguardando o usuário concluir o login...")
            # Aguarda até que o usuário esteja logado (não esteja mais na página de login)
            max_wait = 180  # 3 minutos
            start_time = time.time()
            logged = False

            while time.time() - start_time < max_wait:
                time.sleep(2)
                cur_url = page.url.lower()
                # Se não estiver em login ou signup e tiver cookie ou avatar
                if "login" not in cur_url and "signup" not in cur_url and "pinterest.com" in cur_url:
                    logged = True
                    break

            context.close()

            if logged:
                return {"success": True, "message": "Login no Pinterest realizado com sucesso! Sessão salva."}
            else:
                return {"success": False, "message": "Tempo limite para login esgotado."}

    def is_logged_in(self) -> bool:
        """Verifica se há uma sessão ativa válida no perfil salvo."""
        from playwright.sync_api import sync_playwright

        try:
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=str(self.profile_dir.resolve()),
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled"]
                )
                page = context.new_page()
                page.goto("https://www.pinterest.com/today/", timeout=15000)
                time.sleep(2)
                cur_url = page.url.lower()
                context.close()
                return "login" not in cur_url and "signup" not in cur_url
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
                page = context.new_page()

                # Acessa o Criador de Pins oficial
                page.goto("https://www.pinterest.com/pin-creation-tool/", timeout=45000)
                time.sleep(4)

                # Verifica se caiu na tela de login
                if "login" in page.url.lower():
                    context.close()
                    return {
                        "success": False,
                        "message": "Sessão expirada ou não logada. Abra as Configurações e faça login no Pinterest primeiro."
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
                # Tenta múltiplos seletores comuns do Pinterest
                title_selectors = [
                    'input[placeholder*="título" i]',
                    'textarea[placeholder*="título" i]',
                    'input[placeholder*="title" i]',
                    'textarea[placeholder*="title" i]',
                    '[data-test-id="pin-draft-title"] input',
                    '[data-test-id="pin-draft-title"] textarea',
                    '#storyboard-selector-title'
                ]
                for sel in title_selectors:
                    elem = page.query_selector(sel)
                    if elem:
                        elem.click()
                        elem.fill(title)
                        break

                # 3. PREENCHIMENTO DA DESCRIÇÃO
                logger.info("Preenchendo descrição e hashtags...")
                desc_selectors = [
                    '[data-test-id="editor-description"] div[contenteditable="true"]',
                    'div[role="textbox"]',
                    'textarea[placeholder*="descrição" i]',
                    'textarea[placeholder*="description" i]',
                    '[data-test-id="pin-draft-description"] textarea',
                    'div[contenteditable="true"]'
                ]
                for sel in desc_selectors:
                    elem = page.query_selector(sel)
                    if elem:
                        elem.click()
                        # Se for contenteditable, usa fill ou type
                        try:
                            elem.fill(description)
                        except Exception:
                            page.keyboard.type(description, delay=10)
                        break

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
                        elem.click()
                        elem.fill(link)
                        break

                time.sleep(2)

                # 5. SELEÇÃO DA PASTA (BOARD)
                if board_name:
                    logger.info(f"Selecionando pasta: {board_name}")
                    # Tenta abrir o dropdown de pastas
                    board_btn_selectors = [
                        '[data-test-id="board-dropdown-select-button"]',
                        'button[aria-label*="pasta" i]',
                        'button[aria-label*="board" i]',
                        'div[data-test-id="board-dropdown"] button'
                    ]
                    for sel in board_btn_selectors:
                        btn = page.query_selector(sel)
                        if btn:
                            btn.click()
                            time.sleep(2)
                            # Digita o nome da pasta no campo de busca se houver
                            search_board_input = page.query_selector('input[placeholder*="Pesquisar" i], input[placeholder*="Search" i]')
                            if search_board_input:
                                search_board_input.fill(board_name)
                                time.sleep(1)
                            # Clica no item com o nome da pasta
                            board_item = page.query_selector(f'text="{board_name}"') or page.query_selector(f'[title*="{board_name}" i]')
                            if board_item:
                                board_item.click()
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
                        btn.click()
                        published = True
                        time.sleep(6)
                        break

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
                        "message": "Não foi possível localizar o botão de publicar ativo."
                    }

        except Exception as e:
            logger.error(f"Erro ao publicar Pin via navegador: {e}")
            return {"success": False, "message": f"Erro no navegador Playwright: {str(e)}"}
