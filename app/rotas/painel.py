"""O resumo — a única razão de a ferramenta existir.

**Uma consulta, não um laço.** A versão ingênua carrega os clientes e, para
cada um, vai ao banco buscar campanhas e leads: 1 + 2N idas ao banco para N
clientes. Com dez clientes já dá vinte e uma. Aqui são duas agregações e um
`join`, e o número de consultas não muda quando a agência cresce.

**Os leads são contados numa subconsulta, não no mesmo join do
investimento.** Juntar campanhas e leads na mesma linha multiplicaria o
investimento de uma campanha pelo número de leads dela — o erro clássico de
fan-out, e o tipo de defeito que só aparece quando os números já foram
mostrados para o cliente.
"""
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import case, func, select

from app.dependencias import SessaoDep, UsuarioDep
from app.models import Campanha, Cliente, Lead, StatusLead
from app.schemas import LinhaResumo, Resumo

rotas = APIRouter(prefix="/api/painel", tags=["painel"])


def custo_por_lead(investimento_centavos: int, leads: int) -> int | None:
    """Sem lead não há custo por lead. `None` diz "ainda não dá para saber" —
    e o painel mostra um traço, não R$ 0,00, que seria mentira animadora."""
    if leads <= 0:
        return None
    return round(investimento_centavos / leads)


@rotas.get("/resumo", response_model=Resumo)
def resumo(sessao: SessaoDep, _usuario: UsuarioDep) -> Resumo:
    por_campanha = (
        select(
            Lead.campanha_id.label("campanha_id"),
            func.count(Lead.id).label("leads"),
            func.sum(case((Lead.status == StatusLead.GANHO, 1), else_=0)).label("ganhos"),
        )
        .group_by(Lead.campanha_id)
        .subquery()
    )

    linhas_bd = sessao.execute(
        select(
            Cliente.id,
            Cliente.nome,
            func.count(func.distinct(Campanha.id)),
            func.coalesce(func.sum(Campanha.investimento_centavos), 0),
            func.coalesce(func.sum(por_campanha.c.leads), 0),
            func.coalesce(func.sum(por_campanha.c.ganhos), 0),
        )
        .select_from(Cliente)
        .outerjoin(Campanha, Campanha.cliente_id == Cliente.id)
        .outerjoin(por_campanha, por_campanha.c.campanha_id == Campanha.id)
        .group_by(Cliente.id, Cliente.nome)
        .order_by(Cliente.nome)
    ).all()

    linhas = [
        LinhaResumo(
            cliente_id=cliente_id,
            cliente=nome,
            campanhas=campanhas,
            investimento_centavos=int(investimento),
            leads=int(leads),
            leads_ganhos=int(ganhos),
            custo_por_lead_centavos=custo_por_lead(int(investimento), int(leads)),
            taxa_conversao=round(int(ganhos) / int(leads), 4) if leads else None,
        )
        for cliente_id, nome, campanhas, investimento, leads, ganhos in linhas_bd
    ]

    investimento_total = sum(linha.investimento_centavos for linha in linhas)
    leads_total = sum(linha.leads for linha in linhas)
    ganhos_total = sum(linha.leads_ganhos for linha in linhas)

    return Resumo(
        investimento_centavos=investimento_total,
        leads=leads_total,
        leads_ganhos=ganhos_total,
        custo_por_lead_centavos=custo_por_lead(investimento_total, leads_total),
        linhas=linhas,
    )
