"""Popula o banco com a conta demo e dados plausíveis.

**Existe para o recrutador.** Uma URL ao vivo que pede login e mostra uma tela
vazia não prova nada. Este script deixa o painel com números logo na primeira
abertura, e é idempotente: rodar duas vezes não duplica nada.

    python -m scripts.semear
"""
from __future__ import annotations

import random
from datetime import date, timedelta

from sqlalchemy import inspect, select

from app.db import CriarSessao, engine
from app.models import Campanha, Canal, Cliente, Lead, StatusLead, Usuario
from app.seguranca import cifrar_senha

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


def semear() -> None:
    # De propósito **não** cria tabela. Quem cria esquema é o Alembic, e só
    # ele: dois donos do esquema é como se chega em produção com uma coluna
    # que existe na máquina de quem escreveu e não existe no servidor.
    if not inspect(engine).has_table("usuarios"):
        raise SystemExit("Banco sem esquema. Rode `alembic upgrade head` antes.")

    aleatorio = random.Random(42)  # semente fixa: a demo é sempre a mesma

    with CriarSessao() as sessao:
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
                campanha = Campanha(
                    cliente_id=cliente.id,
                    nome=nome,
                    canal=canal,
                    investimento_centavos=investimento,
                    inicio=hoje - timedelta(days=aleatorio.randint(30, 90)),
                )
                sessao.add(campanha)
                sessao.flush()

                for i in range(total_leads):
                    if i < ganhos:
                        status = StatusLead.GANHO
                    elif i < ganhos + total_leads // 4:
                        status = StatusLead.QUALIFICADO
                    elif i < ganhos + total_leads // 2:
                        status = StatusLead.CONTATADO
                    else:
                        status = StatusLead.NOVO
                    sessao.add(
                        Lead(
                            campanha_id=campanha.id,
                            nome=f"Lead {i + 1:03d} — {nome_cliente.split()[0]}",
                            email=f"lead{i + 1}@exemplo.com.br",
                            telefone=(
                                f"(11) 9{aleatorio.randint(1000, 9999)}"
                                f"-{aleatorio.randint(1000, 9999)}"
                            ),
                            status=status,
                        )
                    )

        sessao.commit()

    print(f"Semeado. Entre com {EMAIL_DEMO} / {SENHA_DEMO}")


if __name__ == "__main__":
    semear()
