"""
main.py
Ponto de entrada do AutoLink Pinterest.
Inicia a aplicação gráfica PySide6.
"""
import sys
import warnings
from pathlib import Path

# Suprime avisos informativos internos de SDK (como AFC)
warnings.filterwarnings("ignore", message=".*automatic function calling.*")
warnings.filterwarnings("ignore", category=UserWarning)

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from src.views.main_window import MainWindow


def main():
    # ID explícito para o Windows exibir o ícone correto na Barra de Tarefas
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("autolink.pinterest.shopee.1.0")
        except Exception:
            pass

    app = QApplication(sys.argv)

    # Ícone da Aplicação
    caminho_icone = Path(__file__).resolve().parent / "assets" / "icon.png"
    if not caminho_icone.exists():
        caminho_icone = Path(__file__).resolve().parent / "assets" / "icon.ico"
    if caminho_icone.exists():
        app.setWindowIcon(QIcon(str(caminho_icone)))

    janela = MainWindow()
    if caminho_icone.exists():
        janela.setWindowIcon(QIcon(str(caminho_icone)))
    janela.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()