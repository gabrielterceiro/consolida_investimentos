# Consolidador de Investimentos em Ações e FIIs

## Descrição

Este script em Python automatiza o processo de consolidação de transações de investimentos (ações e Fundos de Investimento Imobiliário - FIIs) a partir de múltiplos extratos de corretoras em formato Excel. Ele calcula o preço médio de aquisição, a posição atual da carteira, o lucro/prejuízo, o histórico de vendas e os rendimentos (dividendos, JCP), gerando um arquivo Excel consolidado com todas essas informações. O script também lida com desdobramentos/grupamentos de ações e renomeações de tickers.

Este projeto é projetado para ser executado em um ambiente Docker, garantindo consistência e facilidade de configuração.

## Funcionalidades

- **Consolidação de Múltiplos Extratos:** Agrega dados de transações de diversos arquivos Excel (`.xlsx`).
- **Cálculo de Posição e Preço Médio:** Calcula a quantidade atual de cada ativo e seu respectivo preço médio de aquisição.
- **Ajuste por Desdobramentos/Grupamentos:** Aplica fatores de desdobramento ou grupamento às transações.
- **Tratamento de Renomeação de Tickers:** Atualiza tickers antigos para novos.
- **Cotações Atuais:** Busca os preços atuais dos ativos usando `yfinance`.
- **Consolidação de Rendimentos:** Agrega dividendos, JCP, etc., por ativo e ano.
- **Registro de Vendas:** Cria um log detalhado de operações de venda.
- **Saída em Excel:** Gera um arquivo `.xlsx` com abas para Portfólio, Posição (custo), Vendas e Rendimentos.
- **Configurável:** Via arquivo `input/config/config.ini`.
- **Execução em Docker:** Ambiente isolado para fácil execução e gerenciamento de dependências.
- **Formatação Automática:** Formata colunas monetárias e ajusta a largura das colunas no Excel de saída.

## Como Funciona (Visão Geral)

1.  **Leitura da Configuração:** O script lê `input/config/config.ini`.
2.  **Carga de Dados:** Carrega transações dos extratos em `input/`, dados de desdobramentos de `input/correcoes/desdobramentos.xlsx` e renomeações de `input/correcoes/renomeacoes.xlsx`.
3.  **Processamento:** Aplica desdobramentos, renomeia tickers, consolida posições, calcula preços médios, busca cotações atuais, e consolida rendimentos e vendas.
4.  **Geração de Saída:** Salva o relatório consolidado em `output/consolidated_investments.xlsx`.

## Requisitos

- **Docker:** Para construir e executar o contêiner do projeto.
- **Bibliotecas Python** (listadas em `requirements.txt` e instaladas automaticamente no contêiner Docker):
  - `pandas`
  - `yfinance`
  - `openpyxl`
  - `XlsxWriter`

## Estrutura de Pastas

A seguinte estrutura de pastas é esperada no seu diretório local, que será mapeada para dentro do contêiner Docker:

seu_projeto/
│
├── consolidar_investimentos.py # O script principal
├── Dockerfile # Arquivo para construir a imagem Docker
├── requirements.txt # Lista de dependências Python
├── consolidar.bat # Script para executar no Windows (opcional)
│
├── input/
│ ├── config/
│ │ └── config.ini # Arquivo de configuração (ESSENCIAL)
│ ├── correcoes/
│ │ ├── desdobramentos.xlsx # Planilha de desdobramentos/grupamentos (opcional)
│ │ └── renomeacoes.xlsx # Planilha de renomeação de tickers (opcional)
│ └── extrato_corretora_A.xlsx # Exemplo de extrato de movimentações
│ └── extrato_corretora_B.xlsx # Outro exemplo de extrato
│
└── output/
└── consolidated_investments.xlsx # Arquivo consolidado gerado pelo script

## Configuração

1.  **Prepare os Arquivos do Projeto:**

    - Certifique-se de que os arquivos `consolidar_investimentos.py`, `Dockerfile`, `requirements.txt` e (opcionalmente) `consolidar.bat` estejam no diretório raiz do seu projeto.
    - Crie as pastas `input/config/`, `input/correcoes/` e `output/` no diretório raiz do projeto, conforme a estrutura acima.

2.  **Arquivo de Configuração (`input/config/config.ini`):**

    - Crie ou edite o arquivo `input/config/config.ini`. Se não existir, o script tentará criar um padrão (mas é melhor criá-lo manualmente se for usar Docker desde o início).
    - **Importante:** Os caminhos no `config.ini` devem ser relativos ao diretório `/app` dentro do contêiner. Os valores padrão geralmente funcionam bem com a configuração Docker fornecida.

    Conteúdo do `input/config/config.ini`:

    ```ini
    [Paths]
    InputFolder = input
    OutputFolder = output
    CorrectionsFolder = input/correcoes

    [Settings]
    CutoffDate = YYYY-MM-DD
    ```

    Substitua `YYYY-MM-DD` pela data de corte desejada (ex: `2024-12-31`).

3.  **Construa a Imagem Docker:**
    - Abra um terminal ou prompt de comando no diretório raiz do projeto (onde o `Dockerfile` está localizado).
    - Execute o comando:
      ```bash
      docker build -t consolidador-investimentos .
      ```
      Isso criará uma imagem Docker chamada `consolidador-investimentos`.

## Uso

1.  **Prepare seus arquivos de entrada:**

    - **Extratos de Movimentação:** Coloque seus arquivos Excel (`.xlsx`) de movimentações da corretora na pasta `input/` local. Cada arquivo deve conter uma planilha chamada `Movimentação` com as colunas: `Data`, `Movimentação`, `Entrada/Saída`, `Produto`, `Quantidade`, `Preço unitário`, `Valor da Operação`.
    - **Arquivo de Desdobramentos/Grupamentos (Opcional):**
      - Coloque o arquivo `desdobramentos.xlsx` na pasta `input/correcoes/` local.
    - **Arquivo de Renomeações de Tickers (Opcional):**
      - Coloque o arquivo `renomeacoes.xlsx` na pasta `input/correcoes/` local.
    - Veja a seção "Detalhes dos Arquivos de Entrada" abaixo para os formatos esperados.

2.  **Execute o Contêiner Docker:**

    - **Usando `consolidar.bat` (Windows):**

      - Simplesmente execute o arquivo `consolidar.bat` clicando duas vezes nele. Ele já está configurado para mapear as pastas locais para o contêiner.

      ```batch
      @echo off
      SET "CURRENT_DIR=%~dp0"
      docker run --rm ^
        -v "%CURRENT_DIR%input:/app/input" ^
        -v "%CURRENT_DIR%output:/app/output" ^
        consolidador-investimentos
      pause
      ```

      _(Nota: O script `consolidar.bat` original mapeava `/app/correcoes` e `/app/config` separadamente. Simplifiquei para mapear a pasta `input` inteira, que já contém `config` e `correcoes`, e adicionei o mapeamento de `output`)_. Se o seu `config.ini` e os arquivos de correção estão dentro de `input/config` e `input/correcoes` respectivamente, o mapeamento `-v "%CURRENT_DIR%input:/app/input"` é suficiente para cobri-los, pois `InputFolder = input`, `CorrectionsFolder = input/correcoes` no `config.ini` serão relativos a `/app`. O script `consolidar.bat` fornecido por você está correto ao mapear `input`, `input/correcoes` e `input/config` separadamente se os caminhos no `config.ini` forem apenas `input`, `correcoes`, etc. Vou usar o seu mapeamento original do `.bat` para o `README`.

    - **Usando a linha de comando `docker run` (Linux/macOS/Windows):**
      - Abra um terminal no diretório raiz do projeto.
      - Execute o comando:
        ```bash
        docker run --rm \
          -v "$(pwd)/input:/app/input" \
          -v "$(pwd)/input/config:/app/config" \
          -v "$(pwd)/input/correcoes:/app/correcoes" \
          -v "$(pwd)/output:/app/output" \
          consolidador-investimentos
        ```
        _(Substitua `$(pwd)` por `%cd%` no Command Prompt do Windows se não estiver usando PowerShell ou Git Bash)._

3.  **Verifique a Saída:**
    - O arquivo `consolidated_investments.xlsx` será gerado na sua pasta `output/` local.
    - Verifique o console para mensagens de status, avisos ou erros.

## Detalhes dos Arquivos de Entrada

### `input/correcoes/renomeacoes.xlsx`

Exemplo:
| Ticker Antigo | Ticker Novo |
|---------------|-------------|
| ARZZ3 | AZZA3 |
| BCFF11 | BTHF11 |
| BIDI4 | INBR32 |
| BRDT3 | VBBR3 |

### `input/correcoes/desdobramentos.xlsx`

Exemplo:
| Ticker | Data | Fator |
|---------|------------|-------|
| CPTS11 | 2023-09-26 | 10 |
| VINO11 | 2023-08-07 | 5 |
| BIDI4 | 2021-05-26 | 3 |
| BCFF11 | 2023-11-29 | 8 |
| ALZR11 | 2025-05-06 | 10,00 |
| HGBS11 | 2025-05-09 | 10,00 |
| RBVA11 | 2025-05-09 | 10,00 |

- **Ticker:** O código do ativo.
- **Data:** Data "ex" do evento (formato `YYYY-MM-DD`). Transações _anteriores ou na mesma data_ serão ajustadas.
- **Fator:**
  - Para **desdobramento** (split): Se 1 ação vira N, o fator é N. (Ex: 1 ação vira 4, Fator = 4).
  - Para **grupamento** (inplit): Se N ações viram 1, o fator é 1/N. (Ex: 10 ações viram 1, Fator = 0.1).
    _(Nota: O script espera que o pandas consiga converter o 'Fator' para numérico. Se usar vírgula como separador decimal, certifique-se de que seu Excel salve como número ou que o pandas o interprete corretamente)._

### `input/config/config.ini`

```ini
[Paths]
InputFolder = input
OutputFolder = output
CorrectionsFolder = input/correcoes

[Settings]
CutoffDate = YYYY-MM-DD

InputFolder: Caminho relativo a /app para os extratos (ex: input).

OutputFolder: Caminho relativo a /app para o relatório (ex: output).

CorrectionsFolder: Caminho relativo a /app para os arquivos de correção (ex: input/correcoes).

CutoffDate: Data limite para consolidação (formato YYYY-MM-DD).

Arquivo de Saída: output/consolidated_investments.xlsx
Contém as abas: Portfolio, Posicao_Custo, Vendas_Log, Rendimentos_Log. (Veja a descrição das funcionalidades para o detalhe das colunas de cada aba).

Como Contribuir
Contribuições são bem-vindas!

Faça um Fork do projeto.

Crie uma branch para sua feature (git checkout -b feature/nova-feature).

Faça commit de suas alterações (git commit -am 'Adiciona nova feature').

Faça push para a branch (git push origin feature/nova-feature).

Abra um Pull Request.

Licença
Este projeto é distribuído sob
```
