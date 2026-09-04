"""
console.py
Redireciona a saída padrão (stdout) para um sinal Qt, permitindo exibir
prints do sistema dentro do terminal de logs da interface.
"""
from PySide6.QtCore import QObject, Signal


class EmissorConsole(QObject):
    texto_escrito = Signal(str)

    def write(self, text):
        if text.strip() or text == "\n":
            self.texto_escrito.emit(str(text))

    def flush(self):
        pass