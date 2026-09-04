"""
config_manager.py
Gerencia a persistência de configurações, credenciais e parâmetros operacionais
do AutoLink Pinterest em arquivo JSON local.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("AutoLink.Config")

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    # Shopee Affiliate Open API
    "shopee_app_id": "",
    "shopee_secret": "",
    "shopee_country": "BR",
    
    # Pinterest API v5
    "pinterest_access_token": "",
    "pinterest_board_id": "",
    "pinterest_board_name": "",
    
    # IA e Copywriting (Opcional - Google Gemini)
    "gemini_api_key": "",
    "use_gemini": True,
    
    # Automação & Anti-Spam
    "auto_interval_minutes": 45,
    "auto_jitter_minutes": 15,
    "max_pins_per_day": 12,
    "search_keywords": "utilidades domesticas, organizador, achadinhos, cozinha, decoracao",
    "image_template": "classic_deal",
    
    # Interface
    "dark_mode": True
}


class ConfigManager:
    """Gerencia leitura e escrita das configurações do sistema."""

    def __init__(self, file_path: Path = CONFIG_PATH):
        self.file_path = file_path
        self._config: Dict[str, Any] = dict(DEFAULT_CONFIG)
        self.load()

    def load(self) -> Dict[str, Any]:
        """Carrega configurações do arquivo JSON. Cria com padrões se não existir."""
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._config.update(data)
            except Exception as e:
                logger.error(f"Erro ao carregar configurações: {e}. Usando padrões.")
        else:
            self.save()
        return self._config

    def save(self) -> bool:
        """Salva as configurações atuais no arquivo JSON."""
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar configurações: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._config[key] = value

    def update(self, new_data: Dict[str, Any]) -> None:
        self._config.update(new_data)
        self.save()

    def get_all(self) -> Dict[str, Any]:
        return dict(self._config)

