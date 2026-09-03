from __future__ import annotations

from fastapi.testclient import TestClient


def _campanha(autenticado: TestClient, nome_cliente: str = "Padaria do Zé", **extra) -> int:
    cliente_id = autenticado.post("/api/clientes", json={"nome": nome_cliente}).json()["id"]
    corpo = {
        "cliente_id": cliente_id,
        "nome": extra.pop("nome", "Black Friday"),
        "canal": "google_ads",
        "investimento_centavos": extra.pop("investimento_centavos", 120000),
        "inicio": "2026-08-01",
    }
    return autenticado.post("/api/campanhas", json=corpo).json()["id"]


def test_cria_lead_com_status_novo_por_padrao(autenticado: TestClient):
    campanha_id = _campanha(autenticado)
    resposta = autenticado.post(
        "/api/leads", json={"campanha_id": campanha_id, "nome": "Ana Souza"}
    )
    assert resposta.status_code == 201
    assert resposta.json()["status"] == "novo"


def test_campanha_inexistente_da_404(autenticado: TestClient):
    resposta = autenticado.post("/api/leads", json={"campanha_id": 999, "nome": "Ana"})
    assert resposta.status_code == 404


def test_email_invalido_e_recusado(autenticado: TestClient):
    campanha_id = _campanha(autenticado)
    corpo = {"campanha_id": campanha_id, "nome": "Ana", "email": "isto-nao-e-email"}
    assert autenticado.post("/api/leads", json=corpo).status_code == 422


def test_muda_status(autenticado: TestClient):
    campanha_id = _campanha(autenticado)
    lead = autenticado.post("/api/leads", json={"campanha_id": campanha_id, "nome": "Ana"}).json()
    resposta = autenticado.patch(f"/api/leads/{lead['id']}", json={"status": "ganho"})
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "ganho"


def test_status_desconhecido_e_recusado(autenticado: TestClient):
    campanha_id = _campanha(autenticado)
    lead = autenticado.post("/api/leads", json={"campanha_id": campanha_id, "nome": "Ana"}).json()
    resposta = autenticado.patch(f"/api/leads/{lead['id']}", json={"status": "talvez"})
    assert resposta.status_code == 422


def test_filtra_por_campanha(autenticado: TestClient):
    a = _campanha(autenticado, "Padaria do Zé")
    b = _campanha(autenticado, "Ótica Vista")
    autenticado.post("/api/leads", json={"campanha_id": a, "nome": "Ana"})
    autenticado.post("/api/leads", json={"campanha_id": b, "nome": "Bruno"})
    nomes = [linha["nome"] for linha in autenticado.get(f"/api/leads?campanha_id={a}").json()]
    assert nomes == ["Ana"]
