"""Sessão e base declarativa.

A engine é criada uma vez, a partir da `DATABASE_URL`. O `check_same_thread`
só existe no ramo do SQLite — é exigência da biblioteca, não escolha de
arquitetura, e some quando a URL aponta para Postgres.
"""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import carregar_config

_config = carregar_config()
_argumentos = {"check_same_thread": False} if _config.database_url.startswith("sqlite") else {}

engine = create_engine(_config.database_url, connect_args=_argumentos, pool_pre_ping=True)
CriarSessao = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def obter_sessao() -> Iterator[Session]:
    """Dependência do FastAPI: uma sessão por requisição, fechada no fim."""
    sessao = CriarSessao()
    try:
        yield sessao
    finally:
        sessao.close()
