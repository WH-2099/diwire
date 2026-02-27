from pydantic import Field
from pydantic_settings import BaseSettings


class FastAPIE2ESettings(BaseSettings):
    host: str = Field(default="localhost", alias="FASTAPI_E2E_HOST")
    port: int = Field(default=8220, alias="FASTAPI_E2E_PORT")
