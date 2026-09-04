FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

# Dependências primeiro, código depois: mudar uma linha de Python não
# invalida a camada do pip, e o build volta a levar segundos.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Forma shell, e não a de lista, de propósito: é o que permite expandir
# `${PORT}`. Todo PaaS injeta a porta por variável — Render, Railway, Fly,
# Cloud Run — e um contêiner que escuta numa porta fixa passa no build, sobe
# sem erro e nunca recebe requisição, porque o roteador do provedor bate numa
# porta onde não há ninguém. O 8000 é só o padrão para rodar local.
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
