"""A semente é dado de demonstração — e dado de demonstração que não sustenta
o gráfico é pior que gráfico nenhum.

A versão anterior deixava o `criado_em` cair no `default=agora()` e nunca
gerava `perdido`. Nada disso aparecia na tela de então; os dois quebrariam a
série temporal e o funil no dia em que eles existissem. Estes testes travam as
duas correções.
"""
from __future__ import annotations

from datetime import date, timedelta
from random import Random

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Campanha, Canal, Cliente, Lead, Semente, StatusLead
from scripts.semear import (
    CLIENTES,
    VERSAO_SEMENTE,
    data_do_lead,
    limpar_demo,
    marcar,
    status_do_lead,
    versao_no_banco,
)

HOJE = date(2026, 9, 4)


def _statuses(total: int, ganhos: int) -> list[StatusLead]:
    return [status_do_lead(i, total, ganhos) for i in range(total)]


def test_os_cinco_estagios_aparecem(faixa=(34, 9)):
    """`perdido` faltava, e um funil com um degrau sempre vazio parece defeito
    de código — não retrato do processo."""
    total, ganhos = faixa
    assert set(_statuses(total, ganhos)) == set(StatusLead)


@pytest.mark.parametrize("total,ganhos", [(c[3], c[4]) for cs in CLIENTES.values() for c in cs])
def test_toda_campanha_da_semente_tem_os_cinco_estagios(total: int, ganhos: int):
    """Vale para cada campanha do `CLIENTES`, não só para uma escolhida a dedo:
    a menor tem 19 leads, e é nela que uma fatia mal dimensionada zeraria um
    estágio."""
    assert set(_statuses(total, ganhos)) == set(StatusLead)


def test_a_contagem_de_ganhos_e_exatamente_a_pedida(total=51, ganhos=18):
    """O número de ganhos alimenta a taxa de conversão da demo. Se a fatia
    escorregar, os números da tela deixam de bater com a tabela do seed."""
    assert _statuses(total, ganhos).count(StatusLead.GANHO) == ganhos


def test_os_desfechos_fechados_vem_antes_dos_novos():
    """A ordem é o que faz a data sair de graça: como o `criado_em` cresce com
    o índice, ganho e perdido ficam no passado e `novo` fica na semana que
    passou. Sortear status e data de forma independente produziria lead ganho
    ontem e lead novo de dois meses atrás."""
    statuses = _statuses(40, 11)
    ultimo_fechado = max(
        i for i, s in enumerate(statuses) if s in (StatusLead.GANHO, StatusLead.PERDIDO)
    )
    primeiro_novo = min(i for i, s in enumerate(statuses) if s is StatusLead.NOVO)
    assert ultimo_fechado < primeiro_novo


# --- as datas ---

def test_as_datas_cobrem_a_campanha_inteira_em_ordem():
    inicio = HOJE - timedelta(days=60)
    aleatorio = Random(42)
    datas = [data_do_lead(i, 30, inicio, HOJE, aleatorio).date() for i in range(30)]

    assert datas == sorted(datas), "a data tem que crescer com o índice"
    assert datas[0] == inicio
    assert datas[-1] == HOJE


def test_nenhum_lead_nasce_no_futuro():
    """O último lead cai em `hoje` com hora sorteada, que pode ser depois de
    agora. Carimbo no futuro sujaria qualquer filtro de período."""
    from app.models import agora

    inicio = date.today() - timedelta(days=10)
    aleatorio = Random(42)
    datas = [data_do_lead(i, 20, inicio, date.today(), aleatorio) for i in range(20)]
    assert max(datas) <= agora()


def test_campanha_de_um_lead_so_nao_divide_por_zero():
    """`total - 1` no denominador: com um lead só, a divisão seria por zero."""
    inicio = HOJE - timedelta(days=30)
    assert data_do_lead(0, 1, inicio, HOJE, Random(42)).date() == inicio


def test_campanha_que_comeca_hoje_nao_estoura():
    """`hoje - inicio` é zero, e todos os leads caem no mesmo dia — sem erro."""
    datas = [data_do_lead(i, 5, HOJE, HOJE, Random(42)).date() for i in range(5)]
    assert datas == [HOJE] * 5


# --- a marca de versão ---

def test_banco_novo_reporta_versao_zero(sessao: Session):
    """Zero é o que um banco nunca semeado deve dizer — e é o que faz o
    primeiro boot semear em vez de achar que já está em dia."""
    assert versao_no_banco(sessao) == 0


def test_marcar_deixa_uma_linha_so(sessao: Session):
    """Isto é um marcador, não um histórico: duas marcas com números
    diferentes fariam `versao_no_banco` depender da ordem de leitura."""
    marcar(sessao)
    marcar(sessao)
    sessao.commit()
    assert sessao.scalars(select(Semente)).all().__len__() == 1
    assert versao_no_banco(sessao) == VERSAO_SEMENTE


def test_limpar_demo_leva_campanhas_e_leads_junto(sessao: Session):
    cliente = Cliente(nome=next(iter(CLIENTES)))
    sessao.add(cliente)
    sessao.flush()
    campanha = Campanha(
        cliente_id=cliente.id,
        nome="Campanha",
        canal=Canal.GOOGLE_ADS,
        investimento_centavos=1000,
        inicio=date(2026, 8, 1),
    )
    sessao.add(campanha)
    sessao.flush()
    sessao.add(Lead(campanha_id=campanha.id, nome="Lead", status=StatusLead.NOVO))
    sessao.commit()

    assert limpar_demo(sessao) == 1
    sessao.commit()

    assert sessao.scalars(select(Cliente)).all() == []
    assert sessao.scalars(select(Campanha)).all() == [], "campanha órfã sobreviveu"
    assert sessao.scalars(select(Lead)).all() == [], "lead órfão sobreviveu"


def test_limpar_demo_nao_toca_no_que_o_visitante_criou(sessao: Session):
    """A demo é pública e tem cadastro na tela. Refazer os dados de exemplo não
    pode levar junto o cliente que um visitante cadastrou."""
    sessao.add(Cliente(nome=next(iter(CLIENTES))))
    sessao.add(Cliente(nome="Cliente de um visitante"))
    sessao.commit()

    assert limpar_demo(sessao) == 1
    sessao.commit()

    restantes = [c.nome for c in sessao.scalars(select(Cliente))]
    assert restantes == ["Cliente de um visitante"]
