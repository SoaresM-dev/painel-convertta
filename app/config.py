"""Configuração da aplicação, lida do ambiente.

Nada de segredo em código. `DATABASE_URL` e `SEGREDO_JWT` são as duas
variáveis que mudam entre a máquina de desenvolvimento, a CI e o deploy —
e é por isso que elas entram por ambiente, não por arquivo versionado.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # SQLite por padrão para o `pytest` rodar sem serviço no ar. Em
    # desenvolvimento, na CI e em produção esta variável aponta para Postgres —
    # o docker-compose e o workflow da CI a definem.
    database_url: str = "sqlite+pysqlite:///./painel.db"
    segredo_jwt: str = "desenvolvimento-apenas-troque-em-producao"
    expiracao_minutos: int = 480
    origens_liberadas: str = "http://localhost:5173"

    @property
    def origens(self) -> list[str]:
        return [o.strip() for o in self.origens_liberadas.split(",") if o.strip()]


@lru_cache
def carregar_config() -> Config:
    return Config()
