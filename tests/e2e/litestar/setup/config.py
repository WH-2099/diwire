from pydantic import Field
from pydantic_settings import BaseSettings


class LitestarE2ESettings(BaseSettings):
    host: str = Field(default="localhost", alias="LITESTAR_E2E_HOST")
    port: int = Field(default=8240, alias="LITESTAR_E2E_PORT")
