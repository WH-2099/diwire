from pydantic import Field
from pydantic_settings import BaseSettings


class AioHttpE2ESettings(BaseSettings):
    host: str = Field(default="localhost", alias="AIOHTTP_E2E_HOST")
    port: int = Field(default=8230, alias="AIOHTTP_E2E_PORT")
