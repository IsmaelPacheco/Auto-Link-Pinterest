"""
account_manager.py
Gerenciador de Múltiplas Contas do Pinterest para o AutoLink.
Permite cadastrar, editar, ativar/desativar e isolar cookies e perfis de navegação
para cada conta individualmente, suportando escala de alto volume (ex: 45+ pins/dia).
"""
import os
import json
import shutil
import logging
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional

logger = logging.getLogger("AutoLink.AccountManager")

WORKSPACE_DIR = Path("workspace")
ACCOUNTS_JSON = WORKSPACE_DIR / "accounts.json"
ACCOUNTS_DIR = WORKSPACE_DIR / "accounts"


@dataclass
class PinterestAccount:
    id: str
    name: str
    niche: str = "Geral"
    board_name: str = ""
    search_keywords: str = "achadinhos, utilidades, decoracao"
    max_pins_per_day: int = 15
    is_active: bool = True
    created_at: str = ""

    def get_dir(self) -> Path:
        p = ACCOUNTS_DIR / self.id
        p.mkdir(parents=True, exist_ok=True)
        return p

    def get_cookies_file(self) -> Path:
        return self.get_dir() / "cookies.json"

    def get_profile_dir(self) -> Path:
        p = self.get_dir() / "browser_profile"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def has_cookies(self) -> bool:
        cf = self.get_cookies_file()
        if not cf.exists():
            return False
        try:
            with open(cf, "r", encoding="utf-8") as f:
                data = json.load(f)
            return bool(data and isinstance(data, list) and len(data) > 0)
        except Exception:
            return False


class AccountManager:
    """Gerencia o ciclo de vida das contas do Pinterest."""

    def __init__(self, workspace_dir: Path = WORKSPACE_DIR):
        self.workspace_dir = workspace_dir
        self.accounts_json = self.workspace_dir / "accounts.json"
        self.accounts_dir = self.workspace_dir / "accounts"
        self.accounts_dir.mkdir(parents=True, exist_ok=True)
        self._accounts: Dict[str, PinterestAccount] = {}
        self._load()

    def _load(self):
        """Carrega contas do accounts.json ou migra a conta única existente."""
        if self.accounts_json.exists():
            try:
                with open(self.accounts_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        acc = PinterestAccount(**item)
                        self._accounts[acc.id] = acc
            except Exception as e:
                logger.error(f"Erro ao carregar accounts.json: {e}")

        # Se não há nenhuma conta cadastrada, migra a conta existente
        if not self._accounts:
            self._migrar_conta_padrao()

    def _migrar_conta_padrao(self):
        """Migra a conta legada única para 'default' sem perder cookies ou login."""
        default_acc = PinterestAccount(
            id="default",
            name="Conta Principal (Padrão)",
            niche="Achadinhos Geral",
            board_name="",
            search_keywords="utilidades domesticas, organizador, achadinhos, cozinha, decoracao",
            max_pins_per_day=15,
            is_active=True
        )
        self._accounts["default"] = default_acc

        # Se houver cookies legados em workspace/cookies.json, copia para a pasta da conta
        legacy_cookies = self.workspace_dir / "cookies.json"
        target_cookies = default_acc.get_cookies_file()
        if legacy_cookies.exists() and not target_cookies.exists():
            try:
                shutil.copy2(legacy_cookies, target_cookies)
                logger.info("Cookies legados migrados com sucesso para a Conta Principal.")
            except Exception as e:
                logger.warning(f"Falha ao migrar cookies legados: {e}")

        # Se houver perfil legado em workspace/browser_profile, copia
        legacy_profile = self.workspace_dir / "browser_profile"
        target_profile = default_acc.get_profile_dir()
        if legacy_profile.exists() and legacy_profile.is_dir() and not any(target_profile.iterdir()):
            try:
                for item in legacy_profile.iterdir():
                    dst = target_profile / item.name
                    if item.is_dir():
                        shutil.copytree(item, dst, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, dst)
                logger.info("Perfil do navegador legado migrado para a Conta Principal.")
            except Exception as e:
                logger.warning(f"Falha ao migrar perfil do navegador: {e}")

        self._save()

    def _save(self):
        """Persiste todas as contas em accounts.json."""
        try:
            data = [asdict(acc) for acc in self._accounts.values()]
            with open(self.accounts_json, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erro ao salvar accounts.json: {e}")

    def get_all_accounts(self) -> List[PinterestAccount]:
        return list(self._accounts.values())

    def get_active_accounts(self) -> List[PinterestAccount]:
        return [acc for acc in self._accounts.values() if acc.is_active]

    def get_account(self, account_id: str) -> Optional[PinterestAccount]:
        return self._accounts.get(account_id)

    def add_account(
        self,
        name: str,
        niche: str = "Geral",
        board_name: str = "",
        search_keywords: str = "",
        max_pins_per_day: int = 15,
        is_active: bool = True
    ) -> PinterestAccount:
        """Cria uma nova conta isolada com ID único."""
        # Gera ID alfanumérico limpo
        base_id = "".join(c for c in name.lower().replace(" ", "_") if c.isalnum() or c == "_")
        acc_id = f"acc_{base_id}" if base_id else "acc_nova"
        
        counter = 1
        final_id = acc_id
        while final_id in self._accounts:
            final_id = f"{acc_id}_{counter}"
            counter += 1

        acc = PinterestAccount(
            id=final_id,
            name=name.strip(),
            niche=niche.strip(),
            board_name=board_name.strip(),
            search_keywords=search_keywords.strip() or "achadinhos, shopee",
            max_pins_per_day=max(1, int(max_pins_per_day)),
            is_active=is_active
        )
        # Garante que os diretórios existem
        acc.get_dir()
        acc.get_profile_dir()

        self._accounts[final_id] = acc
        self._save()
        logger.info(f"Nova conta cadastrada: '{name}' (ID: {final_id})")
        return acc

    def update_account(self, account_id: str, **kwargs) -> Optional[PinterestAccount]:
        acc = self.get_account(account_id)
        if not acc:
            return None
        for key, val in kwargs.items():
            if hasattr(acc, key):
                setattr(acc, key, val)
        self._save()
        return acc

    def delete_account(self, account_id: str) -> bool:
        if account_id not in self._accounts:
            return False
        # Remove a conta da lista
        acc = self._accounts.pop(account_id)
        self._save()
        # Opcionalmente remove a pasta (ou preserva por segurança)
        try:
            acc_dir = acc.get_dir()
            if acc_dir.exists():
                shutil.rmtree(acc_dir, ignore_errors=True)
        except Exception:
            pass
        logger.info(f"Conta '{account_id}' removida.")
        return True

    def get_browser_engine_for_account(self, account_id: str):
        """Retorna uma instância de PinterestBrowserEngine isolada para a conta informada."""
        from src.engines.pinterest_browser_engine import PinterestBrowserEngine
        acc = self.get_account(account_id)
        if not acc:
            acc = self.get_account("default") or list(self._accounts.values())[0]
        return PinterestBrowserEngine(
            profile_dir=acc.get_profile_dir(),
            cookies_file=acc.get_cookies_file()
        )
