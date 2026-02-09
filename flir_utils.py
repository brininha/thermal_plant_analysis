import shutil
import subprocess
import sys
import os
import numpy as np

# Tenta importar a biblioteca original
try:
    from flirimageextractor import FlirImageExtractor as OriginalFlir
except ImportError:
    raise RuntimeError("A biblioteca 'flirimageextractor' não está instalada! Verifique o requirements.txt.")

class FlirImageExtractor(OriginalFlir):
    def __init__(self, exiftool_path=None, is_debug=False):
        """
        Inicialização 'Cloud-Safe': Copia as variáveis da biblioteca original,
        mas NÃO executa o código de criação de pastas proibidas.
        """
        # 1. Configura o ExifTool (essencial)
        self.exiftool_path = exiftool_path if exiftool_path else shutil.which("exiftool")
        if not self.exiftool_path:
            raise RuntimeError("ExifTool não encontrado! Verifique se 'packages.txt' contém 'exiftool'.")

        # 2. Configura variáveis internas (Copiado da original, mas sem instalar nada)
        self.is_debug = is_debug
        self.thermal_image_np = None
        self.rgb_image_np = None
        self.metadata = {}
        
        # Variáveis de configuração padrão da biblioteca
        self.use_thermal_pixel_values = True 
        self.fix_thermal_pixel_values = True
        
        # IMPORTANTE: Não chamamos super().__init__()!
        # É lá que mora o erro de permissão [Errno 13].
        # Como já configuramos as variáveis acima, não precisamos dele.

    def check_for_exiftool(self):
        # Sobrescreve a checagem para evitar downloads
        return True

    def process_image(self, image_path):
        """
        Executa o processamento usando a lógica da biblioteca original.
        """
        # O método process_image da original usa self.exiftool_path e subprocess.
        # Como configuramos isso manualmente no __init__ acima, vai funcionar!
        super().process_image(image_path)

    def get_thermal_np(self):
        """
        Retorna a matriz térmica usando a fórmula matemática da biblioteca original.
        """
        return super().get_thermal_np()