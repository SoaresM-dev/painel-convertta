"""Ambiente da suíte.

**Banco novo por teste, em memória.** Cada teste recebe um banco vazio: o
resultado não depende da ordem de execução nem do que sobrou do teste
anterior — a categoria de defeito mais cara de diagnosticar numa suíte.

**A CI roda os mesmos testes contra Postgres.** Quando `DATABASE_URL` aponta
para Postgres, é ele que responde; sem ela, SQLite em memória, e `pytest`
funciona num clone recém-feito sem serviço nenhum no ar.
"""
from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# 32+ bytes: abaixo disso o PyJWT avisa que a chave é curta para HS256.
os.environ.setdefault("SEGREDO_JWT", "segredo-de-teste-com-tamanho-suficiente-para-hs256")

from app.db import Base, obter_sessao  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Usuario  # noqa: E402
from app.seguranca import cifrar_senha  # noqa: E402

URL_TESTE = os.environ.get("DATABASE_URL", "sqlite+pysqlite:///:memory:")
E_SQLITE = URL_TESTE.startswith("sqlite")

SENHA_DEMO = "senha-de-teste-123"
EMAIL_DEMO = "demo@convertta.com.br"


@pytest.fixture
def sessao() -> Iterator[Session]:
    if E_SQLITE:
        engine = create_engine(
            URL_TESTE, connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
    else:
        engine = create_engine(URL_TESTE)
        with engine.begin() as conexao:
            # Postgres: derruba o esquema inteiro entre testes, o equivalente
            # ao banco em memória novo do SQLite.
            conexao.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))

    Base.metadata.create_all(engine)
    Criar = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Criar() as s:
        yield s
    engine.dispose()


@pytest.fixture
def usuario(sessao: Session) -> Usuario:
    u = Usuario(email=EMAIL_DEMO, nome="Demo", senha_hash=cifrar_senha(SENHA_DEMO))
    sessao.add(u)
    sessao.commit()
    sessao.refresh(u)
    return u


@pytest.fixture
def cliente_http(sessao: Session) -> Iterator[TestClient]:
    """Cliente HTTP **sem** token — para provar que as rotas recusam anônimo."""
    app.dependency_overrides[obter_sessao] = lambda: sessao
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def autenticado(cliente_http: TestClient, usuario: Usuario) -> TestClient:
    resposta = cliente_http.post(
        "/api/auth/token", data={"username": EMAIL_DEMO, "password": SENHA_DEMO}
    )
    assert resposta.status_code == 200, resposta.text
    cliente_http.headers["Authorization"] = f"Bearer {resposta.json()['access_token']}"
    return cliente_http
