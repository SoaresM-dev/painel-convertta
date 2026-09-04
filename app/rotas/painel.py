"""O painel — a única razão de a ferramenta existir.

**Uma consulta, não um laço.** A versão ingênua carrega os clientes e, para
cada um, vai ao banco buscar campanhas e leads: 1 + 2N idas ao banco para N
clientes. Aqui é uma consulta só, e o número de idas não muda quando a agência
cresce.

**Os leads são contados numa subconsulta, não no mesmo join do
investimento.** Juntar campanhas e leads na mesma linha multiplicaria o
investimento de uma campanha pelo número de leads dela — o erro clássico de
fan-out, e o tipo de defeito que só aparece quando os números já foram
mostrados para o cliente.

**A consulta devolve uma linha por campanha e a soma por cliente acontece em
Python.** É uma troca deliberada, feita quando entrou o filtro de período: o
rateio do investimento depende de aritmética de datas, que o SQLite e o
Postgres escrevem de formas diferentes, e a suíte roda nos dois. O que se paga
é uma linha por campanha em vez de uma por cliente — dezenas, não milhares — e
o que se compra é uma regra de negócio testável sem banco no ar.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import ColumnElement, case, func, select

from app.dependencias import SessaoDep, UsuarioDep
from app.models import Campanha, Canal, Cliente, Lead, StatusLead
from app.schemas import (
    CampanhaDetalhe,
    DetalheCliente,
    EstagioFunil,
    Funil,
    LeadRecente,
    LinhaCanal,
    LinhaResumo,
    PontoSerie,
    Resumo,
    Serie,
)

rotas = APIRouter(prefix="/api/painel", tags=["painel"])

# A ordem em que o funil é desenhado. `perdido` fecha a lista porque não é um
# estágio a caminho da venda: é para onde o lead sai.
ORDEM_FUNIL: tuple[StatusLead, ...] = (
    StatusLead.NOVO,
    StatusLead.CONTATADO,
    StatusLead.QUALIFICADO,
    StatusLead.GANHO,
    StatusLead.PERDIDO,
)

LIMITE_LEADS_RECENTES = 20


# --- as contas, isoladas do banco ---

def custo_por_lead(investimento_centavos: int, leads: int) -> int | None:
    """Sem lead não há custo por lead. `None` diz "ainda não dá para saber" —
    e o painel mostra um traço, não R$ 0,00, que seria mentira animadora."""
    if leads <= 0:
        return None
    return round(investimento_centavos / leads)


def taxa(ganhos: int, leads: int) -> float | None:
    """Mesma regra do custo por lead: sem lead, a taxa não é 0%, é desconhecida."""
    if leads <= 0:
        return None
    return round(ganhos / leads, 4)


# --- período ---

@dataclass(frozen=True)
class Periodo:
    """Recorte de tempo do painel. Os dois lados são opcionais e independentes:
    `de` sem `ate` significa "de lá para cá"."""

    de: date | None = None
    ate: date | None = None


def periodo(
    de: Annotated[date | None, Query(description="Primeiro dia do recorte, inclusive.")] = None,
    ate: Annotated[date | None, Query(description="Último dia do recorte, inclusive.")] = None,
) -> Periodo:
    if de is not None and ate is not None and de > ate:
        # 422 literal: o nome da constante mudou entre versões do Starlette
        # e não vale acoplar a rota a isso.
        raise HTTPException(status_code=422, detail="A data inicial é posterior à final")
    return Periodo(de=de, ate=ate)


PeriodoDep = Annotated[Periodo, Depends(periodo)]


def condicoes_de_lead(p: Periodo) -> list[ColumnElement[bool]]:
    """Recorta os leads pelo `criado_em`.

    O limite superior é "menor que a meia-noite do dia seguinte", e não "menor
    ou igual à data". Com a segunda forma, o banco compara o carimbo com um
    instante de hora zero e o dia inteiro do limite some do resultado — o
    defeito silencioso em que o último dia do mês nunca aparece no relatório
    do mês.
    """
    condicoes: list[ColumnElement[bool]] = []
    if p.de is not None:
        condicoes.append(Lead.criado_em >= datetime.combine(p.de, time.min, tzinfo=UTC))
    if p.ate is not None:
        limite = datetime.combine(p.ate + timedelta(days=1), time.min, tzinfo=UTC)
        condicoes.append(Lead.criado_em < limite)
    return condicoes


def dias_dentro(inicio: date, fim: date | None, p: Periodo, hoje: date) -> tuple[int, int]:
    """Devolve os dias da campanha que caem no período e a duração total dela.

    Campanha sem `fim` está no ar: vale até hoje. Os dois lados são inclusivos,
    então campanha de um dia só dura 1, e não 0.
    """
    fim_efetivo = max(fim if fim is not None else hoje, inicio)
    total = (fim_efetivo - inicio).days + 1

    primeiro = max(p.de, inicio) if p.de is not None else inicio
    ultimo = min(p.ate, fim_efetivo) if p.ate is not None else fim_efetivo
    return max((ultimo - primeiro).days + 1, 0), total


def rateio(investimento_centavos: int, dentro: int, total: int) -> int:
    """A fatia do investimento que cai no período, proporcional aos dias.

    Contar o investimento inteiro de uma campanha de 90 dias dentro de um
    recorte de 7 dias faria o custo por lead da semana parecer treze vezes
    maior do que é. Ratear por dia não é exato — verba não se gasta em
    prestação igual — mas erra por pouco e na direção certa, enquanto não
    ratear erra por uma ordem de grandeza.
    """
    if dentro <= 0 or total <= 0:
        return 0
    if dentro >= total:
        return investimento_centavos
    return round(investimento_centavos * dentro / total)


# --- a leitura do banco, compartilhada por todas as rotas ---

@dataclass(frozen=True)
class Fatia:
    """Uma campanha já recortada pelo período.

    `canal is None` marca a campanha que não encosta no recorte — e também o
    cliente que ainda não tem campanha nenhuma. Os dois casos produzem a mesma
    coisa: o cliente aparece na lista, zerado. Cliente que some da tela quando
    o filtro aperta é cliente que o usuário acha que foi apagado.
    """

    cliente_id: int
    cliente: str
    campanha_id: int | None
    canal: Canal | None
    investimento_centavos: int
    leads: int
    leads_ganhos: int


def _leads_por_campanha(p: Periodo):
    consulta = select(
        Lead.campanha_id.label("campanha_id"),
        func.count(Lead.id).label("leads"),
        func.sum(case((Lead.status == StatusLead.GANHO, 1), else_=0)).label("ganhos"),
    ).group_by(Lead.campanha_id)
    for condicao in condicoes_de_lead(p):
        consulta = consulta.where(condicao)
    return consulta.subquery()


def _fatias(sessao: SessaoDep, p: Periodo, hoje: date) -> list[Fatia]:
    por_campanha = _leads_por_campanha(p)

    linhas = sessao.execute(
        select(
            Cliente.id,
            Cliente.nome,
            Campanha.id,
            Campanha.canal,
            Campanha.investimento_centavos,
            Campanha.inicio,
            Campanha.fim,
            func.coalesce(por_campanha.c.leads, 0),
            func.coalesce(por_campanha.c.ganhos, 0),
        )
        .select_from(Cliente)
        .outerjoin(Campanha, Campanha.cliente_id == Cliente.id)
        .outerjoin(por_campanha, por_campanha.c.campanha_id == Campanha.id)
        .order_by(Cliente.nome, Campanha.id)
    ).all()

    fatias: list[Fatia] = []
    for cliente_id, cliente, campanha_id, canal, investimento, inicio, fim, leads, ganhos in linhas:
        vazia = Fatia(cliente_id, cliente, None, None, 0, 0, 0)
        if campanha_id is None:
            fatias.append(vazia)
            continue
        dentro, total = dias_dentro(inicio, fim, p, hoje)
        if dentro == 0:
            fatias.append(vazia)
            continue
        fatias.append(
            Fatia(
                cliente_id=cliente_id,
                cliente=cliente,
                campanha_id=campanha_id,
                canal=canal,
                investimento_centavos=rateio(int(investimento), dentro, total),
                leads=int(leads),
                leads_ganhos=int(ganhos or 0),
            )
        )
    return fatias


def _somar(fatias: Iterable[Fatia]) -> tuple[int, int, int, int]:
    """Devolve campanhas, investimento, leads e ganhos, nessa ordem."""
    campanhas = investimento = leads = ganhos = 0
    for f in fatias:
        if f.campanha_id is not None:
            campanhas += 1
        investimento += f.investimento_centavos
        leads += f.leads
        ganhos += f.leads_ganhos
    return campanhas, investimento, leads, ganhos


# --- rotas ---

@rotas.get("/resumo", response_model=Resumo)
def resumo(sessao: SessaoDep, _usuario: UsuarioDep, p: PeriodoDep) -> Resumo:
    fatias = _fatias(sessao, p, date.today())

    por_cliente: dict[tuple[int, str], list[Fatia]] = {}
    for f in fatias:
        por_cliente.setdefault((f.cliente_id, f.cliente), []).append(f)

    linhas = []
    for (cliente_id, nome), do_cliente in por_cliente.items():
        campanhas, investimento, leads, ganhos = _somar(do_cliente)
        linhas.append(
            LinhaResumo(
                cliente_id=cliente_id,
                cliente=nome,
                campanhas=campanhas,
                investimento_centavos=investimento,
                leads=leads,
                leads_ganhos=ganhos,
                custo_por_lead_centavos=custo_por_lead(investimento, leads),
                taxa_conversao=taxa(ganhos, leads),
            )
        )

    campanhas, investimento, leads, ganhos = _somar(fatias)
    return Resumo(
        investimento_centavos=investimento,
        campanhas=campanhas,
        leads=leads,
        leads_ganhos=ganhos,
        custo_por_lead_centavos=custo_por_lead(investimento, leads),
        taxa_conversao=taxa(ganhos, leads),
        linhas=linhas,
    )


@rotas.get("/canais", response_model=list[LinhaCanal])
def canais(sessao: SessaoDep, _usuario: UsuarioDep, p: PeriodoDep) -> list[LinhaCanal]:
    """Google x Meta, lado a lado.

    Os dois canais saem sempre, mesmo zerados. Omitir o canal sem campanha
    faria a barra sumir do gráfico, e barra ausente lê-se como "não existe" em
    vez de "não teve investimento neste recorte".
    """
    fatias = _fatias(sessao, p, date.today())
    saida = []
    for canal in Canal:
        campanhas, investimento, leads, ganhos = _somar(f for f in fatias if f.canal == canal)
        saida.append(
            LinhaCanal(
                canal=canal,
                campanhas=campanhas,
                investimento_centavos=investimento,
                leads=leads,
                leads_ganhos=ganhos,
                custo_por_lead_centavos=custo_por_lead(investimento, leads),
                taxa_conversao=taxa(ganhos, leads),
            )
        )
    return saida


@rotas.get("/funil", response_model=Funil)
def funil(sessao: SessaoDep, _usuario: UsuarioDep, p: PeriodoDep) -> Funil:
    consulta = select(Lead.status, func.count(Lead.id)).group_by(Lead.status)
    for condicao in condicoes_de_lead(p):
        consulta = consulta.where(condicao)
    contagem = {status: int(quantos) for status, quantos in sessao.execute(consulta)}

    # Estágio sem lead vem com zero, e não some: o funil precisa mostrar o
    # degrau vazio, que é justamente onde o processo está travando.
    estagios = [EstagioFunil(status=s, leads=contagem.get(s, 0)) for s in ORDEM_FUNIL]
    return Funil(total=sum(e.leads for e in estagios), estagios=estagios)


def _para_data(valor: object) -> date:
    """`func.date()` devolve `date` no Postgres e `str` no SQLite.

    A suíte roda nos dois, e é o tipo de diferença que passa verde na máquina
    de quem escreveu e quebra na CI — ou, pior, o contrário.
    """
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    return date.fromisoformat(str(valor)[:10])


@rotas.get("/serie", response_model=Serie)
def serie(sessao: SessaoDep, _usuario: UsuarioDep, p: PeriodoDep) -> Serie:
    """Leads por dia, com os dias vazios preenchidos com zero.

    O intervalo é limitado dos dois lados por dado real — nunca pelo que o
    cliente pediu. Sem isso, `?de=1900-01-01` mandaria a API preencher
    quarenta mil dias de zero para desenhar meia dúzia de pontos.
    """
    dia = func.date(Lead.criado_em)
    consulta = (
        select(
            dia,
            func.count(Lead.id),
            func.sum(case((Lead.status == StatusLead.GANHO, 1), else_=0)),
        )
        .group_by(dia)
        .order_by(dia)
    )
    for condicao in condicoes_de_lead(p):
        consulta = consulta.where(condicao)

    contagem = {
        _para_data(d): (int(leads), int(ganhos or 0))
        for d, leads, ganhos in sessao.execute(consulta)
    }
    if not contagem:
        return Serie(pontos=[])

    hoje = date.today()
    primeiro, ultimo = min(contagem), max(contagem)
    inicio = max(p.de, primeiro) if p.de is not None else primeiro
    fim = min(p.ate, hoje) if p.ate is not None else max(ultimo, hoje)
    fim = max(fim, inicio)

    pontos = []
    atual = inicio
    while atual <= fim:
        leads, ganhos = contagem.get(atual, (0, 0))
        pontos.append(PontoSerie(dia=atual, leads=leads, leads_ganhos=ganhos))
        atual += timedelta(days=1)
    return Serie(pontos=pontos)


@rotas.get("/clientes/{cliente_id}", response_model=DetalheCliente)
def detalhe_do_cliente(
    cliente_id: int, sessao: SessaoDep, _usuario: UsuarioDep, p: PeriodoDep
) -> DetalheCliente:
    """O que a linha da tabela esconde: campanha a campanha, e quem chegou.

    As rotas `GET /api/campanhas?cliente_id=` e `GET /api/leads?campanha_id=`
    já existiam, e a tela poderia montar isto sozinha — ao custo de uma
    chamada por campanha. Uma rota que responde a tela inteira em duas
    consultas custa menos que N+1 requisições atravessando a internet.
    """
    cliente = sessao.get(Cliente, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    hoje = date.today()
    por_campanha = _leads_por_campanha(p)
    linhas = sessao.execute(
        select(
            Campanha.id,
            Campanha.nome,
            Campanha.canal,
            Campanha.investimento_centavos,
            Campanha.inicio,
            Campanha.fim,
            func.coalesce(por_campanha.c.leads, 0),
            func.coalesce(por_campanha.c.ganhos, 0),
        )
        .select_from(Campanha)
        .outerjoin(por_campanha, por_campanha.c.campanha_id == Campanha.id)
        .where(Campanha.cliente_id == cliente_id)
        .order_by(Campanha.inicio.desc(), Campanha.id)
    ).all()

    campanhas = []
    for camp_id, nome, canal, investimento, inicio, fim, leads_bd, ganhos_bd in linhas:
        dentro, total = dias_dentro(inicio, fim, p, hoje)
        if dentro == 0:
            continue
        leads, ganhos = int(leads_bd), int(ganhos_bd or 0)
        rateado = rateio(int(investimento), dentro, total)
        campanhas.append(
            CampanhaDetalhe(
                id=camp_id,
                nome=nome,
                canal=canal,
                investimento_centavos=rateado,
                inicio=inicio,
                fim=fim,
                leads=leads,
                leads_ganhos=ganhos,
                custo_por_lead_centavos=custo_por_lead(rateado, leads),
                taxa_conversao=taxa(ganhos, leads),
            )
        )

    consulta_leads = (
        select(Lead, Campanha.nome)
        .join(Campanha, Campanha.id == Lead.campanha_id)
        .where(Campanha.cliente_id == cliente_id)
        .order_by(Lead.criado_em.desc(), Lead.id.desc())
        .limit(LIMITE_LEADS_RECENTES)
    )
    for condicao in condicoes_de_lead(p):
        consulta_leads = consulta_leads.where(condicao)

    recentes = [
        LeadRecente(
            id=lead.id,
            nome=lead.nome,
            email=lead.email,
            telefone=lead.telefone,
            status=lead.status,
            criado_em=lead.criado_em,
            campanha_id=lead.campanha_id,
            campanha=nome_campanha,
        )
        for lead, nome_campanha in sessao.execute(consulta_leads)
    ]

    return DetalheCliente(
        cliente_id=cliente.id,
        cliente=cliente.nome,
        campanhas=campanhas,
        leads_recentes=recentes,
    )
