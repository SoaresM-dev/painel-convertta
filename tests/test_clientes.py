from __future__ import annotations

from fastapi.testclient import TestClient


def test_cria_e_lista(autenticado: TestClient):
    assert autenticado.post("/api/clientes", json={"nome": "Padaria do Zé"}).status_code == 201
    nomes = [c["nome"] for c in autenticado.get("/api/clientes").json()]
    assert nomes == ["Padaria do Zé"]


def test_nome_repetido_da_conflito(autenticado: TestClient):
    autenticado.post("/api/clientes", json={"nome": "Padaria do Zé"})
    assert autenticado.post("/api/clientes", json={"nome": "Padaria do Zé"}).status_code == 409


def test_nome_curto_demais_e_recusado(autenticado: TestClient):
    assert autenticado.post("/api/clientes", json={"nome": "x"}).status_code == 422


def test_apagar_cliente_leva_campanhas_e_leads_junto(autenticado: TestClient):
    """Cascata: cliente apagado não pode deixar campanha órfã contando
    investimento no resumo."""
    cliente = autenticado.post("/api/clientes", json={"nome": "Ótica Vista"}).json()
    campanha = autenticado.post(
        "/api/campanhas",
        json={
            "cliente_id": cliente["id"],
            "nome": "Institucional",
            "canal": "meta_ads",
            "investimento_centavos": 50000,
            "inicio": "2026-08-01",
        },
    ).json()
    autenticado.post("/api/leads", json={"campanha_id": campanha["id"], "nome": "Ana"})

    assert autenticado.delete(f"/api/clientes/{cliente['id']}").status_code == 204
    assert autenticado.get("/api/campanhas").json() == []
    assert autenticado.get("/api/leads").json() == []


def test_apagar_cliente_que_nao_existe_da_404(autenticado: TestClient):
    assert autenticado.delete("/api/clientes/999").status_code == 404
