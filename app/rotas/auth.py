"""Login. É a única rota pública do sistema."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.dependencias import SessaoDep, UsuarioDep
from app.models import Usuario
from app.schemas import Token, UsuarioSaida
from app.seguranca import gerar_token, senha_confere

rotas = APIRouter(prefix="/api/auth", tags=["auth"])


@rotas.post("/token", response_model=Token)
def entrar(
    sessao: SessaoDep,
    formulario: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    usuario = sessao.scalar(select(Usuario).where(Usuario.email == formulario.username))
    # A mesma mensagem para e-mail inexistente e senha errada, de propósito:
    # mensagens diferentes contam a quem tenta invadir quais e-mails existem.
    if usuario is None or not senha_confere(formulario.password, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=gerar_token(usuario.id))


@rotas.get("/eu", response_model=UsuarioSaida)
def quem_sou_eu(usuario: UsuarioDep) -> Usuario:
    return usuario
