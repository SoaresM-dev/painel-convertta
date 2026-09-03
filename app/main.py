"""Ponto de entrada da API."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import carregar_config
from app.rotas import auth, campanhas, clientes, leads, painel

config = carregar_config()

app = FastAPI(
    title="Painel Convertta",
    description="Leads e campanhas de tráfego pago dos clientes num lugar só, "
    "com custo por lead calculado.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.origens,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for modulo in (auth, clientes, campanhas, leads, painel):
    app.include_router(modulo.rotas)


@app.get("/api/saude", tags=["infra"])
def saude() -> dict[str, str]:
    """Usada pelo healthcheck do docker-compose e pelo Render."""
    return {"status": "ok"}
