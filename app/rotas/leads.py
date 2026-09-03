from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.dependencias import SessaoDep, UsuarioDep
from app.models import Campanha, Lead
from app.schemas import LeadAtualizacao, LeadEntrada, LeadSaida

rotas = APIRouter(prefix="/api/leads", tags=["leads"])


@rotas.get("", response_model=list[LeadSaida])
def listar(sessao: SessaoDep, _usuario: UsuarioDep, campanha_id: int | None = None) -> list[Lead]:
    consulta = select(Lead).order_by(Lead.criado_em.desc())
    if campanha_id is not None:
        consulta = consulta.where(Lead.campanha_id == campanha_id)
    return list(sessao.scalars(consulta))


@rotas.post("", response_model=LeadSaida, status_code=status.HTTP_201_CREATED)
def criar(dados: LeadEntrada, sessao: SessaoDep, _usuario: UsuarioDep) -> Lead:
    if sessao.get(Campanha, dados.campanha_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campanha não encontrada")
    lead = Lead(**dados.model_dump())
    lead.email = str(dados.email) if dados.email else None
    sessao.add(lead)
    sessao.commit()
    sessao.refresh(lead)
    return lead


@rotas.patch("/{lead_id}", response_model=LeadSaida)
def mudar_status(
    lead_id: int, dados: LeadAtualizacao, sessao: SessaoDep, _usuario: UsuarioDep
) -> Lead:
    lead = sessao.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead não encontrado")
    lead.status = dados.status
    sessao.commit()
    sessao.refresh(lead)
    return lead
