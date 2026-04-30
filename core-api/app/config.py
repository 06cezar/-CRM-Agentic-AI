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
    
    # Configurare pentru a citi si din fisier daca variabilele de mediu lipsesc
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()