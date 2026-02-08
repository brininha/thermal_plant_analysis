import shutil
import subprocess
import sys
import os

# 1. Encontra o ExifTool do sistema (instalado pelo packages.txt)
system_exiftool = shutil.which("exiftool")

if not system_exiftool:
    raise RuntimeError("ERRO CRÍTICO: ExifTool não encontrado no sistema Linux.")

# 2. Hack para enganar a biblioteca ANTES de importá-la
# Dizemos ao Python que se alguém perguntar pelo caminho do ffmpeg/exiftool, é esse aqui:
os.environ["EXIFTOOL_PATH"] = system_exiftool

try:
    # Tenta importar a biblioteca original
    from flirimageextractor import FlirImageExtractor as OriginalFlir
except ImportError:
    # Se não estiver instalada, avisa
    raise ImportError("A biblioteca 'flirimageextractor' não está no requirements.txt!")

# 3. Criamos uma classe segura para a Nuvem
class FlirImageExtractor(OriginalFlir):
    def __init__(self, exiftool_path=None, is_debug=False):
        # AQUI ESTÁ O TRUQUE:
        # Não chamamos o __init__ original imediatamente porque ele tenta criar pastas.
        # Nós configuramos manualmente as variáveis que ele precisa.
        
        self.exiftool_path = system_exiftool
        self.is_debug = is_debug
        self.thermal_image_np = None
        self.metadata = {}
        self.default_csv_path = "/tmp" # Muda para pasta temporária (permitida na nuvem)
        
        # Agora inicializamos apenas a parte de processamento, pulando a instalação
        # Se a biblioteca tiver métodos de setup internos seguros, podemos chamá-los,
        # mas a flirimageextractor é simples, configurar o path acima já resolve.

    def check_for_exiftool(self):
        # Sobrescrevemos o método de verificação para ele sempre dizer "SIM"
        # e nunca tentar baixar nada.
        return True

    def process_image(self, image_path):
        """
        Wrapper seguro para o processamento original
        """
        # Chama o método original da biblioteca, mas agora seguro
        super().process_image(image_path)
        
    def get_thermal_np(self):
        """
        Retorna a matriz térmica usando a fórmula original da biblioteca
        """
        # A biblioteca original salva em self.thermal_image_np
        return super().get_thermal_np()
