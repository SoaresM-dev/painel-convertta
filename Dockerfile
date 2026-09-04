FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

# Dependências primeiro, código depois: mudar uma linha de Python não
# invalida a camada do pip, e o build volta a levar segundos.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# O boot inteiro mora em `scripts/iniciar.sh` — migração, seed e uvicorn, nessa
# ordem. Fica num arquivo, e não nesta linha, porque o campo de comando do
# provedor não passa por shell e engole o `&&`; e a porta sai de lá expandida
# de `$PORT`, que é como todo PaaS a injeta. Chamado por `sh` em vez de
# `./scripts/iniciar.sh` porque o arquivo vem do Windows, onde não existe bit
# de execução.
CMD ["sh", "scripts/iniciar.sh"]
