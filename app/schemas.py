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
    campanhas: int
    leads: int
    leads_ganhos: int
    custo_por_lead_centavos: int | None
    taxa_conversao: float | None
    linhas: list[LinhaResumo]


class LinhaCanal(BaseModel):
    """Google x Meta. O canal sempre esteve na tabela `campanhas` e nunca
    chegou à tela — e é a comparação que uma agência de tráfego pago olha
    primeiro: qual dos dois está entregando lead mais barato."""

    canal: Canal
    campanhas: int
    investimento_centavos: int
    leads: int
    leads_ganhos: int
    custo_por_lead_centavos: int | None
    taxa_conversao: float | None


class EstagioFunil(BaseModel):
    status: StatusLead
    leads: int


class Funil(BaseModel):
    """Distribuição por estágio — **não** um funil cumulativo.

    O banco guarda o status *atual* do lead, não o histórico por onde ele
    passou. Um funil cumulativo de verdade diria "82 chegaram a contatado",
    contando também quem já avançou para qualificado e ganho; esse número não
    existe aqui e inventá-lo seria mentir com aparência de relatório. O que
    sai é o que se pode provar: quantos leads estão em cada estágio agora.
    """

    total: int
    estagios: list[EstagioFunil]


class PontoSerie(BaseModel):
    dia: date
    leads: int
    leads_ganhos: int


class Serie(BaseModel):
    """Dias sem lead vêm com zero, não vêm ausentes.

    Omitir o dia vazio faz a linha do gráfico pular o buraco e ligar dois
    pontos distantes como se fossem vizinhos — a queda desaparece do desenho
    justamente quando ela é a informação.
    """

    pontos: list[PontoSerie]


class CampanhaDetalhe(BaseModel):
    id: int
    nome: str
    canal: Canal
    investimento_centavos: int
    inicio: date
    fim: date | None
    leads: int
    leads_ganhos: int
    custo_por_lead_centavos: int | None
    taxa_conversao: float | None


class LeadRecente(BaseModel):
    id: int
    nome: str
    email: str | None
    telefone: str | None
    status: StatusLead
    criado_em: datetime
    campanha_id: int
    campanha: str


class DetalheCliente(BaseModel):
    cliente_id: int
    cliente: str
    campanhas: list[CampanhaDetalhe]
    leads_recentes: list[LeadRecente]
