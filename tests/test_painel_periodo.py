"""O filtro de período, e o rateio que ele obriga.

O recorte de tempo não é enfeite de tela: ele muda o número. Um investimento
de 90 dias contado inteiro dentro de uma semana faria o custo por lead da
semana parecer treze vezes maior — e esse é o número que a agência mostra
para o cliente.
"""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Lead, StatusLead
from app.rotas.painel import Periodo, dias_dentro, rateio

HOJE = date(2026, 9, 4)


def _campanha(autenticado: TestClient, inicio: str, fim: str | None = None, investimento=90000):
    cliente_id = autenticado.post("/api/clientes", json={"nome": "Padaria do Zé"}).json()["id"]
    corpo = {
        "cliente_id": cliente_id,
        "nome": "Campanha",
        "canal": "google_ads",
        "investimento_centavos": investimento,
        "inicio": inicio,
    }
    if fim is not None:
        corpo["fim"] = fim
    return cliente_id, autenticado.post("/api/campanhas", json=corpo).json()["id"]


def _lead_em(sessao: Session, campanha_id: int, quando: date, status=StatusLead.NOVO) -> Lead:
    """Insere um lead com data no passado.

    Pela API isso é impossível de propósito — `LeadEntrada` não aceita
    `criado_em`, então nenhum cliente da rede escolhe o carimbo de tempo do
    próprio registro. O teste escreve direto na sessão porque é o teste que
    precisa fabricar o passado, não a API.
    """
    lead = Lead(
        campanha_id=campanha_id,
        nome=f"Lead {quando.isoformat()}",
        status=status,
        criado_em=datetime.combine(quando, datetime.min.time(), tzinfo=UTC) + timedelta(hours=12),
    )
    sessao.add(lead)
    sessao.commit()
    return lead


# --- a aritmética de datas, sem banco no meio ---

@pytest.mark.parametrize(
    "inicio,fim,de,ate,esperado_dentro,esperado_total",
    [
        # campanha inteira dentro do recorte
        (date(2026, 8, 1), date(2026, 8, 10), date(2026, 7, 1), date(2026, 9, 1), 10, 10),
        # recorte cobre metade
        (date(2026, 8, 1), date(2026, 8, 10), date(2026, 8, 6), None, 5, 10),
        # recorte não encosta na campanha
        (date(2026, 8, 1), date(2026, 8, 10), date(2026, 8, 20), None, 0, 10),
        # sem recorte nenhum: tudo dentro
        (date(2026, 8, 1), date(2026, 8, 10), None, None, 10, 10),
        # campanha de um dia dura 1, não 0 — os dois lados são inclusivos
        (date(2026, 8, 1), date(2026, 8, 1), None, None, 1, 1),
    ],
)
def test_dias_dentro(inicio, fim, de, ate, esperado_dentro, esperado_total):
    assert dias_dentro(inicio, fim, Periodo(de, ate), HOJE) == (esperado_dentro, esperado_total)


def test_campanha_sem_fim_vale_ate_hoje():
    """`fim = None` é campanha no ar. Tratá-la como campanha de um dia faria o
    rateio devolver o investimento inteiro em qualquer recorte."""
    dentro, total = dias_dentro(date(2026, 9, 1), None, Periodo(), HOJE)
    assert (dentro, total) == (4, 4)


@pytest.mark.parametrize(
    "investimento,dentro,total,esperado",
    [
        (90000, 10, 10, 90000),  # recorte cobre tudo: valor cheio, sem arredondar
        (90000, 5, 10, 45000),   # metade
        (90000, 0, 10, 0),       # fora do recorte: zero, não proporcional a nada
        (100000, 1, 3, 33333),   # arredonda, não trunca
        (90000, 20, 10, 90000),  # dentro maior que o total nunca ultrapassa o valor cheio
    ],
)
def test_rateio(investimento, dentro, total, esperado):
    assert rateio(investimento, dentro, total) == esperado


# --- o filtro atravessando a API ---

def test_periodo_invertido_e_recusado(autenticado: TestClient):
    resposta = autenticado.get(
        "/api/painel/resumo", params={"de": "2026-09-10", "ate": "2026-09-01"}
    )
    assert resposta.status_code == 422


def test_lead_fora_do_periodo_nao_e_contado(autenticado: TestClient, sessao: Session):
    _, campanha_id = _campanha(autenticado, inicio="2026-06-01")
    _lead_em(sessao, campanha_id, date(2026, 6, 15))
    _lead_em(sessao, campanha_id, date(2026, 8, 20))
    _lead_em(sessao, campanha_id, date(2026, 8, 25))

    corpo = autenticado.get(
        "/api/painel/resumo", params={"de": "2026-08-01", "ate": "2026-08-31"}
    ).json()
    assert corpo["leads"] == 2, "o lead de junho entrou num recorte de agosto"

    assert autenticado.get("/api/painel/resumo").json()["leads"] == 3


def test_o_ultimo_dia_do_recorte_entra(autenticado: TestClient, sessao: Session):
    """O defeito silencioso que o `< meia-noite do dia seguinte` existe para
    evitar: com `<=`, o dia do limite superior some inteiro do relatório."""
    _, campanha_id = _campanha(autenticado, inicio="2026-08-01")
    _lead_em(sessao, campanha_id, date(2026, 8, 31))

    corpo = autenticado.get(
        "/api/painel/resumo", params={"de": "2026-08-01", "ate": "2026-08-31"}
    ).json()
    assert corpo["leads"] == 1


def test_investimento_e_rateado_pelo_recorte(autenticado: TestClient):
    """Campanha de 10 dias, R$ 900,00. Um recorte de 5 dias vale R$ 450,00."""
    _campanha(autenticado, inicio="2026-08-01", fim="2026-08-10", investimento=90000)

    corpo = autenticado.get(
        "/api/painel/resumo", params={"de": "2026-08-01", "ate": "2026-08-05"}
    ).json()
    assert corpo["investimento_centavos"] == 45000
    assert corpo["linhas"][0]["investimento_centavos"] == 45000


def test_campanha_fora_do_recorte_nao_conta_e_o_cliente_continua_na_lista(
    autenticado: TestClient,
):
    """Cliente que some da tela quando o filtro aperta é cliente que o usuário
    acha que foi apagado."""
    _campanha(autenticado, inicio="2026-08-01", fim="2026-08-10")

    corpo = autenticado.get("/api/painel/resumo", params={"de": "2026-09-01"}).json()
    assert len(corpo["linhas"]) == 1
    assert corpo["linhas"][0]["campanhas"] == 0
    assert corpo["investimento_centavos"] == 0
    assert corpo["custo_por_lead_centavos"] is None


def test_sem_recorte_o_investimento_sai_inteiro(autenticado: TestClient):
    """A regressão que o rateio poderia introduzir: arredondar um valor que
    não precisava ser dividido."""
    _campanha(autenticado, inicio="2026-08-01", fim="2026-08-10", investimento=100000)
    assert autenticado.get("/api/painel/resumo").json()["investimento_centavos"] == 100000
