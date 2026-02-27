from pydantic import Field
from pydantic_settings import BaseSettings


class CeleryE2ESettings(BaseSettings):
    broker_url: str = Field(default="redis://localhost:6379/0", alias="CELERY_E2E_BROKER_URL")
    result_backend: str = Field(
        default="redis://localhost:6379/1",
        alias="CELERY_E2E_RESULT_BACKEND",
    )
    queue: str = Field(default="diwire-e2e", alias="CELERY_E2E_QUEUE")
