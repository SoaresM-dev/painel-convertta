"""Popula o banco com a conta demo e dados plausíveis.

**Existe para o recrutador.** Uma URL ao vivo que pede login e mostra uma tela
vazia não prova nada. Este script deixa o painel com números logo na primeira
abertura, e é idempotente: rodar duas vezes não duplica nada.

**A semente converge, não só evita duplicata.** `VERSAO_SEMENTE` é gravada no
banco; quando o número muda, os clientes de demonstração são refeitos. Sem isso
a idempotência por existência — "esta campanha já existe? então pula" — protege
contra duplicata e impede correção: a produção fica presa na primeira versão do
dado para sempre.

**Os leads têm data e têm perda.** A primeira versão deixava o `criado_em` cair
no `default=agora()` e nunca gerava `perdido`. Nenhuma das duas coisas aparecia
na tela de então — mas a série temporal viraria um pico vertical no instante do
deploy, e o funil teria um estágio permanentemente vazio. Dado de demonstração
que não sustenta o gráfico é pior que ausência de gráfico.

    python -m scripts.semear
"""
from __future__ import annotations

import random
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.db import CriarSessao, engine
from app.models import Campanha, Canal, Cliente, Lead, Semente, StatusLead, Usuario, agora
from app.seguranca import cifrar_senha

# Subir este número faz o próximo boot refazer os dados de demonstração.
# A idempotência por existência sozinha nunca corrige o que já está no banco:
# foi assim que a produção ficou com os leads todos no mesmo instante e sem
# nenhum `perdido`, mesmo depois de a semente ser consertada no código.
VERSAO_SEMENTE = 2

EMAIL_DEMO = "demo@convertta.com.br"
SENHA_DEMO = "demo1234"

CLIENTES = {
    "Padaria do Zé": [
        ("Institucional — bairro", Canal.META_ADS, 48000, 34, 9),
        ("Encomendas de festa", Canal.GOOGLE_ADS, 96000, 51, 18),
    ],
    "Ótica Vista Clara": [
        ("Lentes multifocais", Canal.GOOGLE_ADS, 180000, 62, 14),
        ("Remarketing — armações", Canal.META_ADS, 60000, 40, 11),
    ],
    "Studio Pilates Norte": [
        ("Aula experimental", Canal.META_ADS, 120000, 88, 27),
    ],
    "Advocacia Ramos": [
        ("Direito trabalhista", Canal.GOOGLE_ADS, 240000, 19, 6),
    ],
}


def status_do_lead(indice: int, total: int, ganhos: int) -> StatusLead:
    """Distribui os cinco estágios sobre os leads de uma campanha.

    A ordem importa e não é decorativa: os primeiros índices ficam com os
    desfechos fechados (`ganho`, `perdido`) e os últimos com `novo`. Como a
    data também cresce com o índice, sai de graça o padrão que existe numa
    agência de verdade — o que fechou, fechou faz tempo; o que chegou esta
    semana ainda está em `novo`. Sortear status e data de forma independente
    produziria leads ganhos ontem e leads novos de dois meses atrás.
    """
    perdidos = total // 5
    qualificados = total // 6
    contatados = total // 4

    if indice < ganhos:
        return StatusLead.GANHO
    if indice < ganhos + perdidos:
        return StatusLead.PERDIDO
    if indice < ganhos + perdidos + qualificados:
        return StatusLead.QUALIFICADO
    if indice < ganhos + perdidos + qualificados + contatados:
        return StatusLead.CONTATADO
    return StatusLead.NOVO


def data_do_lead(
    indice: int, total: int, inicio: date, hoje: date, aleatorio: random.Random
) -> datetime:
    """Espalha os leads entre o início da campanha e hoje, em ordem.

    O horário é sorteado dentro do horário comercial só para os pontos não
    caírem todos à meia-noite — a série é por dia, mas o `criado_em` aparece
    inteiro na lista de leads recentes.
    """
    dias_ativos = max((hoje - inicio).days, 0)
    dia = inicio + timedelta(days=round(dias_ativos * indice / max(total - 1, 1)))
    momento = datetime.combine(
        dia, time(hour=aleatorio.randint(8, 20), minute=aleatorio.randint(0, 59)), tzinfo=UTC
    )
    # O último lead cai em `hoje` com hora sorteada, que pode ser depois de
    # agora. Lead com carimbo no futuro sujaria qualquer filtro de período.
    return min(momento, agora())


def versao_no_banco(sessao: Session) -> int:
    """Zero quando nunca foi semeado — que é o que um banco novo deve reportar."""
    marca = sessao.scalar(select(Semente).order_by(Semente.id.desc()).limit(1))
    return 0 if marca is None else marca.versao


def limpar_demo(sessao: Session) -> int:
    """Apaga só os clientes do `CLIENTES`; campanhas e leads somem por cascata.

    Filtrar pelo nome não é preciosismo: a demo é pública e tem cadastro na
    tela, então um visitante pode ter criado cliente próprio. Apagar a tabela
    inteira levaria junto o que não é nosso.
    """
    clientes = list(sessao.scalars(select(Cliente).where(Cliente.nome.in_(CLIENTES))))
    for cliente in clientes:
        sessao.delete(cliente)
    return len(clientes)


def marcar(sessao: Session) -> None:
    """Uma linha só, sempre reescrita: isto é um marcador, não um histórico."""
    for antiga in sessao.scalars(select(Semente)):
        sessao.delete(antiga)
    sessao.flush()
    sessao.add(Semente(versao=VERSAO_SEMENTE))
    # O flush final não é enfeite: a sessão do projeto roda com `autoflush`
    # desligado, e sem ele uma segunda chamada não enxergaria a linha recém-
    # adicionada — deixaria duas marcas, e aí `versao_no_banco` passa a
    # depender da ordem de leitura.
    sessao.flush()


def semear() -> None:
    # De propósito **não** cria tabela. Quem cria esquema é o Alembic, e só
    # ele: dois donos do esquema é como se chega em produção com uma coluna
    # que existe na máquina de quem escreveu e não existe no servidor.
    if not inspect(engine).has_table("usuarios"):
        raise SystemExit("Banco sem esquema. Rode `alembic upgrade head` antes.")

    aleatorio = random.Random(42)  # semente fixa: a demo é sempre a mesma

    with CriarSessao() as sessao:
        antiga = versao_no_banco(sessao)
        if antiga != VERSAO_SEMENTE:
            removidos = limpar_demo(sessao)
            sessao.flush()
            if removidos:
                print(f"Semente v{antiga} -> v{VERSAO_SEMENTE}: {removidos} clientes refeitos.")

        if sessao.scalar(select(Usuario).where(Usuario.email == EMAIL_DEMO)) is None:
            sessao.add(
                Usuario(email=EMAIL_DEMO, nome="Conta demo", senha_hash=cifrar_senha(SENHA_DEMO))
            )

        hoje = date.today()
        for nome_cliente, campanhas in CLIENTES.items():
            cliente = sessao.scalar(select(Cliente).where(Cliente.nome == nome_cliente))
            if cliente is None:
                cliente = Cliente(nome=nome_cliente)
                sessao.add(cliente)
                sessao.flush()

            for nome, canal, investimento, total_leads, ganhos in campanhas:
                existente = sessao.scalar(
                    select(Campanha).where(
                        Campanha.cliente_id == cliente.id, Campanha.nome == nome
                    )
                )
                if existente is not None:
                    continue
                inicio = hoje - timedelta(days=aleatorio.randint(30, 90))
                campanha = Campanha(
                    cliente_id=cliente.id,
                    nome=nome,
                    canal=canal,
                    investimento_centavos=investimento,
                    inicio=inicio,
                )
                sessao.add(campanha)
                sessao.flush()

                for i in range(total_leads):
                    sessao.add(
                        Lead(
                            campanha_id=campanha.id,
                            nome=f"Lead {i + 1:03d} — {nome_cliente.split()[0]}",
                            email=f"lead{i + 1}@exemplo.com.br",
                            telefone=(
                                f"(11) 9{aleatorio.randint(1000, 9999)}"
                                f"-{aleatorio.randint(1000, 9999)}"
                            ),
                            status=status_do_lead(i, total_leads, ganhos),
                            criado_em=data_do_lead(i, total_leads, inicio, hoje, aleatorio),
                        )
                    )

        marcar(sessao)
        sessao.commit()

    print(f"Semeado (v{VERSAO_SEMENTE}). Entre com {EMAIL_DEMO} / {SENHA_DEMO}")


if __name__ == "__main__":
    semear()
