from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str
    database_url: str
    download_files: bool = False
    download_path: str = "./downloads"
    moderation_enabled: bool = False
    admin_ids: str = ""

    model_config = SettingsConfigDict(
        env_file=(".env", "config/.env"),
        extra="ignore",
    )


def get_settings() -> Settings:
    return Settings()


def get_admin_ids(settings: Settings) -> set[int]:
    if not settings.admin_ids:
        return set()
    ids = []
    for part in settings.admin_ids.split(","):
        part = part.strip()
        if part.isdigit():
            ids.append(int(part))
    return set(ids)

