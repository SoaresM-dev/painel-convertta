from __future__ import annotations

from fastapi.testclient import TestClient


def _cliente(autenticado: TestClient, nome: str = "Padaria do Zé") -> int:
    return autenticado.post("/api/clientes", json={"nome": nome}).json()["id"]


def _payload(cliente_id: int, **extra) -> dict:
    base = {
        "cliente_id": cliente_id,
        "nome": "Black Friday",
        "canal": "google_ads",
        "investimento_centavos": 120000,
        "inicio": "2026-08-01",
    }
    base.update(extra)
    return base


def test_cria_campanha(autenticado: TestClient):
    resposta = autenticado.post("/api/campanhas", json=_payload(_cliente(autenticado)))
    assert resposta.status_code == 201
    assert resposta.json()["investimento_centavos"] == 120000


def test_cliente_inexistente_da_404(autenticado: TestClient):
    assert autenticado.post("/api/campanhas", json=_payload(999)).status_code == 404


def test_investimento_negativo_e_recusado(autenticado: TestClient):
    """Investimento negativo tornaria o custo por lead negativo, e o painel
    inteiro deixaria de fazer sentido."""
    corpo = _payload(_cliente(autenticado), investimento_centavos=-1)
    assert autenticado.post("/api/campanhas", json=corpo).status_code == 422


def test_fim_antes_do_inicio_e_recusado(autenticado: TestClient):
    corpo = _payload(_cliente(autenticado), inicio="2026-08-10", fim="2026-08-01")
    assert autenticado.post("/api/campanhas", json=corpo).status_code == 422


def test_canal_desconhecido_e_recusado(autenticado: TestClient):
    corpo = _payload(_cliente(autenticado), canal="tiktok_ads")
    assert autenticado.post("/api/campanhas", json=corpo).status_code == 422


def test_mesmo_nome_no_mesmo_cliente_da_conflito(autenticado: TestClient):
    cliente_id = _cliente(autenticado)
    autenticado.post("/api/campanhas", json=_payload(cliente_id))
    assert autenticado.post("/api/campanhas", json=_payload(cliente_id)).status_code == 409


def test_mesmo_nome_em_clientes_diferentes_e_permitido(autenticado: TestClient):
    """Duas agências rodando "Black Friday" é o caso normal, não o erro."""
    a = _cliente(autenticado, "Padaria do Zé")
    b = _cliente(autenticado, "Ótica Vista")
    assert autenticado.post("/api/campanhas", json=_payload(a)).status_code == 201
    assert autenticado.post("/api/campanhas", json=_payload(b)).status_code == 201


def test_filtra_por_cliente(autenticado: TestClient):
    a = _cliente(autenticado, "Padaria do Zé")
    b = _cliente(autenticado, "Ótica Vista")
    autenticado.post("/api/campanhas", json=_payload(a, nome="Alfa"))
    autenticado.post("/api/campanhas", json=_payload(b, nome="Beta"))
    nomes = [c["nome"] for c in autenticado.get(f"/api/campanhas?cliente_id={a}").json()]
    assert nomes == ["Alfa"]
