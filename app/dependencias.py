"""A dependência que fecha as rotas.

Toda rota de dados pede `usuario_atual`. Não existe caminho que leia ou
escreva no banco sem token válido — a proteção é estrutural, não uma
checagem repetida em cada função (que é o que se esquece de escrever).
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db import obter_sessao
from app.models import Usuario
from app.seguranca import ler_token

esquema_oauth = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

SessaoDep = Annotated[Session, Depends(obter_sessao)]


def usuario_atual(
    sessao: SessaoDep,
    token: Annotated[str, Depends(esquema_oauth)],
) -> Usuario:
    nao_autorizado = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    usuario_id = ler_token(token)
    if usuario_id is None:
        raise nao_autorizado
    usuario = sessao.get(Usuario, usuario_id)
    if usuario is None:
        raise nao_autorizado
    return usuario


UsuarioDep = Annotated[Usuario, Depends(usuario_atual)]
