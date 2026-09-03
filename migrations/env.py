"""Alembic ligado ao mesmo config da aplicação.

A URL vem do ambiente, nunca do `alembic.ini`: é a mesma variável que a API
usa, então migração e aplicação não podem apontar para bancos diferentes —
que é como se descobre, em produção, que a migração rodou no banco errado.
"""
from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app import models  # noqa: F401 — importa para registrar as tabelas no metadata
from app.config import carregar_config
from app.db import Base

config = context.config
config.set_main_option("sqlalchemy.url", carregar_config().database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    conectavel = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with conectavel.connect() as conexao:
        context.configure(connection=conexao, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
