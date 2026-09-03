"""A porta. Se ela falhar, o resto não importa."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.conftest import EMAIL_DEMO, SENHA_DEMO

ROTAS_FECHADAS = [
    ("get", "/api/clientes"),
    ("post", "/api/clientes"),
    ("get", "/api/campanhas"),
    ("post", "/api/campanhas"),
    ("get", "/api/leads"),
    ("post", "/api/leads"),
    ("get", "/api/painel/resumo"),
]


@pytest.mark.parametrize("metodo,caminho", ROTAS_FECHADAS)
def test_nenhuma_rota_de_dados_responde_sem_token(cliente_http: TestClient, metodo, caminho):
    """Enumerado de propósito: uma rota nova que esquecer a dependência de
    usuário passa a existir sem entrar nesta lista, e o teste da linha
    seguinte é quem cobra isso."""
    assert getattr(cliente_http, metodo)(caminho).status_code == 401


def test_a_lista_acima_cobre_todas_as_rotas_de_dados(cliente_http: TestClient):
    """Trava contra o esquecimento: se alguém adicionar uma rota `/api/` e não
    a listar aqui, este teste reprova e mostra qual ficou de fora."""
    from app.main import app

    publicas = {"/api/saude", "/api/auth/token", "/api/auth/eu"}
    declaradas = {caminho for _metodo, caminho in ROTAS_FECHADAS}
    do_app = {
        rota.path
        for rota in app.routes
        if getattr(rota, "path", "").startswith("/api/") and "{" not in rota.path
    }
    faltando = do_app - publicas - declaradas
    assert not faltando, f"rotas sem teste de autenticação: {sorted(faltando)}"


def test_login_com_senha_certa_devolve_token(cliente_http: TestClient, usuario):
    resposta = cliente_http.post(
        "/api/auth/token", data={"username": EMAIL_DEMO, "password": SENHA_DEMO}
    )
    assert resposta.status_code == 200
    assert resposta.json()["access_token"]


def test_login_com_senha_errada_recusa(cliente_http: TestClient, usuario):
    resposta = cliente_http.post(
        "/api/auth/token", data={"username": EMAIL_DEMO, "password": "errada"}
    )
    assert resposta.status_code == 401


def test_email_inexistente_e_senha_errada_dao_a_mesma_resposta(cliente_http: TestClient, usuario):
    """Respostas diferentes contariam a quem tenta invadir quais e-mails
    existem no sistema."""
    inexistente = cliente_http.post(
        "/api/auth/token", data={"username": "ninguem@convertta.com.br", "password": "x"}
    )
    errada = cliente_http.post(
        "/api/auth/token", data={"username": EMAIL_DEMO, "password": "x"}
    )
    assert inexistente.status_code == errada.status_code == 401
    assert inexistente.json() == errada.json()


def test_token_invalido_e_recusado(cliente_http: TestClient, usuario):
    cliente_http.headers["Authorization"] = "Bearer isto-nao-e-um-token"
    assert cliente_http.get("/api/clientes").status_code == 401


def test_a_senha_nunca_volta_pela_api(autenticado: TestClient):
    corpo = autenticado.get("/api/auth/eu").json()
    assert "senha_hash" not in corpo and "senha" not in corpo
    assert corpo["email"] == EMAIL_DEMO


def test_a_senha_guardada_nao_e_a_senha(usuario):
    """Vazamento do banco não pode devolver senha de ninguém."""
    assert usuario.senha_hash != SENHA_DEMO
    assert usuario.senha_hash.startswith("$2")  # prefixo do bcrypt
