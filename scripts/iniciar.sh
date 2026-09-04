#!/bin/sh
# Boot da API. Existe porque o campo de comando do Render (e do Railway, e de
# quase todo PaaS) não passa por shell: ele quebra a linha em argumentos e
# executa direto, então o `&&` chega como argumento do primeiro comando. Três
# passos encadeados precisam de um arquivo.
set -e

alembic upgrade head
python -m scripts.semear

# `exec` para o uvicorn herdar o PID 1 e receber o SIGTERM do provedor: sem
# isso o shell segura o sinal e o contêiner morre por timeout a cada deploy.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
