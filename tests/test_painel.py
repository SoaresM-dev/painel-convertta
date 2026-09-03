"""O resumo é o número que o cliente da agência vê. Errar aqui é o defeito
mais caro do sistema — por isso é o arquivo com mais teste."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.rotas.painel import custo_por_lead


def _montar(autenticado: TestClient, cliente: str, investimento: int, leads: int, ganhos: int = 0):
    cliente_id = autenticado.post("/api/clientes", json={"nome": cliente}).json()["id"]
    campanha_id = autenticado.post(
        "/api/campanhas",
        json={
            "cliente_id": cliente_id,
            "nome": f"Campanha {cliente}",
            "canal": "google_ads",
            "investimento_centavos": investimento,
            "inicio": "2026-08-01",
        },
    ).json()["id"]
    for i in range(leads):
        lead = autenticado.post(
            "/api/leads", json={"campanha_id": campanha_id, "nome": f"Lead {i}"}
        ).json()
        if i < ganhos:
            autenticado.patch(f"/api/leads/{lead['id']}", json={"status": "ganho"})
    return cliente_id, campanha_id


# --- a conta, isolada ---

@pytest.mark.parametrize(
    "investimento,leads,esperado",
    [
        (120000, 10, 12000),   # R$ 1.200 / 10 = R$ 120,00
        (100000, 3, 33333),    # arredonda, não trunca
        (0, 5, 0),             # campanha sem investimento é custo zero de verdade
        (120000, 0, None),     # sem lead não há custo por lead
    ],
)
def test_custo_por_lead(investimento, leads, esperado):
    assert custo_por_lead(investimento, leads) == esperado


def test_sem_lead_o_custo_e_desconhecido_e_nao_zero(autenticado: TestClient):
    """R$ 0,00 leria como "conseguimos leads de graça". `None` diz a verdade:
    ainda não dá para saber."""
    _montar(autenticado, "Padaria do Zé", investimento=120000, leads=0)
    linha = autenticado.get("/api/painel/resumo").json()["linhas"][0]
    assert linha["custo_por_lead_centavos"] is None
    assert linha["taxa_conversao"] is None


# --- o resumo inteiro ---

def test_resumo_vazio(autenticado: TestClient):
    corpo = autenticado.get("/api/painel/resumo").json()
    assert corpo == {
        "investimento_centavos": 0,
        "leads": 0,
        "leads_ganhos": 0,
        "custo_por_lead_centavos": None,
        "linhas": [],
    }


def test_cliente_sem_campanha_aparece_zerado(autenticado: TestClient):
    """Cliente novo tem que aparecer na lista, não sumir até ter campanha."""
    autenticado.post("/api/clientes", json={"nome": "Ótica Vista"})
    linha = autenticado.get("/api/painel/resumo").json()["linhas"][0]
    assert (linha["campanhas"], linha["investimento_centavos"], linha["leads"]) == (0, 0, 0)


def test_uma_campanha_com_leads(autenticado: TestClient):
    _montar(autenticado, "Padaria do Zé", investimento=120000, leads=10, ganhos=3)
    linha = autenticado.get("/api/painel/resumo").json()["linhas"][0]
    assert linha["leads"] == 10
    assert linha["leads_ganhos"] == 3
    assert linha["custo_por_lead_centavos"] == 12000
    assert linha["taxa_conversao"] == 0.3


def test_duas_campanhas_nao_multiplicam_o_investimento(autenticado: TestClient):
    """**O teste que justifica a subconsulta.** Juntar campanhas e leads no
    mesmo `join` multiplicaria o investimento de cada campanha pelo número de
    leads dela: 1.200 + 800 viraria 1.200x2 + 800x3. Erro de fan-out, e do
    tipo que só aparece depois de o número já ter sido mostrado ao cliente."""
    cliente_id = autenticado.post("/api/clientes", json={"nome": "Padaria do Zé"}).json()["id"]
    for nome, investimento, leads in (("Alfa", 120000, 2), ("Beta", 80000, 3)):
        campanha_id = autenticado.post(
            "/api/campanhas",
            json={
                "cliente_id": cliente_id,
                "nome": nome,
                "canal": "meta_ads",
                "investimento_centavos": investimento,
                "inicio": "2026-08-01",
            },
        ).json()["id"]
        for i in range(leads):
            autenticado.post("/api/leads", json={"campanha_id": campanha_id, "nome": f"{nome}{i}"})

    linha = autenticado.get("/api/painel/resumo").json()["linhas"][0]
    assert linha["campanhas"] == 2
    assert linha["investimento_centavos"] == 200000, "investimento multiplicado por leads"
    assert linha["leads"] == 5
    assert linha["custo_por_lead_centavos"] == 40000


def test_totais_somam_os_clientes_e_saem_em_ordem_alfabetica(autenticado: TestClient):
    _montar(autenticado, "Ótica Vista", investimento=80000, leads=4, ganhos=1)
    _montar(autenticado, "Padaria do Zé", investimento=120000, leads=6, ganhos=2)

    corpo = autenticado.get("/api/painel/resumo").json()
    assert [linha["cliente"] for linha in corpo["linhas"]] == ["Padaria do Zé", "Ótica Vista"]
    assert corpo["investimento_centavos"] == 200000
    assert corpo["leads"] == 10
    assert corpo["leads_ganhos"] == 3
    assert corpo["custo_por_lead_centavos"] == 20000
