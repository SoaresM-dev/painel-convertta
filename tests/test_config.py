"""A normalização da URL do banco.

Existe um teste para isto porque o defeito que ele trava não aparece em
desenvolvimento nem na CI — só no primeiro deploy, com uma mensagem que aponta
para a biblioteca errada.
"""
from __future__ import annotations

import pytest

from app.config import Config

CASOS = [
    # o que Render, Railway e Fly entregam
    ("postgresql://u:s@host:5432/db", "postgresql+psycopg://u:s@host:5432/db"),
    # a forma antiga, que provedor velho ainda usa e o SQLAlchemy removeu na 1.4
    ("postgres://u:s@host:5432/db", "postgresql+psycopg://u:s@host:5432/db"),
    # já normalizada: não pode ser mexida
    ("postgresql+psycopg://u:s@host/db", "postgresql+psycopg://u:s@host/db"),
    # SQLite, o padrão de teste: intocado
    ("sqlite+pysqlite:///./painel.db", "sqlite+pysqlite:///./painel.db"),
]


@pytest.mark.parametrize("entrada,esperado", CASOS)
def test_normaliza_o_driver_do_postgres(entrada, esperado):
    assert Config(database_url=entrada).database_url == esperado


def test_a_senha_com_caractere_especial_sobrevive():
    """Senha gerada por provedor costuma ter `/` e `+`. A troca é só do
    prefixo — se alguém trocar por um `replace` solto, isto quebra."""
    url = "postgresql://user:a+b/c@host:5432/db"
    assert Config(database_url=url).database_url == "postgresql+psycopg://user:a+b/c@host:5432/db"
