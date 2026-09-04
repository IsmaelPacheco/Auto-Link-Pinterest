"""
theme.py
Responsável por carregar/aplicar os temas visuais (claro/escuro) do Nexus Pro.
Mantém toda a definição de cores fora da lógica de widgets (separação de
responsabilidades), lendo os arquivos .qss em gui/styles/.
"""
from pathlib import Path
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect
from PySide6.QtGui import QColor

PASTA_STYLES = Path(__file__).resolve().parent / "styles"


class ThemeManager:
    """Carrega e aplica os temas claro/escuro em uma janela Qt."""

    ARQUIVOS = {
        "dark": PASTA_STYLES / "theme_dark.qss",
        "light": PASTA_STYLES / "theme_light.qss",
    }

    TEXTO_BOTAO = {
        "dark": "☀   Light",
        "light": "🌙   Dark",
    }

    def __init__(self):
        self._cache = {}

    def _carregar_qss(self, modo: str) -> str:
        if modo not in self._cache:
            caminho = self.ARQUIVOS[modo]
            self._cache[modo] = caminho.read_text(encoding="utf-8")
        return self._cache[modo]

    def texto_botao_tema(self, is_dark_mode: bool) -> str:
        return self.TEXTO_BOTAO["dark" if is_dark_mode else "light"]

    def aplicar(self, janela, is_dark_mode: bool):
        """Aplica o QSS na janela e recria as sombras dos cards (cardPanel)."""
        modo = "dark" if is_dark_mode else "light"
        janela.setStyleSheet(self._carregar_qss(modo))
        self._aplicar_sombras(janela, is_dark_mode)

    def _aplicar_sombras(self, janela, is_dark_mode: bool, intensidade=28, y=10):
        cor_sombra = QColor(0, 0, 0, 110 if is_dark_mode else 35)
        for card in janela.findChildren(QFrame, "cardPanel"):
            sombra = QGraphicsDropShadowEffect(card)
            sombra.setBlurRadius(intensidade)
            sombra.setXOffset(0)
            sombra.setYOffset(y)
            sombra.setColor(cor_sombra)
            card.setGraphicsEffect(sombra)