"""
abrir_navegador_recuperacao.py
Abre o Chromium com a sua sessão ativa e logada do Pinterest para você
acessar as configurações e alterar seu e-mail e segurança com calma.
"""
import sys
import json
import time
from pathlib import Path

# Força codificação UTF-8
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright

profile_dir = Path("workspace") / "browser_profile"
cookies_file = Path("workspace") / "cookies.json"

print("=" * 65)
print("🔓 ABRINDO CHROMIUM COM SUA SESSÃO ATIVA DO PINTEREST...")
print("=" * 65)

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=str(profile_dir.resolve()),
        headless=False,
        args=[
            "--start-maximized",
            "--disable-blink-features=AutomationControlled"
        ],
        no_viewport=True
    )
    
    if cookies_file.exists():
        try:
            with open(cookies_file, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            if cookies:
                context.add_cookies(cookies)
                print(f"✓ {len(cookies)} cookies de sessão injetados com sucesso.")
        except Exception as e:
            print(f"Aviso ao carregar cookies: {e}")

    page = context.new_page()
    page.goto("https://www.pinterest.com/settings/account-settings/")
    
    print("\n✅ Janela do Pinterest aberta na tela!")
    print("👉 Você pode alterar seu e-mail, senha, vincular Google ou adicionar telefone.")
    print("👉 Quando terminar suas alterações, basta fechar a janela do navegador.")
    print("Aguardando você concluir...\n")
    
    try:
        while True:
            time.sleep(2)
            # Salva cookies periodicamente para persistir a nova sessão
            try:
                cur_cookies = context.cookies()
                with open(cookies_file, "w", encoding="utf-8") as f:
                    json.dump(cur_cookies, f, indent=2)
            except Exception:
                pass
            
            # Se todas as abas foram fechadas pelo usuário, encerra
            if len(context.pages) == 0:
                break
    except KeyboardInterrupt:
        pass
    finally:
        try:
            cur_cookies = context.cookies()
            with open(cookies_file, "w", encoding="utf-8") as f:
                json.dump(cur_cookies, f, indent=2)
            context.close()
        except Exception:
            pass
        print("\n🎉 Sessão atualizada e salva com sucesso!")
