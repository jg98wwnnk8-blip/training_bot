from core.config import Settings


def test_normalize_database_url_postgres_scheme() -> None:
    settings = Settings(
        bot_token="test-token",
        database_url="postgres://user:pass@localhost:5432/workout",
    )
    assert settings.database_url.startswith("postgresql+asyncpg://")


def test_normalize_database_url_postgresql_scheme() -> None:
    settings = Settings(
        bot_token="test-token",
        database_url="postgresql://user:pass@localhost:5432/workout",
    )
    assert settings.database_url.startswith("postgresql+asyncpg://")


def test_keep_asyncpg_database_url_unchanged() -> None:
    original = "postgresql+asyncpg://user:pass@localhost:5432/workout"
    settings = Settings(
        bot_token="test-token",
        database_url=original,
    )
    assert settings.database_url == original
