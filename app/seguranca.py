"""Hash de senha e token de acesso.

**A senha nunca é guardada.** O que vai para o banco é o hash do bcrypt, com
sal próprio por senha — dois usuários com a mesma senha têm hashes
diferentes, e vazamento do banco não devolve senha nenhuma.

**O token não guarda segredo.** O JWT carrega só o id do usuário e a
expiração; ele é assinado, não criptografado, e qualquer um consegue ler o
conteúdo. Por isso nada sensível entra ali dentro.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.config import carregar_config

ALGORITMO = "HS256"


def cifrar_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def senha_confere(senha: str, hash_guardado: str) -> bool:
    try:
        return bcrypt.checkpw(senha.encode("utf-8"), hash_guardado.encode("utf-8"))
    except ValueError:
        # Hash malformado no banco: trata como senha errada, nunca como acesso.
        return False


def gerar_token(usuario_id: int) -> str:
    config = carregar_config()
    expira_em = datetime.now(UTC) + timedelta(minutes=config.expiracao_minutos)
    return jwt.encode(
        {"sub": str(usuario_id), "exp": expira_em},
        config.segredo_jwt,
        algorithm=ALGORITMO,
    )


def ler_token(token: str) -> int | None:
    """Devolve o id do usuário, ou None se o token for inválido ou expirado."""
    try:
        dados = jwt.decode(token, carregar_config().segredo_jwt, algorithms=[ALGORITMO])
        return int(dados["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
