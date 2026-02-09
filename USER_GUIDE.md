# 🌱 Ferramenta de análise térmica de plantas — guia do usuário

Ferramenta para extrair temperatura foliar de imagens FLIR, utilizando processamento radiométrico e geração de relatórios estatísticos.

## 1. Instalação e inicialização

O software foi preparado para rodar localmente no seu computador, garantindo performance e privacidade dos dados.

### Para usuários Windows
Esta versão não requer instalação técnica.

1.  **Baixar e extrair**:
    * Baixe o arquivo `software_analise_termica.zip`.
    * **Importante:** Não abra direto do ZIP. Clique com o botão direito no arquivo e escolha **"Extrair tudo"** (Extract all).
2.  **Iniciar**:
    * Abra a pasta extraída.
    * Dê um clique duplo no arquivo **`Iniciar.bat`** (pode aparecer apenas como `Iniciar`).
    * *Nota:* Se o Windows exibir um aviso de proteção, clique em **Mais informações** > **Executar assim mesmo**.
3.  **Primeiro Uso**:
    * Uma janela preta (terminal) se abrirá. **Não a feche.**
    * Na primeira vez, o sistema levará alguns minutos para configurar o ambiente. Nas próximas, será instantâneo.
    * O navegador abrirá automaticamente com o software pronto.

### Para usuários Mac e Linux (via terminal)
Como o script automático (`.bat`) é exclusivo para Windows, siga estes passos:

1.  **Pré-requisitos**:
    * Tenha o **Python 3.10+** instalado.
    * Instale a ferramenta **ExifTool**:
        * **Mac (via Homebrew):** `brew install exiftool`
        * **Linux (Ubuntu/Debian):** `sudo apt-get install libimage-exiftool-perl`
2.  **Execução**:
    * Abra o terminal na pasta descompactada do projeto.
    * Instale as bibliotecas (apenas na 1ª vez):
        ```bash
        pip install -r requirements.txt
        ```
    * Inicie o software:
        ```bash
        streamlit run app_completo.py
        ```

---

## 2. Preparação dos arquivos (importante)

Para o sistema agrupar automaticamente a foto visual com a foto térmica e ler metadados (tratamento, período, etc.), os arquivos devem seguir estritamente o padrão de nomenclatura abaixo, separados por underline (_).

**Padrão de nomenclatura**
```
ID_TempAmbiente_Tratamento_Periodo_Replica_Tipo.jpg
```

- ID: identificador único da planta (ex.: `P01`, `Planta10`).  
- TempAmbiente: temperatura da estufa/câmara no momento da foto (ex.: `21`, `27`, `35`, `45`). essencial para calibração automática.  
- Tratamento: grupo experimental (ex.: `controle`, `heatstress`, `recovery`).  
- Periodo: momento da coleta (ex.: `Dia`, `Noite`, `Manha`).  
- Replica: número da réplica (ex.: `R1`, `R2`).  
- Tipo: deve terminar com `thermal` ou `visual`.

Exemplos válidos:
- `P05_27_Controle_Dia_R1_visual.jpg`  
- `P05_27_Controle_Dia_R1_thermal.jpg`

---

## 3. Passo a passo de uso

### Passo 1 — Upload
1. Abra a aplicação no navegador.  
2. Na barra lateral, faça upload dos arquivos (aceita múltiplos).  
Dica: arraste dezenas de arquivos; o sistema agrupa pares automaticamente.

### Passo 2 — Editor de recorte
- Esquerda: imagem visual (referência).  
- Direita: imagem térmica com retângulo de seleção.  
Ajuste o retângulo para cobrir a planta e clique em **Confirmar**. O sistema salva os dados e passa para a próxima amostra.

### Passo 3 — Dashboard e análise
Abra a aba **Dashboard completo** para visualizar:
- Inspeção de pixels: Passe o mouse sobre o mapa de calor para ver a temperatura exata de cada ponto.

- Gráfico de barras: Comparativo de médias por tratamento.

- Heatmap geral: Matriz de calor (tratamento × período).

- Boxplot: Distribuição estatística para detecção de outliers.

---

## 4. Exportando resultados

Na seção **Relatório e exportação** do dashboard:

- **Baixar tabela (CSV)**: exporta dados brutos (média, máxima, mínima, desvio padrão).  
- **Gerar relatório PDF**: gera PDF com, para cada amostra:
  - foto visual original;  
  - recorte da imagem térmica; 
  - um mapa de calor gerado matematicamente a partir dos sensores. 
  - tabela de estatísticas.

---

## Observações e dicas
- Use nomes consistentes para evitar falhas no pareamento automático.  
- Recomenda‑se imagens com boa resolução para melhores resultados (essa dica será útil para a próxima versão de segmentação automática).
- Se você subir uma imagem thermal sem a correspondente visual (ou vice-versa), o sistema avisará e ela não será processada.