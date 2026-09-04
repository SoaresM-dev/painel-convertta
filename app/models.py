"""As três entidades do painel, e só elas.

**Escopo travado de propósito:** cliente, campanha e lead. Escopo que cresce é
o que mata projeto de portfólio — a versão que fica pronta vale mais que a
versão completa que nunca sobe.

**Dinheiro em centavos, sempre inteiro.** `float` para dinheiro erra por
arredondamento binário: 0,1 + 0,2 não dá 0,3, e um relatório de investimento
que fecha com um centavo de diferença é um relatório em que ninguém confia.
A conversão para reais acontece na borda, na hora de exibir.
"""
from __future__ import annotations

import enum
from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def agora() -> datetime:
    """UTC com fuso explícito. Datetime ingênuo em banco é dor garantida
    no primeiro horário de verão."""
    return datetime.now(UTC)


class Canal(enum.StrEnum):
    GOOGLE_ADS = "google_ads"
    META_ADS = "meta_ads"


class StatusLead(enum.StrEnum):
    NOVO = "novo"
    CONTATADO = "contatado"
    QUALIFICADO = "qualificado"
    GANHO = "ganho"
    PERDIDO = "perdido"


class Semente(Base):
    """Qual versão dos dados de demonstração está neste banco.

    **Não é uma quarta entidade do domínio** — é escrituração, e por isso não
    quebra o escopo travado acima. Existe porque a semente era idempotente por
    existência ("esta campanha já existe? então pula"), e idempotência assim
    protege contra duplicata mas impede correção: mudar o conteúdo da semente
    nunca alcançava um banco já semeado.

    Foi o que aconteceu quando os leads ganharam data e o estágio `perdido` —
    o código subiu, a produção continuou com o dado velho, e o gráfico no ar
    era um pico vertical de um dia só. Com a marca, a semente deixa de ser
    "não duplica" e passa a ser "converge para a definição atual".
    """

    __tablename__ = "semente"

    id: Mapped[int] = mapped_column(primary_key=True)
    versao: Mapped[int] = mapped_column(Integer)
    aplicada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    nome: Mapped[str] = mapped_column(String(120))
    # O hash do bcrypt, nunca a senha. O banco não sabe a senha de ninguém.
    senha_hash: Mapped[str] = mapped_column(String(255))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)

    campanhas: Mapped[list[Campanha]] = relationship(
        back_populates="cliente", cascade="all, delete-orphan"
    )


class Campanha(Base):
    __tablename__ = "campanhas"
    # O mesmo cliente não tem duas campanhas com o mesmo nome. É a regra que
    # evita o relatório com duas linhas iguais e números diferentes.
    __table_args__ = (UniqueConstraint("cliente_id", "nome", name="uq_campanha_por_cliente"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("clientes.id", ondelete="CASCADE"), index=True
    )
    nome: Mapped[str] = mapped_column(String(160))
    canal: Mapped[Canal] = mapped_column(Enum(Canal, native_enum=False, length=20))
    investimento_centavos: Mapped[int] = mapped_column(Integer, default=0)
    inicio: Mapped[date] = mapped_column(Date)
    fim: Mapped[date | None] = mapped_column(Date, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)

    cliente: Mapped[Cliente] = relationship(back_populates="campanhas")
    leads: Mapped[list[Lead]] = relationship(
        back_populates="campanha", cascade="all, delete-orphan"
    )


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    campanha_id: Mapped[int] = mapped_column(
        ForeignKey("campanhas.id", ondelete="CASCADE"), index=True
    )
    nome: Mapped[str] = mapped_column(String(160))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[StatusLead] = mapped_column(
        Enum(StatusLead, native_enum=False, length=20), default=StatusLead.NOVO
    )
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)

    campanha: Mapped[Campanha] = relationship(back_populates="leads")
