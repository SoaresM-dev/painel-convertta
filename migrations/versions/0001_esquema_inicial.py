"""Esquema inicial: usuários, clientes, campanhas e leads.

Revision ID: 0001
Revises:
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

CANAIS = sa.Enum("GOOGLE_ADS", "META_ADS", name="canal", native_enum=False, length=20)
STATUS = sa.Enum(
    "NOVO", "CONTATADO", "QUALIFICADO", "GANHO", "PERDIDO",
    name="statuslead", native_enum=False, length=20,
)


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("senha_hash", sa.String(255), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_usuarios_email", "usuarios", ["email"])

    op.create_table(
        "clientes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("nome", sa.String(120), nullable=False, unique=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_clientes_nome", "clientes", ["nome"])

    op.create_table(
        "campanhas",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "cliente_id",
            sa.Integer,
            sa.ForeignKey("clientes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("nome", sa.String(160), nullable=False),
        sa.Column("canal", CANAIS, nullable=False),
        sa.Column("investimento_centavos", sa.Integer, nullable=False, server_default="0"),
        sa.Column("inicio", sa.Date, nullable=False),
        sa.Column("fim", sa.Date, nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("cliente_id", "nome", name="uq_campanha_por_cliente"),
    )
    op.create_index("ix_campanhas_cliente_id", "campanhas", ["cliente_id"])

    op.create_table(
        "leads",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "campanha_id",
            sa.Integer,
            sa.ForeignKey("campanhas.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("nome", sa.String(160), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("telefone", sa.String(40), nullable=True),
        sa.Column("status", STATUS, nullable=False, server_default="NOVO"),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_leads_campanha_id", "leads", ["campanha_id"])


def downgrade() -> None:
    op.drop_table("leads")
    op.drop_table("campanhas")
    op.drop_table("clientes")
    op.drop_table("usuarios")
