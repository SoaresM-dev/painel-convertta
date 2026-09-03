from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.dependencias import SessaoDep, UsuarioDep
from app.models import Campanha, Cliente
from app.schemas import CampanhaEntrada, CampanhaSaida

rotas = APIRouter(prefix="/api/campanhas", tags=["campanhas"])


@rotas.get("", response_model=list[CampanhaSaida])
def listar(
    sessao: SessaoDep, _usuario: UsuarioDep, cliente_id: int | None = None
) -> list[Campanha]:
    consulta = select(Campanha).order_by(Campanha.inicio.desc())
    if cliente_id is not None:
        consulta = consulta.where(Campanha.cliente_id == cliente_id)
    return list(sessao.scalars(consulta))


@rotas.post("", response_model=CampanhaSaida, status_code=status.HTTP_201_CREATED)
def criar(dados: CampanhaEntrada, sessao: SessaoDep, _usuario: UsuarioDep) -> Campanha:
    if sessao.get(Cliente, dados.cliente_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")
    if dados.fim is not None and dados.fim < dados.inicio:
        # 422 literal: o nome da constante mudou entre versões do Starlette
        # e não vale acoplar a rota a isso.
        raise HTTPException(
            status_code=422,
            detail="A data de fim não pode ser anterior à de início",
        )
    campanha = Campanha(**dados.model_dump())
    sessao.add(campanha)
    try:
        sessao.commit()
    except IntegrityError:
        sessao.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este cliente já tem uma campanha com esse nome",
        ) from None
    sessao.refresh(campanha)
    return campanha
