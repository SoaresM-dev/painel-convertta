"""Contratos de entrada e saída.

Separados dos models de propósito: o que entra pela rede é validado antes de
virar linha no banco, e o que sai é escolhido — `senha_hash` não tem schema
de saída, então não existe rota capaz de vazá-lo por descuido.
"""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import Canal, StatusLead


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UsuarioSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    nome: str


# --- cliente ---

class ClienteEntrada(BaseModel):
    nome: str = Field(min_length=2, max_length=120)


class ClienteSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    criado_em: datetime


# --- campanha ---

class CampanhaEntrada(BaseModel):
    cliente_id: int
    nome: str = Field(min_length=2, max_length=160)
    canal: Canal
    # Em centavos, e nunca negativo: investimento negativo tornaria o custo
    # por lead negativo, e o painel inteiro deixaria de fazer sentido.
    investimento_centavos: int = Field(ge=0, default=0)
    inicio: date
    fim: date | None = None


class CampanhaSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: int
    nome: str
    canal: Canal
    investimento_centavos: int
    inicio: date
    fim: date | None


# --- lead ---

class LeadEntrada(BaseModel):
    campanha_id: int
    nome: str = Field(min_length=2, max_length=160)
    email: EmailStr | None = None
    telefone: str | None = Field(default=None, max_length=40)
    status: StatusLead = StatusLead.NOVO


class LeadAtualizacao(BaseModel):
    status: StatusLead


class LeadSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campanha_id: int
    nome: str
    email: str | None
    telefone: str | None
    status: StatusLead
    criado_em: datetime


# --- painel ---

class LinhaResumo(BaseModel):
    cliente_id: int
    cliente: str
    campanhas: int
    investimento_centavos: int
    leads: int
    leads_ganhos: int
    # None quando não há lead nenhum: dividir por zero não é "custo zero",
    # é "ainda não dá para saber". O painel mostra "—", não "R$ 0,00".
    custo_por_lead_centavos: int | None
    taxa_conversao: float | None


class Resumo(BaseModel):
    investimento_centavos: int
    leads: int
    leads_ganhos: int
    custo_por_lead_centavos: int | None
    linhas: list[LinhaResumo]
