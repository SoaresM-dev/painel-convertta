from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.dependencias import SessaoDep, UsuarioDep
from app.models import Cliente
from app.schemas import ClienteEntrada, ClienteSaida

rotas = APIRouter(prefix="/api/clientes", tags=["clientes"])


@rotas.get("", response_model=list[ClienteSaida])
def listar(sessao: SessaoDep, _usuario: UsuarioDep) -> list[Cliente]:
    return list(sessao.scalars(select(Cliente).order_by(Cliente.nome)))


@rotas.post("", response_model=ClienteSaida, status_code=status.HTTP_201_CREATED)
def criar(dados: ClienteEntrada, sessao: SessaoDep, _usuario: UsuarioDep) -> Cliente:
    cliente = Cliente(nome=dados.nome.strip())
    sessao.add(cliente)
    try:
        sessao.commit()
    except IntegrityError:
        # A unicidade é garantida pelo banco, não por um SELECT antes do
        # INSERT — que perde a corrida quando duas requisições chegam juntas.
        sessao.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Cliente já existe"
        ) from None
    sessao.refresh(cliente)
    return cliente


@rotas.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover(cliente_id: int, sessao: SessaoDep, _usuario: UsuarioDep) -> None:
    cliente = sessao.get(Cliente, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")
    sessao.delete(cliente)
    sessao.commit()
