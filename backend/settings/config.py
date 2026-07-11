from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    PROJECT_NAME: str = "VitalRisk AI"
    VERSION: str = "1.0.0"

    # Variables individuales (para correr local con uvicorn)
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""
    DB_NAME: str = "postgres"
    DB_PORT: int = 5432
    DB_HOST: str = "localhost"

    # URL completa (la inyecta Docker — tiene prioridad si existe)
    DATABASE_URL: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def db_url(self) -> str:
        # Si Docker inyectó DATABASE_URL, úsala directamente
        # Si no (ejecución local), constrúyela desde las variables individuales
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}")

    @property
    def MODEL_PATH(self) -> Path:
        return BASE_DIR / "data" / "models" / "modelo_xgboost_vitalrisk.pkl"

settings = Settings()