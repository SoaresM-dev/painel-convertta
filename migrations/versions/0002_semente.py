"""Marca da versão da semente, para o dado de demonstração poder ser corrigido.

A semente era idempotente **por existência**: "esta campanha já existe? então
pula". Isso protege contra duplicata e, sem querer, impede correção — mudar o
conteúdo da semente nunca alcança um banco que já foi semeado uma vez.

Foi exatamente o que aconteceu quando os leads ganharam data e o estágio
`perdido`: o código subiu, a produção continuou com o dado velho, e o gráfico no
ar era um pico vertical de um dia só. Com a marca de versão, a semente deixa de
ser "não duplica" e passa a ser "converge para a definição atual".

Revision ID: 0002
Revises: 0001
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "semente",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("versao", sa.Integer, nullable=False),
        sa.Column("aplicada_em", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("semente")
