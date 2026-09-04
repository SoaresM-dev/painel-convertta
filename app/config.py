"""Configuração da aplicação, lida do ambiente.

Nada de segredo em código. `DATABASE_URL` e `SEGREDO_JWT` são as duas
variáveis que mudam entre a máquina de desenvolvimento, a CI e o deploy —
e é por isso que elas entram por ambiente, não por arquivo versionado.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
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

    @field_validator("database_url")
    @classmethod
    def normalizar_driver(cls, url: str) -> str:
        """Render, Railway, Heroku e Fly entregam `postgresql://…` — sem driver.

        Nesse formato o SQLAlchemy escolhe o `psycopg2`, que não está nas
        dependências: este projeto usa `psycopg` 3. O deploy quebra no boot com
        `ModuleNotFoundError: No module named 'psycopg2'`, que não diz nada
        sobre a causa e manda a pessoa instalar a biblioteca errada.

        A alternativa é exigir que quem publica edite a URL à mão antes de
        colar. Já é uma pegadinha documentada em duas notas — e documentação
        que precisa ser lembrada na hora certa é a que falha. Normalizar aqui
        resolve para sempre, em qualquer provedor.

        `postgres://` (a forma antiga do Heroku) também é aceita: o SQLAlchemy
        removeu esse alias na versão 1.4 e ele ainda aparece em provedor velho.
        """
        for prefixo in ("postgresql://", "postgres://"):
            if url.startswith(prefixo):
                return "postgresql+psycopg://" + url[len(prefixo):]
        return url

    @property
    def origens(self) -> list[str]:
        return [o.strip() for o in self.origens_liberadas.split(",") if o.strip()]


@lru_cache
def carregar_config() -> Config:
    return Config()
