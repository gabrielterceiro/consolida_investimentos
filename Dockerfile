# 1. Usar uma imagem base oficial do Python
# Escolha uma versão que seja compatível com seu script. Python 3.9 é uma boa escolha geral.
FROM python:3.9-slim

# 2. Definir o diretório de trabalho dentro do contêiner
# Todos os comandos subsequentes serão executados a partir deste diretório
WORKDIR /app

# 3. Copiar o arquivo de dependências para o diretório de trabalho
COPY requirements.txt .

# 4. Instalar as dependências listadas no requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiar seu script Python para o diretório de trabalho no contêiner
COPY consolidar_investimentos.py .

# 6. Criar as pastas de input, output e correcoes DENTRO do contêiner.
# Embora vamos usar volumes para mapear pastas locais para estas,
# é uma boa prática criá-las na imagem para que o script sempre as encontre,
# mesmo que volumes não sejam montados (embora neste caso sejam essenciais).
RUN mkdir -p /app/input && \
    mkdir -p /app/output && \
    mkdir -p /app/correcoes

# 7. Definir o comando que será executado quando o contêiner iniciar
# Este comando executa seu script Python
CMD ["python", "consolidar_investimentos.py"]