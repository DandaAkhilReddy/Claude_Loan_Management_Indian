"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/loan_analyzer"

    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_key: str = ""
    azure_openai_deployment: str = "gpt-4o-mini"

    # Azure Document Intelligence
    azure_doc_intel_endpoint: str = ""
    azure_doc_intel_key: str = ""

    # Azure Blob Storage
    azure_storage_connection_string: str = ""
    azure_storage_container: str = "loan-documents"

    # Azure Translator
    azure_translator_key: str = ""
    azure_translator_region: str = "centralindia"

    # Azure TTS
    azure_tts_key: str = ""
    azure_tts_region: str = "centralindia"

    # Firebase
    firebase_project_id: str = ""

    # App
    environment: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173"  # comma-separated in production

    class Config:
        env_file = ".env"


settings = Settings()
