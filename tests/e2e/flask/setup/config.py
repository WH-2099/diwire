from pydantic import Field
from pydantic_settings import BaseSettings


class FlaskE2ESettings(BaseSettings):
    host: str = Field(default="localhost", alias="FLASK_E2E_HOST")
    port: int = Field(default=8240, alias="FLASK_E2E_PORT")
