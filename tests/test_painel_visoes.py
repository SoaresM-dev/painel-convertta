"""As três visões que o painel ganhou: canal, funil e série — e o drill-down.

Todas leem dado que já estava no banco desde o primeiro commit e que nenhuma
tela mostrava: `Campanha.canal`, os cinco estágios de `Lead.status` e o
`Lead.criado_em`.
"""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Lead, StatusLead


def _cliente(autenticado: TestClient, nome: str) -> int:
    return autenticado.post("/api/clientes", json={"nome": nome}).json()["id"]


def _campanha(
    autenticado: TestClient,
    cliente_id: int,
    nome: str,
    canal: str = "google_ads",
    investimento: int = 90000,
    inicio: str = "2026-08-01",
    fim: str | None = "2026-08-10",
) -> int:
    corpo = {
        "cliente_id": cliente_id,
        "nome": nome,
        "canal": canal,
        "investimento_centavos": investimento,
        "inicio": inicio,
    }
    if fim is not None:
        corpo["fim"] = fim
    return autenticado.post("/api/campanhas", json=corpo).json()["id"]


def _lead_em(sessao: Session, campanha_id: int, quando: date, status=StatusLead.NOVO) -> None:
    sessao.add(
        Lead(
            campanha_id=campanha_id,
            nome=f"Lead {quando.isoformat()} {status}",
            status=status,
            criado_em=datetime.combine(quando, datetime.min.time(), tzinfo=UTC)
            + timedelta(hours=12),
        )
    )
    sessao.commit()


# --- canais ---

def test_canais_saem_sempre_os_dois_mesmo_zerados(autenticado: TestClient):
    """Barra ausente lê-se como "não existe", e não como "não teve
    investimento neste recorte"."""
    corpo = autenticado.get("/api/painel/canais").json()
    assert [linha["canal"] for linha in corpo] == ["google_ads", "meta_ads"]
    assert all(linha["investimento_centavos"] == 0 for linha in corpo)
    assert all(linha["custo_por_lead_centavos"] is None for linha in corpo)


def test_canais_separam_investimento_e_leads(autenticado: TestClient, sessao: Session):
    cliente_id = _cliente(autenticado, "Padaria do Zé")
    google = _campanha(autenticado, cliente_id, "Busca", "google_ads", investimento=120000)
    meta = _campanha(autenticado, cliente_id, "Feed", "meta_ads", investimento=60000)

    for _ in range(4):
        _lead_em(sessao, google, date(2026, 8, 5))
    for _ in range(6):
        _lead_em(sessao, meta, date(2026, 8, 5), StatusLead.GANHO)

    por_canal = {linha["canal"]: linha for linha in autenticado.get("/api/painel/canais").json()}

    assert por_canal["google_ads"]["investimento_centavos"] == 120000
    assert por_canal["google_ads"]["leads"] == 4
    assert por_canal["google_ads"]["custo_por_lead_centavos"] == 30000
    assert por_canal["google_ads"]["taxa_conversao"] == 0.0

    assert por_canal["meta_ads"]["investimento_centavos"] == 60000
    assert por_canal["meta_ads"]["leads"] == 6
    assert por_canal["meta_ads"]["custo_por_lead_centavos"] == 10000
    assert por_canal["meta_ads"]["taxa_conversao"] == 1.0


def test_canais_respeitam_o_periodo(autenticado: TestClient, sessao: Session):
    cliente_id = _cliente(autenticado, "Padaria do Zé")
    google = _campanha(autenticado, cliente_id, "Busca", "google_ads", inicio="2026-06-01",
                       fim="2026-06-30")
    _lead_em(sessao, google, date(2026, 6, 10))

    por_canal = {
        linha["canal"]: linha
        for linha in autenticado.get("/api/painel/canais", params={"de": "2026-08-01"}).json()
    }
    assert por_canal["google_ads"]["campanhas"] == 0
    assert por_canal["google_ads"]["leads"] == 0


# --- funil ---

def test_funil_traz_os_cinco_estagios_na_ordem(autenticado: TestClient):
    corpo = autenticado.get("/api/painel/funil").json()
    assert [e["status"] for e in corpo["estagios"]] == [
        "novo",
        "contatado",
        "qualificado",
        "ganho",
        "perdido",
    ]
    assert corpo["total"] == 0


def test_estagio_vazio_vem_com_zero_e_nao_some(autenticado: TestClient, sessao: Session):
    """O degrau vazio é justamente onde o processo está travando. Omitir a
    linha esconde a informação que o funil existe para dar."""
    cliente_id = _cliente(autenticado, "Padaria do Zé")
    campanha_id = _campanha(autenticado, cliente_id, "Busca")
    for status in (StatusLead.NOVO, StatusLead.NOVO, StatusLead.GANHO, StatusLead.PERDIDO):
        _lead_em(sessao, campanha_id, date(2026, 8, 5), status)

    corpo = autenticado.get("/api/painel/funil").json()
    por_status = {e["status"]: e["leads"] for e in corpo["estagios"]}

    assert por_status == {"novo": 2, "contatado": 0, "qualificado": 0, "ganho": 1, "perdido": 1}
    assert corpo["total"] == 4


def test_funil_respeita_o_periodo(autenticado: TestClient, sessao: Session):
    cliente_id = _cliente(autenticado, "Padaria do Zé")
    campanha_id = _campanha(autenticado, cliente_id, "Busca", inicio="2026-06-01", fim=None)
    _lead_em(sessao, campanha_id, date(2026, 6, 10), StatusLead.GANHO)
    _lead_em(sessao, campanha_id, date(2026, 8, 10), StatusLead.NOVO)

    corpo = autenticado.get("/api/painel/funil", params={"de": "2026-08-01"}).json()
    assert corpo["total"] == 1
    assert {e["status"]: e["leads"] for e in corpo["estagios"]}["ganho"] == 0


# --- série ---

def test_serie_vazia_quando_nao_ha_lead(autenticado: TestClient):
    assert autenticado.get("/api/painel/serie").json() == {"pontos": []}


def test_serie_preenche_o_dia_sem_lead_com_zero(autenticado: TestClient, sessao: Session):
    """Omitir o dia vazio faz a linha ligar dois pontos distantes como se
    fossem vizinhos — e a queda some do desenho justamente quando ela é a
    informação."""
    cliente_id = _cliente(autenticado, "Padaria do Zé")
    campanha_id = _campanha(autenticado, cliente_id, "Busca", inicio="2026-08-01")
    _lead_em(sessao, campanha_id, date(2026, 8, 10))
    _lead_em(sessao, campanha_id, date(2026, 8, 13), StatusLead.GANHO)

    corpo = autenticado.get(
        "/api/painel/serie", params={"de": "2026-08-10", "ate": "2026-08-13"}
    ).json()

    assert [p["dia"] for p in corpo["pontos"]] == [
        "2026-08-10",
        "2026-08-11",
        "2026-08-12",
        "2026-08-13",
    ]
    assert [p["leads"] for p in corpo["pontos"]] == [1, 0, 0, 1]
    assert [p["leads_ganhos"] for p in corpo["pontos"]] == [0, 0, 0, 1]


def test_serie_nao_preenche_antes_do_primeiro_lead(autenticado: TestClient, sessao: Session):
    """`?de=1900-01-01` não pode mandar a API desenhar quarenta mil zeros."""
    cliente_id = _cliente(autenticado, "Padaria do Zé")
    campanha_id = _campanha(autenticado, cliente_id, "Busca", inicio="2026-08-01")
    _lead_em(sessao, campanha_id, date(2026, 8, 10))

    corpo = autenticado.get(
        "/api/painel/serie", params={"de": "1900-01-01", "ate": "2026-08-10"}
    ).json()
    assert corpo["pontos"] == [{"dia": "2026-08-10", "leads": 1, "leads_ganhos": 0}]


# --- drill-down ---

def test_detalhe_de_cliente_inexistente_e_404(autenticado: TestClient):
    assert autenticado.get("/api/painel/clientes/9999").status_code == 404


def test_detalhe_traz_campanhas_com_custo_proprio_e_leads_recentes(
    autenticado: TestClient, sessao: Session
):
    cliente_id = _cliente(autenticado, "Padaria do Zé")
    busca = _campanha(autenticado, cliente_id, "Busca", "google_ads", investimento=120000)
    feed = _campanha(autenticado, cliente_id, "Feed", "meta_ads", investimento=60000)

    for _ in range(4):
        _lead_em(sessao, busca, date(2026, 8, 5))
    _lead_em(sessao, feed, date(2026, 8, 7), StatusLead.GANHO)

    corpo = autenticado.get(f"/api/painel/clientes/{cliente_id}").json()
    assert corpo["cliente"] == "Padaria do Zé"

    por_nome = {c["nome"]: c for c in corpo["campanhas"]}
    assert por_nome["Busca"]["custo_por_lead_centavos"] == 30000
    assert por_nome["Feed"]["custo_por_lead_centavos"] == 60000
    assert por_nome["Feed"]["taxa_conversao"] == 1.0

    # O mais recente primeiro, e cada lead sabe de que campanha veio.
    assert corpo["leads_recentes"][0]["campanha"] == "Feed"
    assert len(corpo["leads_recentes"]) == 5


def test_detalhe_limita_os_leads_recentes(autenticado: TestClient, sessao: Session):
    """A lista é uma amostra, não um export: sem limite, um cliente com dez mil
    leads derruba a tela e a resposta."""
    cliente_id = _cliente(autenticado, "Padaria do Zé")
    campanha_id = _campanha(autenticado, cliente_id, "Busca")
    for dia in range(1, 26):
        _lead_em(sessao, campanha_id, date(2026, 8, 1) + timedelta(days=dia))

    corpo = autenticado.get(f"/api/painel/clientes/{cliente_id}").json()
    assert len(corpo["leads_recentes"]) == 20


def test_campanha_fora_do_recorte_some_do_detalhe(autenticado: TestClient):
    """No resumo o cliente continua na lista zerado — mas no detalhe dele, uma
    campanha que não encosta no recorte não tem linha para ocupar."""
    cliente_id = _cliente(autenticado, "Padaria do Zé")
    _campanha(autenticado, cliente_id, "Antiga", inicio="2026-06-01", fim="2026-06-30")

    corpo = autenticado.get(
        f"/api/painel/clientes/{cliente_id}", params={"de": "2026-08-01"}
    ).json()
    assert corpo["campanhas"] == []


# --- a trava de sempre ---

def test_as_visoes_novas_recusam_anonimo(cliente_http: TestClient):
    """Rota nova é a forma mais comum de furar autenticação por esquecimento."""
    for caminho in ("/api/painel/canais", "/api/painel/funil", "/api/painel/serie",
                    "/api/painel/clientes/1"):
        assert cliente_http.get(caminho).status_code == 401, caminho
