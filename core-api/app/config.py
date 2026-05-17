from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    
    
    database_url: str
    frontend_url: str
    google_credentials_json: str
    backend_url: str
    ai_service_url: str
    mail_username: str
    mail_password: str
    mail_from: str
    mail_port: int
    mail_server: str
    mail_from_name: str
    secret_key: str
    
    # MinIO Settings
    minio_endpoint: str = "minio:9000"  # Default to service name in Docker network
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket_name: str = "crm-emails"
    minio_secure: bool = False

    # Ollama Settings
    ollama_base_url: str = "http://localhost:11434"
    email_classifier_model: str = "llama3.2:3b"
    
    # Configurare pentru a citi si din fisier daca variabilele de mediu lipsesc
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()